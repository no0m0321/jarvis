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
    help="자비스 — 음성 기반 개인 AI 비서",
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
    detect_model: str = typer.Option("tiny", "--detect-model", help="wake 감지용 (빠른 게 좋음 — '자비스' 짧으니 tiny 충분)"),
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
        capture_phrase,
        listen_for_wake,
        transcribe,
    )
    from jarvis.voice.wake import _is_hover_active, get_wake_words

    _lock_path = _Path.home() / "Library" / "Caches" / "jarvis-lock.json"

    def _write_lock(active: bool) -> None:
        try:
            _lock_path.parent.mkdir(parents=True, exist_ok=True)
            _lock_path.write_text(_json.dumps({"lock": active, "ts": _time.time()}))
        except Exception:
            pass

    # 호칭 — JARVIS_OWNER_NAME env 우선, 없으면 "주인님"
    from jarvis.config import settings as _s
    _OWNER = (_s.owner_name.strip() or "주인님")

    try:
        port = health_server.start()
        if port > 0:
            console.print(f"[dim]health: http://127.0.0.1:{port}/healthz[/dim]")
    except Exception:
        pass

    console.print("[bold cyan]자비스 wake 모드.[/bold cyan]")
    console.print("[dim]노치 hover → 마이크 ON | '자비스/Jarvis' 부르면 응답[/dim]")
    console.print("[dim]Ctrl+C 종료 | 명령은 한국어 (auto는 짧은 발화에 부정확)[/dim]")

    # DEFAULT_WAKE_WORDS + JARVIS_WAKE_WORD env (쉼표 구분) + --word CLI 추가
    wake_words = list(get_wake_words())
    if word:
        wake_words.insert(0, word)

    rms_cb = hud.set_voice_level

    try:
        while True:
            hud.set_state("idle")
            _write_lock(False)

            # 1. Hover ON 대기 (block)
            while not _is_hover_active():
                _time.sleep(0.2)

            # 2. wake word listening (hover 동안만 — _HOVER_GATE)
            console.print("\n[bold magenta]🎙 hover — '자비스' 호출 대기[/bold magenta]")
            hud.set_state("listening", "wake")
            heard = listen_for_wake(
                wake_words=wake_words,
                detection_model=detect_model,
                language="ko",  # 한국어 강제 — auto-detect는 짧은 '자비스'를 'Service'/'Yavuz' 등으로 오인
                silence_threshold=0.012,  # capture_phrase 기본과 맞춤 — 약한 발화 시작 흡수
                chunk_silence_duration=0.3,  # 발화 종료 → 응답 빠르게 (0.5 → 0.3)
                on_chunk_rms=rms_cb,
            )
            console.print(f"[bold magenta]wake matched → {heard}[/bold magenta]")

            # 3. wake matched — 즉시 lock + 비동기 ack ("네") 후 곧바로 listening
            _write_lock(True)
            if not no_speak:
                hud.set_state("speaking", "ack")
                # 비동기 — TTS 끝날 때까지 기다리지 않고 바로 다음 listening으로
                import subprocess as _sp
                _sp.Popen(["say", "-v", "Yuna", "네"])

            # 4. Multi-turn 대화 loop — '사라져' 등 종료어까지 계속
            EXIT_KEYWORDS = {
                "꺼져", "꺼지다", "사라져", "사라지다", "그만", "종료", "끝", "잘자",
                "bye", "goodbye", "stop", "quit",
            }
            empty_streak = 0
            tx_lang = "ko" if lang in ("auto", "ko") else lang

            while True:
                hud.set_state("listening", "command")
                console.print("[dim]말씀하세요...[/dim]")
                # 사용자 hesitation 흡수 — 2.5초 침묵 후에야 발화 종료로 간주
                # max 25초까지 한 발화 캡처 가능 (긴 명령/생각 흐름 OK)
                audio = capture_phrase(
                    silence_duration=2.5,
                    max_speech_duration=25.0,
                    silence_threshold=0.012,  # 작은 hesitation ('음', '어')도 발화로
                    on_chunk_rms=rms_cb,
                )
                if audio.size == 0:
                    empty_streak += 1
                    if empty_streak >= 3:
                        if not no_speak:
                            _say(f"쉬겠습니다 {_OWNER}")
                        break
                    continue
                empty_streak = 0

                hud.set_state("analyzing", "transcribe")
                command_text = transcribe(
                    audio, language=tx_lang, model_name=main_model
                ).strip()
                if not command_text:
                    continue
                console.print(f"[green]> {command_text}[/green]")

                # 종료어 체크 (변종 다양화)
                low = command_text.lower().strip(" .!?,~")
                exit_match = any(kw in low for kw in EXIT_KEYWORDS)
                # 한국어 변종 추가 매칭 — Whisper transcribe 변동 흡수
                if not exit_match:
                    norm = low.replace(" ", "").replace(",", "")
                    for kw in ("꺼져", "꺼지", "사라져", "사라지", "그만", "종료", "잘자"):
                        if kw in norm:
                            exit_match = True
                            break
                if exit_match:
                    if not no_speak:
                        _say(f"알겠습니다 {_OWNER}")
                    break

                # run_agent → 답변
                response = run_agent(
                    command_text, max_turns=8, verbose=False, console=console
                )
                console.print(f"[bold]자비스:[/bold] {response}")
                if response and not no_speak:
                    hud.set_state("speaking", "answer")
                    _say(response[:400])

            # multi-turn 종료 — lock OFF + idle
            hud.set_state("idle")
            _write_lock(False)

            # 종료 후 cool-down — 사용자가 마우스 떠나야만 새 wake (hallucinate 방지)
            console.print("[dim](종료 — 마우스를 노치에서 치워야 다음 wake[/dim]")
            cool_down_until = _time.time() + 2.5
            while _time.time() < cool_down_until:
                _time.sleep(0.2)
            # hover OFF 강제 대기 — 사용자가 마우스 노치에서 치울 때까지
            while _is_hover_active():
                _time.sleep(0.3)
            # 추가 안정화 대기 (hover OFF 후 0.5초)
            _time.sleep(0.5)
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
    """Übersicht 앱 시작 (위젯 자동 로드). macOS 전용."""
    import os as _os
    from jarvis.platform import IS_MACOS, os_label

    if not IS_MACOS:
        console.print(
            f"[yellow]HUD widget(Übersicht)은 macOS 전용 — {os_label()}에서 미지원.[/yellow]\n"
            "[dim]Windows/Linux: HUD 상태 파일은 작성되지만 위젯은 표시 안 됨. "
            "v0.5.x에서 cross-platform HUD 예정.[/dim]"
        )
        return

    apps = _os.popen("ls /Applications/ 2>/dev/null").read()
    if "bersicht" not in apps:
        console.print("[red]Übersicht 미설치 — `brew install --cask ubersicht`[/red]")
        return
    _os.system("open /Applications/*bersicht*.app")
    console.print("OK: Übersicht 시작")


