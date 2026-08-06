"""Mr. Rao — entry point for the local web server (dev + portable exe)."""
from __future__ import annotations

import sys
import threading
import webbrowser

import config
from mr_rao import create_app

app = create_app()


def _safe_print(msg: str) -> None:
    """Avoid UnicodeEncodeError on Windows cp1252 consoles."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def _run_server():
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    # CLI first (portable exe: convert / watch / health / dropped files)
    if len(sys.argv) > 1 and sys.argv[1] in ("convert", "watch", "health", "--help", "-h"):
        from mr_rao.cli import main as cli_main

        raise SystemExit(cli_main(sys.argv[1:]))

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        from mr_rao.cli import main as cli_main

        raise SystemExit(cli_main(["convert", *sys.argv[1:]]))

    url = f"http://{config.HOST}:{config.PORT}"
    _safe_print(f"{config.APP_NAME} v{config.APP_VERSION}")
    _safe_print(f"-> {url}")
    _safe_print(
        f"   debug={config.DEBUG} tray={config.USE_TRAY} frozen={getattr(sys, 'frozen', False)}"
    )

    server = threading.Thread(target=_run_server, daemon=True, name="mr-rao-http")
    server.start()

    if config.OPEN_BROWSER:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    stop_event = threading.Event()

    def on_quit():
        stop_event.set()

    if config.USE_TRAY:
        try:
            from mr_rao.tray import run_tray

            run_tray(url, on_quit)
        except Exception as e:
            _safe_print(f"Tray unavailable ({e}). Server on {url} - Ctrl+C to exit.")
            try:
                stop_event.wait()
            except KeyboardInterrupt:
                pass
    else:
        try:
            while server.is_alive():
                server.join(timeout=1.0)
        except KeyboardInterrupt:
            _safe_print("Stopping Mr. Rao...")
