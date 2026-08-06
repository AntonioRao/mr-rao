"""Mr. Rao — entry point for the local web server (dev + portable exe).

Copyright (C) 2026 Rao

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License along
with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
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


def _run_server(port: int):
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=port,
        use_reloader=False,
        threaded=True,
    )


def _resolve_port() -> int:
    """Scegli una porta libera e dillo, invece di sovrapporsi in silenzio.

    Su Windows il bind su una porta occupata riesce comunque (SO_REUSEADDR):
    senza questo controllo l'app apre il browser su un server altrui — tipico
    caso: una vecchia versione installata ancora in esecuzione.
    """
    from mr_rao.portcheck import describe_occupant, find_free_port, port_in_use

    port = config.PORT
    if not port_in_use(config.HOST, port):
        return port

    occupante = describe_occupant(config.HOST, port) or "un altro programma"
    libera = find_free_port(config.HOST, port + 1)
    _safe_print("")
    _safe_print(f"!! La porta {port} e' gia' occupata da: {occupante}")
    if libera is None:
        _safe_print("!! Nessuna porta libera trovata. Chiudi l'altra istanza e riprova.")
        raise SystemExit(1)
    _safe_print(f"!! Se volevi usare quella, chiudi prima l'altra istanza.")
    _safe_print(f"-> Questa istanza parte sulla porta {libera}.")
    _safe_print("")
    return libera


if __name__ == "__main__":
    # CLI first (portable exe: convert / watch / health / dropped files)
    if len(sys.argv) > 1 and sys.argv[1] in ("convert", "watch", "health", "--help", "-h"):
        from mr_rao.cli import main as cli_main

        raise SystemExit(cli_main(sys.argv[1:]))

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        from mr_rao.cli import main as cli_main

        raise SystemExit(cli_main(["convert", *sys.argv[1:]]))

    _safe_print(f"{config.APP_NAME} v{config.APP_VERSION}")
    port = _resolve_port()
    from mr_rao.portcheck import connect_host

    url = f"http://{connect_host(config.HOST)}:{port}"
    _safe_print(f"-> {url}")
    _safe_print(
        f"   debug={config.DEBUG} tray={config.USE_TRAY} frozen={getattr(sys, 'frozen', False)}"
    )

    server = threading.Thread(
        target=_run_server, args=(port,), daemon=True, name="mr-rao-http"
    )
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