@hud_app.command("stop")
def hud_stop() -> None:
    """Übersicht 종료. macOS 전용."""
    import os as _os
    from jarvis.platform import IS_MACOS, os_label

    if not IS_MACOS:
        console.print(f"[yellow]Übersicht은 macOS 전용 — {os_label()}에서 미지원.[/yellow]")
        return

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


@plugin_app.command("install")
def plugin_install(
    source: str = typer.Argument(
        ..., help="GitHub repo URL (https://github.com/user/repo) 또는 파일 URL (https://...py)"
    ),
    name: str = typer.Option("", "--name", help="저장 파일명 override (기본: URL 끝)"),
) -> None:
    """플러그인을 URL/GitHub repo에서 ~/.jarvis/plugins/ 에 설치.

    안전: 사용자 플러그인은 임의 Python 코드 — 신뢰하는 source만 설치.
    GitHub repo 입력 시 main 브랜치의 plugin.py 또는 단일 .py 파일 자동 감지.
    """
    import re
    import urllib.request
    from pathlib import Path

    plugin_dir = Path.home() / ".jarvis" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # 보안 경고
    console.print("[yellow]⚠ 플러그인은 임의 Python 코드를 실행합니다.[/yellow]")
    console.print(f"[yellow]  source: {source}[/yellow]")
    confirm = Prompt.ask("계속? (y/N)", default="N")
    if confirm.lower() not in ("y", "yes"):
        console.print("취소.")
        return

    # GitHub repo URL → raw file URL 변환
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", source)
    if m:
        user, repo = m.group(1), m.group(2)
        # 우선순위: plugin.py → jarvis_plugin.py → main.py → repo이름.py
        candidates = [
            f"https://raw.githubusercontent.com/{user}/{repo}/main/plugin.py",
            f"https://raw.githubusercontent.com/{user}/{repo}/main/jarvis_plugin.py",
            f"https://raw.githubusercontent.com/{user}/{repo}/main/{repo}.py",
        ]
        url = None
        for u in candidates:
            try:
                with urllib.request.urlopen(u, timeout=5) as r:
                    if r.status == 200:
                        url = u
                        break
            except Exception:
                continue
        if not url:
            console.print(f"[red]repo에서 plugin.py 또는 {repo}.py 찾을 수 없음[/red]")
            return
        out_name = name or f"{repo}.py"
    else:
        url = source
        out_name = name or url.rsplit("/", 1)[-1]
        if not out_name.endswith(".py"):
            out_name += ".py"

    target = plugin_dir / out_name
    if target.exists():
        if Prompt.ask(f"{target.name} 이미 존재 — 덮어쓸까? (y/N)", default="N").lower() not in ("y", "yes"):
            return

    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = r.read().decode("utf-8")
    except Exception as e:
        console.print(f"[red]다운로드 실패: {e}[/red]")
        return

    target.write_text(data, encoding="utf-8")
    console.print(f"[green]OK: {target} ({len(data)}B)[/green]")
    console.print("[dim]plugin reload 또는 daemon 재시작으로 활성화[/dim]")


