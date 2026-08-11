"""Mr. Rao — entry point for the local web server (dev + portable exe).

Copyright (C) 2026 Antonio Andrea Rao

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

# **Questo import viene prima degli altri, e non e' disordine.** L'eseguibile
# e' costruito senza console (`console=False` in `MrRao.spec`), quindi al
# doppio click non compare nessuna finestra nera. Ma quando c'e' un comando da
# eseguire la console del terminale che ci ha lanciati va agganciata **prima**
# che qualunque altro modulo stampi o configuri un handler di logging: quelle
# righe finirebbero nel vuoto, e il comando sembrerebbe non aver fatto niente.
import console_win  # noqa: E402

console_win.aggancia()

import sys  # noqa: E402
import threading  # noqa: E402
import webbrowser  # noqa: E402

import config  # noqa: E402
from mr_rao import create_app  # noqa: E402

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


def _decidi_porta():
    """Scegli la porta e dillo, invece di sovrapporsi in silenzio.

    Su Windows il bind su una porta occupata riesce comunque (SO_REUSEADDR):
    senza questo controllo l'app apre il browser su un server altrui — tipico
    caso: una vecchia versione installata ancora in esecuzione.

    La scelta vera sta in `mr_rao.portcheck.decidi_avvio`, che si può provare
    senza alzare un server; qui resta solo l'effetto — stampare, e uscire
    quando non c'è niente da avviare.
    """
    from mr_rao.portcheck import RINUNCIA, decidi_avvio

    d = decidi_avvio(config.HOST, config.PORT, config.APP_VERSION)
    if d.righe:
        _safe_print("")
        for riga in d.righe:
            _safe_print(riga)
        _safe_print("")
    if d.azione == RINUNCIA:
        raise SystemExit(1)
    return d


if __name__ == "__main__":
    # CLI first (portable exe: convert / watch / health / dropped files)
    # La condizione e' **la stessa** che ha deciso se agganciare la console:
    # se qui si scrivesse `len(sys.argv) > 1` a mano, un domani qualcuno
    # potrebbe cambiarne una sola, e si otterrebbe o una finestra nera per un
    # avvio che non stampa niente, o un comando che stampa senza console --
    # cioe' muto.
    if console_win.serve_console() and sys.argv[1] in (
            "convert", "watch", "health", "--help", "-h"):
        from mr_rao.cli import main as cli_main

        raise SystemExit(cli_main(sys.argv[1:]))

    if console_win.serve_console() and not sys.argv[1].startswith("-"):
        from mr_rao.cli import main as cli_main

        raise SystemExit(cli_main(["convert", *sys.argv[1:]]))

    _safe_print(f"{config.APP_NAME} v{config.APP_VERSION}")
    decisione = _decidi_porta()
    port = decisione.porta
    from mr_rao.portcheck import RIUSA, connect_host

    url = f"http://{connect_host(config.HOST)}:{port}"

    if decisione.azione == RIUSA:
        # Nessun server, nessuna icona nella barra, nessun tentativo di
        # registrare la scorciatoia (che è esclusiva: il secondo processo la
        # perderebbe in silenzio). Si apre la finestra e si esce con 0 —
        # perché non è successo niente di sbagliato: era già tutto acceso.
        _safe_print(f"-> {url}")
        if config.OPEN_BROWSER:
            webbrowser.open(url)
        raise SystemExit(0)

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
