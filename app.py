"""Mr. Rao — entry point for the local web server (dev + portable exe)."""
from __future__ import annotations

import sys
import threading
import webbrowser

import config
from mr_rao import create_app

app = create_app()


def _run_server():
    # threaded=True so tray/UI and conversions can overlap
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    print(f"{config.APP_NAME} v{config.APP_VERSION}")
    url = f"http://{config.HOST}:{config.PORT}"
    print(f"→ {url}")
    print(f"   debug={config.DEBUG} tray={config.USE_TRAY} frozen={getattr(sys, 'frozen', False)}")

    # CLI args: convert / watch without starting server
    if len(sys.argv) > 1 and sys.argv[1] in ("convert", "watch", "health", "--help", "-h"):
        from mr_rao.cli import main as cli_main

        raise SystemExit(cli_main(sys.argv[1:]))

    # Files dropped on the exe → convert CLI style then exit
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        from pathlib import Path

        from mr_rao.cli import main as cli_main

        args = ["convert", *sys.argv[1:]]
        raise SystemExit(cli_main(args))

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

            # pystray wants main thread on some platforms; run tray here and server in bg
            run_tray(url, on_quit)
        except Exception as e:
            print(f"Tray non disponibile ({e}). Server attivo su {url} — Ctrl+C per uscire.")
            try:
                stop_event.wait()
            except KeyboardInterrupt:
                pass
    else:
        try:
            while server.is_alive():
                server.join(timeout=1.0)
        except KeyboardInterrupt:
            print("\nArresto Mr. Rao…")
