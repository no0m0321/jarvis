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
    buffer: "list[str]" = []
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
    buffer: "list[str]" = []
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
    lang: str = typer.Option("ko", "--lang"),
    chime: bool = typer.Option(True, "--chime/--no-chime", help="wake 응답 음성"),
) -> None:
    """Wake word 대기 모드. '자비스'라고 부르면 명령 받을 준비."""
    from jarvis import hud
    from jarvis.tools.macos import _say
    from jarvis.voice import (
        DEFAULT_WAKE_WORDS,
        capture_phrase,
        listen_for_wake,
        strip_wake,
        transcribe,
    )

    wake_words = list(DEFAULT_WAKE_WORDS)
    if word:
        wake_words.insert(0, word)

    assistant = JarvisAssistant()
    history: "list[dict]" = []

    console.print("[bold cyan]자비스 wake 모드 대기.[/bold cyan]")
    console.print(f"[dim]호출어: {', '.join(wake_words[:4])}... | Ctrl+C 종료[/dim]")

    try:
        while True:
            hud.set_state("idle")
            heard = listen_for_wake(
                wake_words=wake_words,
                detection_model=detect_model,
                language=lang,
            )
            console.print(f"\n[bold magenta]wake → {heard}[/bold magenta]")
            hud.set_state("listening", "command")

            command_text = strip_wake(heard, wake_words).strip()

            if not command_text:
                if chime and not no_speak:
                    hud.set_state("speaking", "ack")
                    _say("네", voice="Yuna")
                console.print("[dim]말씀하시오...[/dim]")
                hud.set_state("listening", "command")
                audio = capture_phrase(silence_duration=1.5, max_speech_duration=15.0)
                if audio.size == 0:
                    console.print("[yellow](명령 없음)[/yellow]")
                    continue
                hud.set_state("analyzing", "transcribe")
                command_text = transcribe(audio, language=lang, model_name=main_model).strip()

            if not command_text:
                console.print("[yellow](전사 결과 없음)[/yellow]")
                continue
            console.print(f"[green]> {command_text}[/green]")

            history.append({"role": "user", "content": command_text})
            buffer: "list[str]" = []
            console.print("[dim]자비스:[/dim] ", end="")
            for chunk in assistant.stream(history):
                console.print(chunk, end="")
                buffer.append(chunk)
            console.print()
            response = "".join(buffer)
            history.append({"role": "assistant", "content": response})
            if not no_speak:
                hud.set_state("speaking", "answer")
                _say(response, voice="Yuna")
                hud.set_state("idle")
    except KeyboardInterrupt:
        console.print("\n[dim]세션 종료.[/dim]")
    finally:
        hud.set_state("idle")


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
    history: "list[dict]" = []
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
            buffer: "list[str]" = []
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
    history: "list[dict]" = []
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
        buffer: "list[str]" = []
        for chunk in assistant.stream(history):
            console.print(chunk, end="")
            buffer.append(chunk)
        console.print()
        history.append({"role": "assistant", "content": "".join(buffer)})


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
