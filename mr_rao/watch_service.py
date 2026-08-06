"""In-process hotfolder watch (shared by CLI, API, tray)."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import ALLOWED_EXTENSIONS
from mr_rao.converter import ConvertOptions, convert_file


@dataclass
class WatchState:
    running: bool = False
    inbox: str = ""
    outbox: str = ""
    interval: float = 2.0
    move_done: bool = False
    processed: int = 0
    last_file: str = ""
    last_error: str = ""
    message: str = "idle"
    options: ConvertOptions = field(default_factory=ConvertOptions)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _seen: set[str] = field(default_factory=set, repr=False)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "inbox": self.inbox,
                "outbox": self.outbox,
                "interval": self.interval,
                "move_done": self.move_done,
                "processed": self.processed,
                "last_file": self.last_file,
                "last_error": self.last_error,
                "message": self.message,
            }


_state = WatchState()


def get_watch_state() -> dict[str, Any]:
    return _state.to_dict()


def start_watch(
    inbox: str | Path,
    outbox: str | Path,
    options: ConvertOptions | None = None,
    interval: float = 2.0,
    move_done: bool = False,
) -> dict[str, Any]:
    stop_watch()
    inbox_p = Path(inbox).expanduser().resolve()
    outbox_p = Path(outbox).expanduser().resolve()
    inbox_p.mkdir(parents=True, exist_ok=True)
    outbox_p.mkdir(parents=True, exist_ok=True)

    with _state._lock:
        _state.inbox = str(inbox_p)
        _state.outbox = str(outbox_p)
        _state.interval = max(0.5, float(interval))
        _state.move_done = bool(move_done)
        _state.options = options or ConvertOptions()
        _state.processed = 0
        _state.last_file = ""
        _state.last_error = ""
        _state.message = "avviato"
        _state._seen.clear()
        _state._stop.clear()
        _state.running = True
        t = threading.Thread(target=_loop, daemon=True, name="mr-rao-watch")
        _state._thread = t
        t.start()
    return get_watch_state()


def stop_watch() -> dict[str, Any]:
    with _state._lock:
        _state._stop.set()
        _state.running = False
        _state.message = "fermato"
        t = _state._thread
    if t and t.is_alive():
        t.join(timeout=3.0)
    with _state._lock:
        _state._thread = None
    return get_watch_state()


def _loop() -> None:
    while not _state._stop.is_set():
        try:
            with _state._lock:
                inbox = Path(_state.inbox)
                outbox = Path(_state.outbox)
                opts = _state.options
                move_done = _state.move_done
            if not inbox.is_dir():
                with _state._lock:
                    _state.last_error = "Cartella inbox non valida"
                    _state.message = "errore inbox"
            else:
                for path in sorted(inbox.iterdir()):
                    if _state._stop.is_set():
                        break
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                        continue
                    # skip done subfolder
                    if path.parent.name.lower() == "done":
                        continue
                    try:
                        key = f"{path.name}:{path.stat().st_mtime_ns}"
                    except OSError:
                        continue
                    with _state._lock:
                        if key in _state._seen:
                            continue
                    # wait for stable size
                    try:
                        s1 = path.stat().st_size
                        time.sleep(0.35)
                        if path.stat().st_size != s1:
                            continue
                    except OSError:
                        continue
                    with _state._lock:
                        _state.message = f"Conversione {path.name}"
                        _state.last_file = path.name
                    r = convert_file(path, options=opts)
                    with _state._lock:
                        _state._seen.add(key)
                    if r.error:
                        with _state._lock:
                            _state.last_error = r.error
                            _state.message = f"Errore: {path.name}"
                        continue
                    dest = outbox / (path.stem + ".md")
                    dest.write_text(r.markdown, encoding="utf-8")
                    with _state._lock:
                        _state.processed += 1
                        _state.message = f"OK: {path.name}"
                        _state.last_error = ""
                    if move_done:
                        done = inbox / "done"
                        done.mkdir(exist_ok=True)
                        try:
                            path.rename(done / path.name)
                        except OSError as e:
                            with _state._lock:
                                _state.last_error = f"Move failed: {e}"
        except Exception as e:
            with _state._lock:
                _state.last_error = str(e)
                _state.message = "errore loop"
        # sleep in chunks for responsive stop
        for _ in range(int(_state.interval * 10)):
            if _state._stop.is_set():
                break
            time.sleep(0.1)
    with _state._lock:
        _state.running = False
        _state.message = "fermato"