@plugin_app.command("remove")
def plugin_remove(name: str = typer.Argument(..., help="플러그인 파일명 (확장자 제외)")) -> None:
    """플러그인 제거 (~/.jarvis/plugins/<name>.py 삭제)."""
    from pathlib import Path

    plugin_dir = Path.home() / ".jarvis" / "plugins"
    target = plugin_dir / (name if name.endswith(".py") else f"{name}.py")
    if not target.exists():
        console.print(f"[red]없음: {target}[/red]")
        return
    if Prompt.ask(f"{target.name} 삭제? (y/N)", default="N").lower() in ("y", "yes"):
        target.unlink()
        console.print(f"[green]OK: 제거됨[/green]")


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
    detect_model: str = typer.Option("tiny", "--detect-model"),
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


@app.command()
def init() -> None:
    """첫 실행 마법사 — API 키, 마이크, 권한, daemon 등록 안내."""
    from pathlib import Path

    console.print("[bold cyan]자비스 첫 실행 마법사[/bold cyan]\n")

    # 1) API 키
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if not env_path.exists():
        env_path.write_text("ANTHROPIC_API_KEY=\nJARVIS_MODEL=claude-opus-4-7\n", encoding="utf-8")
    cur = env_path.read_text(encoding="utf-8")
    if "ANTHROPIC_API_KEY=" in cur and not cur.split("ANTHROPIC_API_KEY=", 1)[1].split("\n", 1)[0].strip().startswith("sk-"):
        key = Prompt.ask("[1/4] ANTHROPIC_API_KEY (입력 후 Enter, 비우면 건너뜀)", default="")
        if key.strip():
            new = "\n".join(
                line if not line.startswith("ANTHROPIC_API_KEY=") else f"ANTHROPIC_API_KEY={key.strip()}"
                for line in cur.splitlines()
            )
            env_path.write_text(new + "\n", encoding="utf-8")
            console.print("[green]  ✔ .env 저장[/green]")
    else:
        console.print("[green][1/4] ANTHROPIC_API_KEY 이미 설정됨[/green]")

    # 2) 호칭
    owner = Prompt.ask("[2/4] 사용자 호칭 (예: 민지님 / Boss / 주인님)", default="주인님")
    if owner and owner != "주인님":
        with env_path.open("a", encoding="utf-8") as f:
            f.write(f"JARVIS_OWNER_NAME={owner}\n")
        console.print(f"[green]  ✔ 호칭: {owner}[/green]")

    # 3) memory.md 안내
    memo = Path.home() / ".jarvis" / "memory.md"
    memo.parent.mkdir(parents=True, exist_ok=True)
    if not memo.exists():
        from jarvis.assistant import _MEMORY_TEMPLATE
        memo.write_text(_MEMORY_TEMPLATE, encoding="utf-8")
        console.print(f"[green][3/4] 메모 템플릿 생성: {memo}[/green]")
        console.print("[dim]  → 사용자 정체성·선호를 적어두면 모든 세션에서 참조됨[/dim]")
    else:
        console.print(f"[green][3/4] 메모 이미 존재: {memo}[/green]")

    # 4) macOS 권한 + daemon 안내
    console.print("[yellow][4/4] macOS 권한 + daemon 등록[/yellow]")
    console.print("  • 권한 트리거:  [bold]jarvis permissions[/bold]")
    console.print("  • 진단:         [bold]jarvis doctor[/bold]")
    console.print("  • daemon 시작:  [bold]jarvis daemon install[/bold]")

    console.print("\n[bold green]초기화 완료.[/bold green] 동작 확인:  [cyan]jarvis ask \"안녕\"[/cyan]")


