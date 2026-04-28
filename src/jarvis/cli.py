from __future__ import annotations

import os

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from jarvis import __version__
from jarvis.assistant import JarvisAssistant

app = typer.Typer(
    name="jarvis",
    help="자비스 — 승우의 개인 AI 비서",
    no_args_is_help=True,
    add_completion=False,
)
daemon_app = typer.Typer(
    name="daemon",
    help="wake 모드 launchd 데몬 관리 (install/uninstall/status/logs/restart)",
    no_args_is_help=True,
)
app.add_typer(daemon_app, name="daemon")
console = Console()


@app.command()
def version() -> None:
    """버전 출력."""
    console.print(f"jarvis [bold cyan]{__version__}[/bold cyan]")


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="질문 또는 지시"),
    fast: bool = typer.Option(False, "--fast", help="빠른 모델(Haiku) 사용"),
) -> None:
    """단발성 질문. 스트리밍 출력."""
    from jarvis.config import settings

    assistant = JarvisAssistant(model=settings.fast_model if fast else None)
    console.print("[dim]자비스:[/dim] ", end="")
    buffer: list[str] = []
    for chunk in assistant.stream([{"role": "user", "content": prompt}]):
        console.print(chunk, end="")
        buffer.append(chunk)
    console.print()


@app.command()
def do(
    task: str = typer.Argument(..., help="자비스가 수행할 작업"),
    max_turns: int = typer.Option(12, "--max-turns", help="최대 에이전트 턴"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="중간 출력 숨기고 결과만"),
) -> None:
    """에이전트 모드. 도구를 자유롭게 사용해 작업 수행."""
    from jarvis.agent import run_agent

    result = run_agent(task, max_turns=max_turns, verbose=not quiet, console=console)
    if quiet and result:
        console.print(Markdown(result))


@app.command()
def listen(
    model: str = typer.Option("small", "--model", help="Whisper 모델: tiny|base|small|medium|large"),
    no_speak: bool = typer.Option(False, "--no-speak", help="TTS 출력 끔"),
    lang: str = typer.Option("ko", "--lang", help="음성 언어 코드"),
) -> None:
    """단발 음성: 마이크 녹음 → 전사 → 자비스 답변 (텍스트 + TTS)."""
    from jarvis.tools.macos import _say
    from jarvis.voice import record_until_silence, transcribe

    console.print("[bold cyan]말씀하시오.[/bold cyan] [dim](1.5초 침묵 시 자동 종료)[/dim]")
    audio = record_until_silence()
    if audio.size == 0:
        console.print("[yellow](음성 감지 실패)[/yellow]")
        return
    console.print("[dim]전사 중...[/dim]")
    text = transcribe(audio, language=lang, model_name=model)
    if not text:
        console.print("[yellow](전사 결과 없음)[/yellow]")
        return
    console.print(f"[green]> {text}[/green]")

    assistant = JarvisAssistant()
    buffer: list[str] = []
    console.print("[dim]자비스:[/dim] ", end="")
    for chunk in assistant.stream([{"role": "user", "content": text}]):
        console.print(chunk, end="")
        buffer.append(chunk)
    console.print()
    if not no_speak:
        _say("".join(buffer), voice="Yuna")


