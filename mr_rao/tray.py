# pystray is used under the GNU LGPL v3 (or later).
# Copyright (C) 2016-2022 Moses Palmér — https://github.com/moses-palmer/pystray
# Full license texts: licenses/pystray/ (COPYING.LGPL, COPYING, NOTICE.txt)
# How to replace pystray: docs/LGPL_PYSTRAY.md
# Mr. Rao's own LICENSE does not apply to pystray.
"""System tray icon for Mr. Rao (requires pystray, LGPL-3.0)."""
from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

import config

_LGPL_NOTICE_SHOWN = False


def _print_lgpl_notice() -> None:
    """LGPL requires appropriate notices when distributing; we also print at runtime."""
    global _LGPL_NOTICE_SHOWN
    if _LGPL_NOTICE_SHOWN:
        return
    _LGPL_NOTICE_SHOWN = True
    print(
        "Tray: uses pystray (LGPL-3.0), Copyright (C) 2016-2022 Moses Palmér.\n"
        "  Source: https://github.com/moses-palmer/pystray\n"
        "  License files: licenses/pystray/  |  docs/LGPL_PYSTRAY.md"
    )


def _load_icon_image():
    from PIL import Image

    candidates = [
        config.STATIC_FOLDER / "img" / "logo.png",
        config.STATIC_FOLDER / "img" / "favicon-64.png",
        config.WRITABLE_DIR / "static" / "img" / "logo.png",
    ]
    for p in candidates:
        if p.exists():
            return Image.open(p).convert("RGBA")
    return Image.new("RGBA", (64, 64), (59, 130, 246, 255))


def run_tray(url: str, on_quit) -> None:
    """Block on tray loop (call from main thread on Windows)."""
    try:
        import pystray
        from pystray import MenuItem as Item
    except ImportError:
        print("pystray non installato — tray disabilitato. pip install pystray")
        return

    _print_lgpl_notice()

    def open_ui(icon=None, item=None):
        webbrowser.open(url)

    def open_watch_hint(icon=None, item=None):
        webbrowser.open(url + "#watch")

    def quit_app(icon, item):
        icon.stop()
        on_quit()

    # La scorciatoia sugli appunti. La notifica non e' un contorno: una
    # trasformazione silenziosa non fa distinguere «ha funzionato» da «non e'
    # partito», e i sospetti sono roba che il motore ha segnalato e **non
    # tolto** -- chi incolla senza leggere incolla un dato ancora li'.
    from mr_rao import appunti as _appunti

    memoria = _appunti.Memoria()

    def _avvisa(testo: str) -> None:
        try:
            icon.notify(testo, config.APP_NAME)
        except Exception:
            # Le notifiche non sono garantite su ogni Windows: se mancano, il
            # messaggio va almeno sulla console invece di sparire.
            print(f"[{config.APP_NAME}] {testo}")

    def scorciatoia_scattata() -> None:
        esito = _appunti.passa_dagli_appunti(
            _appunti.leggi_appunti, _appunti.scrivi_appunti, memoria=memoria
        )
        _avvisa(esito.messaggio())

    def ripristina_originale(icon=None, item=None):
        esito = _appunti.ripristina(_appunti.scrivi_appunti, memoria)
        _avvisa(esito.errore or "Negli appunti c'e' di nuovo il testo originale.")

    voci = [
        Item(f"Apri {config.APP_NAME}", open_ui, default=True),
        Item("Hotfolder (UI)", open_watch_hint),
    ]
    if config.SCORCIATOIA_ATTIVA:
        voci.append(Item("Ripristina gli appunti originali", ripristina_originale))
    voci.append(Item("Esci", quit_app))

    image = _load_icon_image()
    icon = pystray.Icon("mr-rao", image, config.APP_NAME, pystray.Menu(*voci))

    if config.SCORCIATOIA_ATTIVA:
        _appunti.avvia_scorciatoia(
            config.SCORCIATOIA, scorciatoia_scattata,
            quando_fallisce=lambda m: print(f"[{config.APP_NAME}] scorciatoia: {m}"),
        )

    icon.run()


def start_tray_thread(url: str, on_quit) -> threading.Thread | None:
    try:
        import pystray  # noqa: F401
    except ImportError:
        return None

    t = threading.Thread(target=run_tray, args=(url, on_quit), daemon=True, name="mr-rao-tray")
    t.start()
    return t
