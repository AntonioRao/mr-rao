"""System tray icon for Mr. Rao (optional — requires pystray)."""
from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

import config


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
    # fallback solid
    return Image.new("RGBA", (64, 64), (59, 130, 246, 255))


def run_tray(url: str, on_quit) -> None:
    """Block on tray loop (call from main thread on Windows)."""
    try:
        import pystray
        from pystray import MenuItem as Item
    except ImportError:
        print("pystray non installato — tray disabilitato. pip install pystray")
        return

    def open_ui(icon=None, item=None):
        webbrowser.open(url)

    def open_watch_hint(icon=None, item=None):
        webbrowser.open(url + "#watch")

    def quit_app(icon, item):
        icon.stop()
        on_quit()

    image = _load_icon_image()
    menu = pystray.Menu(
        Item(f"Apri {config.APP_NAME}", open_ui, default=True),
        Item("Hotfolder (UI)", open_watch_hint),
        Item("Esci", quit_app),
    )
    icon = pystray.Icon("mr-rao", image, config.APP_NAME, menu)
    icon.run()


def start_tray_thread(url: str, on_quit) -> threading.Thread | None:
    try:
        import pystray  # noqa: F401
    except ImportError:
        return None

    t = threading.Thread(target=run_tray, args=(url, on_quit), daemon=True, name="mr-rao-tray")
    t.start()
    return t