@app.command()
def wake(
    word: str = typer.Option("", "--word", help="추가 wake word (기본 변종 + 이 단어 포함)"),
    detect_model: str = typer.Option("base", "--detect-model", help="wake 감지용 (빠른 게 좋음)"),
    main_model: str = typer.Option("small", "--model", help="명령 전사용"),
    no_speak: bool = typer.Option(False, "--no-speak", help="TTS 출력 끔"),
    lang: str = typer.Option("auto", "--lang", help="명령 언어. 'auto' = 한/영 자동 감지"),
    chime: bool = typer.Option(True, "--chime/--no-chime", help="wake 응답 음성"),
) -> None:
    """Wake mode — hover로 마이크 활성, '자비스/Jarvis' 발화 → '예 주인님' 응답.

    흐름:
      1. JarvisHUD.app이 노치 hover → hover.json active=true → 마이크 ON
      2. daemon이 wake word ('자비스' 또는 'Jarvis') listening
      3. wake matched → '예 주인님 무엇을 도와드릴까요' TTS + lock 시작
      4. 명령 발화 (한/영) → transcribe → run_agent → 짧은 답변 + TTS
      5. 답변 완료 → lock 해제 → hover OFF 후 collapse
    """
    import json as _json
    import time as _time
    from pathlib import Path as _Path

    from jarvis import health_server, hud
    from jarvis.agent import run_agent
    from jarvis.tools.macos import _say
    from jarvis.voice import (
        DEFAULT_WAKE_WORDS,
        capture_phrase,
        listen_for_wake,
        transcribe,
    )
    from jarvis.voice.wake import _is_hover_active

    _lock_path = _Path.home() / "Library" / "Caches" / "jarvis-lock.json"

    def _write_lock(active: bool) -> None:
        try:
            _lock_path.parent.mkdir(parents=True, exist_ok=True)
            _lock_path.write_text(_json.dumps({"lock": active, "ts": _time.time()}))
        except Exception:
            pass

    try:
        port = health_server.start()
        if port > 0:
            console.print(f"[dim]health: http://127.0.0.1:{port}/healthz[/dim]")
    except Exception:
        pass

    console.print("[bold cyan]자비스 wake 모드.[/bold cyan]")
    console.print("[dim]노치(카메라) 영역에 마우스 hover → 명령 발화 (wake word 불필요)[/dim]")
    console.print("[dim]Ctrl+C 종료 | 명령은 한국어/영어 둘 다 가능[/dim]")

    rms_cb = hud.set_voice_level

    try:
        while True:
            hud.set_state("idle")

            # 1. Hover ON 대기 (block)
            while not _is_hover_active():
                _time.sleep(0.2)

            console.print("\n[bold magenta]🎙 hover detected — 명령 받겠습니다[/bold magenta]")
            # 세션 시작 — lock ON (마우스 떠나도 panel 유지)
            _write_lock(True)

            # 2. "네" chime
            if chime and not no_speak:
                hud.set_state("speaking", "ack")
                _say("네")

            # 3. 명령 capture (긴 silence — 사용자 발화 충분히 받음)
            hud.set_state("listening", "command")
            console.print("[dim]말씀하시오...[/dim]")
            audio = capture_phrase(
                silence_duration=1.8,
                max_speech_duration=20.0,
                on_chunk_rms=rms_cb,
            )
            if audio.size == 0:
                console.print("[yellow](명령 없음 — hover OFF 후 다시)[/yellow]")
                while _is_hover_active():
                    _time.sleep(0.3)
                continue

            # 4. Transcribe (auto-detect 한/영)
            hud.set_state("analyzing", "transcribe")
            command_text = transcribe(
                audio,
                language="auto" if lang == "auto" else lang,
                model_name=main_model,
            ).strip()

            if not command_text:
                console.print("[yellow](전사 결과 없음)[/yellow]")
                _write_lock(False)
                while _is_hover_active():
                    _time.sleep(0.3)
                continue

            console.print(f"[green]> {command_text}[/green]")

            # 6. run_agent로 명령 실행 (도구 사용)
            response = run_agent(
                command_text,
                max_turns=8,
                verbose=False,
                console=console,
            )
            console.print(f"[bold]자비스:[/bold] {response}")

            # 7. TTS 답변
            if response and not no_speak:
                hud.set_state("speaking", "answer")
                _say(response[:500])

            hud.set_state("idle")
            _write_lock(False)

            # 8. hover OFF까지 대기 (double-trigger 방지)
            while _is_hover_active():
                _time.sleep(0.3)
    except KeyboardInterrupt:
        console.print("\n[dim]세션 종료.[/dim]")
    finally:
        hud.set_state("idle")
        _write_lock(False)


@app.command()
def voice(
    model: str = typer.Option("small", "--model", help="Whisper 모델"),
    no_speak: bool = typer.Option(False, "--no-speak", help="TTS 출력 끔"),
    lang: str = typer.Option("ko", "--lang", help="음성 언어 코드"),
) -> None:
    """인터랙티브 음성 대화 루프. '/exit' 또는 Ctrl+C로 종료."""
    from jarvis.tools.macos import _say
    from jarvis.voice import record_until_silence, transcribe

    assistant = JarvisAssistant()
    history: list[dict] = []
    console.print("[bold cyan]자비스 음성 모드 온라인.[/bold cyan] [dim]Ctrl+C로 종료[/dim]")
    try:
        while True:
            console.print("\n[bold cyan]말씀하시오...[/bold cyan]")
            audio = record_until_silence()
            if audio.size == 0:
                console.print("[yellow](음성 감지 실패 — 다시 시도)[/yellow]")
                continue
            text = transcribe(audio, language=lang, model_name=model)
            if not text:
                console.print("[yellow](전사 결과 없음)[/yellow]")
                continue
            console.print(f"[green]> {text}[/green]")
            if text.strip().rstrip(".!?") in {"/exit", "/quit", "종료", "끝", "잘자"}:
                break

            history.append({"role": "user", "content": text})
            buffer: list[str] = []
            console.print("[dim]자비스:[/dim] ", end="")
            for chunk in assistant.stream(history):
                console.print(chunk, end="")
                buffer.append(chunk)
            console.print()
            response = "".join(buffer)
            history.append({"role": "assistant", "content": response})
            if not no_speak:
                _say(response, voice="Yuna")
    except KeyboardInterrupt:
        console.print("\n[dim]세션 종료.[/dim]")