@app.command()
def doctor() -> None:
    """진단 — API 키 / 마이크 / 의존성 / launchd 상태 / HUD 검사."""
    import importlib
    import shutil
    import subprocess as _sp
    from pathlib import Path

    console.print("[bold cyan]자비스 진단 (jarvis doctor)[/bold cyan]")
    ok = lambda m: console.print(f"[green]  ✔[/green] {m}")
    bad = lambda m: console.print(f"[red]  ✗[/red] {m}")

    # 1) API key
    from jarvis.config import settings as _s
    if _s.anthropic_api_key.startswith("sk-"):
        ok(f"ANTHROPIC_API_KEY (앞: {_s.anthropic_api_key[:10]}…)")
    else:
        bad("ANTHROPIC_API_KEY 미설정 — .env 또는 jarvis init")

    # 2) Python 의존성
    for mod in ("anthropic", "typer", "rich", "sounddevice", "numpy", "faster_whisper"):
        try:
            importlib.import_module(mod)
            ok(f"의존성: {mod}")
        except ImportError:
            bad(f"의존성: {mod} (pip install -e .)")

    # 3) 마이크
    try:
        import sounddevice as _sd
        devs = _sd.query_devices()
        in_devs = [d for d in devs if d.get("max_input_channels", 0) > 0]
        if in_devs:
            ok(f"마이크 입력 장치 {len(in_devs)}개 — 기본: {_sd.default.device}")
        else:
            bad("마이크 입력 장치 없음")
    except Exception as e:
        bad(f"마이크 query 실패: {e}")

    # 4) launchd daemon
    try:
        out = _sp.run(
            ["launchctl", "list"], capture_output=True, text=True, timeout=3
        ).stdout
        if "com.swxvno.jarvis" in out or "jarvis.wake" in out:
            ok("launchd daemon 등록됨")
        else:
            bad("launchd daemon 미등록 — jarvis daemon install")
    except Exception:
        bad("launchctl 실행 실패")

    # 5) HUD
    if shutil.which("swift"):
        ok("swift toolchain 발견")
    else:
        bad("swift 없음 — Xcode Command Line Tools 설치")
    hud_bin = Path.home() / "jarvis" / "hud-overlay" / ".build" / "release" / "JarvisHUD"
    if hud_bin.exists():
        ok(f"JarvisHUD 빌드됨: {hud_bin}")
    else:
        # 다른 위치 시도
        proj_hud = Path(__file__).resolve().parents[2] / "hud-overlay" / ".build" / "release" / "JarvisHUD"
        if proj_hud.exists():
            ok(f"JarvisHUD 빌드됨: {proj_hud}")
        else:
            bad("JarvisHUD 미빌드 — cd hud-overlay && swift build -c release")

    # 6) memory.md
    memo = Path.home() / ".jarvis" / "memory.md"
    if memo.exists():
        ok(f"~/.jarvis/memory.md ({memo.stat().st_size}B)")
    else:
        bad("~/.jarvis/memory.md 없음 — jarvis init")

    console.print()


@app.command()
def permissions() -> None:
    """macOS 자동화 권한 다이얼로그 일괄 트리거 (Calendar/Reminders/Music/Mail)."""
    import subprocess as _sp

    console.print("[bold cyan]macOS 자동화 권한 트리거[/bold cyan]")
    console.print("[dim]각 앱에 대한 권한 다이얼로그가 뜸. 모두 '허용' 누르시오.[/dim]\n")

    targets = [
        ("Calendar", 'tell application "Calendar" to count calendars'),
        ("Reminders", 'tell application "Reminders" to count lists'),
        ("Music", 'tell application "Music" to player state'),
        ("Mail", 'tell application "Mail" to count accounts'),
        ("Finder", 'tell application "Finder" to count items in home'),
        ("System Events", 'tell application "System Events" to count processes'),
    ]
    for name, script in targets:
        try:
            r = _sp.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                console.print(f"[green]  ✔[/green] {name}")
            else:
                console.print(f"[yellow]  ⚠[/yellow] {name} — {r.stderr.strip()[:80]}")
        except Exception as e:
            console.print(f"[red]  ✗[/red] {name} — {e}")

    console.print("\n[dim]시스템 환경설정 → 개인정보 보호 → 자동화에서 자비스 항목 확인 가능.[/dim]")


if __name__ == "__main__":
    app()