@app.command()
def chat() -> None:
    """인터랙티브 대화. /exit 또는 Ctrl+C로 종료."""
    assistant = JarvisAssistant()
    history: list[dict] = []
    console.print("[bold cyan]자비스 온라인.[/bold cyan] [dim]종료: /exit[/dim]")
    while True:
        try:
            user_input = Prompt.ask("[bold green]>[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]세션 종료.[/dim]")
            break
        if user_input.strip() in {"/exit", "/quit", "/q"}:
            break
        if not user_input.strip():
            continue
        history.append({"role": "user", "content": user_input})
        console.print("[dim]자비스:[/dim] ", end="")
        buffer: list[str] = []
        for chunk in assistant.stream(history):
            console.print(chunk, end="")
            buffer.append(chunk)
        console.print()
        history.append({"role": "assistant", "content": "".join(buffer)})


hud_app = typer.Typer(
    name="hud",
    help="HUD 위젯 직접 제어 (start/stop/state)",
    no_args_is_help=True,
)
app.add_typer(hud_app, name="hud")


@hud_app.command("start")
def hud_start() -> None:
    """Übersicht 앱 시작 (위젯 자동 로드)."""
    import os as _os

    apps = _os.popen("ls /Applications/ 2>/dev/null").read()
    if "bersicht" not in apps:
        console.print("[red]Übersicht 미설치 — `brew install --cask ubersicht`[/red]")
        return
    _os.system("open /Applications/*bersicht*.app")
    console.print("OK: Übersicht 시작")


@hud_app.command("stop")
def hud_stop() -> None:
    """Übersicht 종료."""
    import os as _os

    _os.system("osascript -e 'tell application \"Übersicht\" to quit' 2>/dev/null || pkill -f bersicht")
    console.print("OK: Übersicht 종료")


@hud_app.command("state")
def hud_state(
    state: str = typer.Argument(..., help="idle|listening|analyzing|speaking"),
    message: str = typer.Option("", "--message", "-m"),
) -> None:
    """수동으로 HUD 상태 토글 (디버깅용)."""
    from jarvis import hud as _hud

    valid = {"idle", "listening", "analyzing", "speaking"}
    if state not in valid:
        console.print(f"[red]invalid state. choose: {valid}[/red]")
        return
    _hud.set_state(state, message)
    console.print(f"OK: state={state} message={message!r}")


@app.command()
def note(
    text: str = typer.Argument(..., help="메모 내용"),
) -> None:
    """~/.jarvis/notes.md 에 메모 한 줄 append (timestamp 포함)."""
    from datetime import datetime as _dt
    from pathlib import Path

    path = Path.home() / ".jarvis" / "notes.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = _dt.now().strftime("%Y-%m-%d %H:%M")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- [{ts}] {text}\n")
    console.print(f"OK: {path}")


@app.command()
def timer(
    minutes: float = typer.Argument(..., help="분"),
    message: str = typer.Option("타이머 종료", "--message", "-m"),
) -> None:
    """N분 타이머 — 종료 시 사운드 + macOS 알림."""
    import subprocess
    import time as _t

    secs = int(minutes * 60)
    console.print(f"[cyan]⏱ {minutes}분 타이머 시작 — {message}[/cyan]")
    try:
        _t.sleep(secs)
    except KeyboardInterrupt:
        console.print("\n[yellow]타이머 취소[/yellow]")
        return
    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
    subprocess.run(
        ["osascript", "-e", f'display notification "{message}" with title "자비스 타이머"'],
        check=False,
    )
    console.print(f"[bold green]⏰ {message}[/bold green]")


plugin_app = typer.Typer(
    name="plugin",
    help="플러그인 관리 (~/.jarvis/plugins/*.py)",
    no_args_is_help=True,
)
app.add_typer(plugin_app, name="plugin")


@plugin_app.command("list")
def plugin_list() -> None:
    """등록된 플러그인 list."""
    from jarvis import plugins

    discovered = plugins.discover()
    if not discovered:
        console.print(f"[dim](no plugins at ~/.jarvis/plugins/)[/dim]")
        return
    console.print(f"[bold]{len(discovered)} plugin(s):[/bold]")
    for p in discovered:
        console.print(f"  • {p.stem} ({p})")


@plugin_app.command("reload")
def plugin_reload() -> None:
    """플러그인 강제 재로드."""
    from jarvis import plugins

    loaded = plugins.load_all()
    console.print(f"loaded: {loaded or '(none)'}")


@plugin_app.command("init")
def plugin_init() -> None:
    """~/.jarvis/plugins/example.py 템플릿 생성."""
    from pathlib import Path

    plugin_dir = Path.home() / ".jarvis" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    example = plugin_dir / "example.py"
    if example.exists():
        console.print(f"[yellow]이미 존재: {example}[/yellow]")
        return
    example.write_text('''"""예시 plugin — ~/.jarvis/plugins/example.py."""
from jarvis.tools.registry import REGISTRY, Tool


def _hello(name: str = "world") -> str:
    return f"Hello, {name}!"


REGISTRY.register(Tool(
    name="hello",
    description="간단한 인사 도구.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": [],
    },
    handler=_hello,
))
''')
    console.print(f"OK: {example}")
    console.print("[dim]daemon 또는 jarvis 명령 재시작 시 자동 로드됨[/dim]")


@app.command("config")
def config_cmd(
    show: bool = typer.Option(False, "--show", "-s"),
    edit: bool = typer.Option(False, "--edit", "-e"),
    init: bool = typer.Option(False, "--init", help="기본 config.toml 생성"),
) -> None:
    """~/.jarvis/config.toml 설정 파일 관리."""
    import os as _os

    from jarvis import user_config

    path = user_config.path()
    if init:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            console.print(f"[yellow]이미 존재: {path}[/yellow]")
            return
        path.write_text('''# 자비스 사용자 설정 (~/.jarvis/config.toml)

# voice = "Reed"        # TTS voice (Reed/Yuna/Eddy/Sandy 등)
# persona = "jarvis"    # jarvis|casual|formal|creative
# hud_sounds = true     # sci-fi 사운드 효과
# wake_debug = false    # wake 이벤트 stderr 출력
# health_port = 41418   # health server 포트
''', encoding="utf-8")
        console.print(f"OK: {path}")
        return
    if edit:
        editor = _os.environ.get("EDITOR", "vi")
        _os.system(f"{editor} {path}")
        return
    if show or True:  # default: show
        if path.exists():
            console.print(path.read_text(encoding="utf-8") or "(empty)")
        else:
            console.print(f"(no config at {path}) — `jarvis config --init` 으로 생성")


@app.command()
def stats() -> None:
    """자비스 자체 상태 + 등록 도구 list + 최근 history."""
    from jarvis import history as _hist
    from jarvis.tools import REGISTRY

    console.print("[bold cyan]▣ JARVIS STATS[/bold cyan]")
    console.print(f"[dim]tools registered:[/dim] {len(REGISTRY.names())}")
    console.print(f"[dim]history file:[/dim] {_hist.path()}")
    console.print(f"[dim]history entries:[/dim] {len(_hist.tail(99999))}")

    import subprocess
    try:
        pgrep = subprocess.run(["pgrep", "-f", "jarvis wake"], capture_output=True, text=True, timeout=3)
        console.print(f"[dim]daemon PIDs:[/dim] {pgrep.stdout.strip() or '(not running)'}")
    except Exception:
        pass

    import json
    from pathlib import Path
    hud_p = Path.home() / "Library" / "Caches" / "jarvis-hud.json"
    if hud_p.exists():
        st = json.loads(hud_p.read_text())
        console.print(f"[dim]hud state:[/dim] {st.get('state', '?')}")


@app.command()
def tools_list(
    detail: bool = typer.Option(False, "--detail", "-d"),
) -> None:
    """등록된 모든 도구 list."""
    from jarvis.tools import REGISTRY

    for name in sorted(REGISTRY.names()):
        tool = REGISTRY.get(name)
        if detail and tool:
            console.print(f"[bold cyan]{name}[/bold cyan]")
            console.print(f"  [dim]{tool.description}[/dim]")
            req = tool.input_schema.get("required", [])
            if req:
                console.print(f"  [dim]required: {req}[/dim]")
        else:
            console.print(f"  {name}")


@app.command()
def update() -> None:
    """git pull + pip install — 자비스 self-update."""
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    console.print(f"[cyan]자비스 업데이트 시작 — {root}[/cyan]")
    pull = subprocess.run(["git", "-C", str(root), "pull"], capture_output=True, text=True)
    console.print(pull.stdout or pull.stderr)
    if pull.returncode == 0:
        venv_pip = root / ".venv" / "bin" / "pip"
        if venv_pip.exists():
            inst = subprocess.run(
                [str(venv_pip), "install", "-q", "-e", f"{root}[dev]"],
                capture_output=True, text=True,
            )
            console.print(inst.stdout[-500:] if inst.stdout else "(deps OK)")
    console.print("[green]업데이트 완료. daemon은 `jarvis daemon restart`로 반영.[/green]")


@app.command()
def memory(
    show: bool = typer.Option(False, "--show", help="현재 메모 출력"),
    edit: bool = typer.Option(False, "--edit", help="$EDITOR로 메모 편집"),
    add: str = typer.Option("", "--add", help="메모 끝에 한 줄 추가"),
    clear: bool = typer.Option(False, "--clear", help="메모 비우기"),
) -> None:
    """~/.jarvis/memory.md — 시스템 프롬프트에 자동 첨부되는 cross-session 기억."""
    import os as _os
    from pathlib import Path

    path = Path.home() / ".jarvis" / "memory.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if clear:
        path.write_text("", encoding="utf-8")
        console.print("OK: 메모 비웠음")
        return
    if add:
        with path.open("a", encoding="utf-8") as f:
            f.write(f"- {add}\n")
        console.print(f"OK: 메모 추가됨 ({path})")
        return
    if edit:
        editor = _os.environ.get("EDITOR", "vi")
        _os.system(f"{editor} {path}")
        return
    if show or not (add or edit or clear):
        if path.exists():
            console.print(path.read_text(encoding="utf-8") or "(empty)")
        else:
            console.print(f"(no memory file at {path})")


@hud_app.command("history")
def hud_history(
    n: int = typer.Option(10, "--n", "-n", help="마지막 n개 turn"),
) -> None:
    """대화 히스토리 tail."""
    from jarvis import history as _hist

    entries = _hist.tail(n)
    if not entries:
        console.print(f"(history empty — {_hist.path()})")
        return
    for e in entries:
        from datetime import datetime as _dt
        ts = _dt.fromtimestamp(e["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        role = e["role"]
        content = e["content"][:200]
        color = "green" if role == "user" else "cyan"
        console.print(f"[dim]{ts}[/dim] [{color}]{role}[/{color}] {content}")


@daemon_app.command("install")
def daemon_install(
    no_chime: bool = typer.Option(False, "--no-chime"),
    no_speak: bool = typer.Option(False, "--no-speak"),
    detect_model: str = typer.Option("base", "--detect-model"),
    main_model: str = typer.Option("small", "--model"),
    debug: bool = typer.Option(False, "--debug", help="JARVIS_WAKE_DEBUG=1로 verbose 로그"),
) -> None:
    """launchd plist 작성 + 자동 실행 시작 (RunAtLoad + KeepAlive)."""
    from jarvis.daemon import install as do_install

    args = ["wake", "--detect-model", detect_model, "--model", main_model]
    if no_chime:
        args.append("--no-chime")
    if no_speak:
        args.append("--no-speak")
    env_vars = {"JARVIS_WAKE_DEBUG": "1"} if debug else None
    console.print(do_install(args, env_vars=env_vars))
    console.print(
        "[dim]주의: 첫 실행 시 macOS 마이크 권한 다이얼로그가 뜰 수 있음. "
        "Terminal/Python에 권한 부여 필요.[/dim]"
    )


@daemon_app.command("uninstall")
def daemon_uninstall() -> None:
    """plist 제거 + launchd 언로드."""
    from jarvis.daemon import uninstall as do_uninstall

    console.print(do_uninstall())


@daemon_app.command("status")
def daemon_status() -> None:
    """현재 로드 상태 + PID + 마지막 종료 코드."""
    from jarvis.daemon import status

    console.print(status())


@daemon_app.command("restart")
def daemon_restart() -> None:
    """unload → bootstrap (plist 변경 반영)."""
    from jarvis.daemon import restart

    console.print(restart())


@daemon_app.command("logs")
def daemon_logs(
    stream: str = typer.Option("out", "--stream", "-s", help="out 또는 err"),
    lines: int = typer.Option(50, "--lines", "-n"),
    follow: bool = typer.Option(False, "--follow", "-f", help="tail -f"),
) -> None:
    """daemon stdout/stderr 로그 출력."""
    from jarvis.daemon import LOG_ERR, LOG_OUT, tail_log

    if follow:
        path = LOG_OUT if stream == "out" else LOG_ERR
        if not path.exists():
            console.print(f"NO_LOG: {path}")
            return
        os.execvp("tail", ["tail", "-f", "-n", str(lines), str(path)])
    else:
        console.print(tail_log(stream, lines))


if __name__ == "__main__":
    app()
