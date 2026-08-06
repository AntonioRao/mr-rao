"""In-process hotfolder watch (shared by CLI, API, tray)."""
from __future__ import annotations

import os
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
    message: str = "non attiva"
    options: ConvertOptions = field(default_factory=ConvertOptions)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # dict, not set: insertion order lets us drop the oldest keys. A long-running
    # hotfolder would otherwise grow this forever.
    _seen: dict[str, float] = field(default_factory=dict, repr=False)

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

MAX_SEEN = 5000


def get_watch_state() -> dict[str, Any]:
    return _state.to_dict()


def _remember(key: str) -> None:
    """Record a processed file, keeping the memory bounded."""
    _state._seen[key] = time.time()
    if len(_state._seen) > MAX_SEEN:
        for old in list(_state._seen)[: MAX_SEEN // 2]:
            del _state._seen[old]


def write_atomic(dest: Path, text: str) -> None:
    """Scrive su un file temporaneo e poi rinomina.

    Una scrittura diretta lascia un .md troncato se il processo muore a metà
    (spegnimento, chiusura forzata): chi legge la cartella di uscita non ha
    modo di accorgersene. Col rename il file o c'è intero o non c'è.
    """
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dest)


def output_path_for(outbox: Path, source: Path) -> Path:
    """Pick a free .md name for a source file.

    'a.pdf' and 'a.docx' both wanted 'a.md', so the second silently overwrote
    the first. Disambiguate with the original extension, then a counter.
    """
    candidate = outbox / (source.stem + ".md")
    if not candidate.exists():
        return candidate
    with_ext = outbox / f"{source.stem}-{source.suffix.lstrip('.').lower()}.md"
    if not with_ext.exists():
        return with_ext
    for n in range(2, 1000):
        numbered = outbox / f"{with_ext.stem}-{n}.md"
        if not numbered.exists():
            return numbered
    return with_ext


def start_watch(
    inbox: str | Path,
    outbox: str | Path,
    options: ConvertOptions | None = None,
    interval: float = 2.0,
    move_done: bool = False,
) -> dict[str, Any]:
    stop_watch()
    # CodeQL py/path-injection (alert 9 e 10): questi percorsi arrivano dalla
    # richiesta e non sono confinati. Non e' una svista, e' la funzione: la
    # cartella sorvegliata deve poter stare nei Documenti o su un disco di
    # rete, e l'interfaccia ha un selettore di cartelle nativo apposta.
    #
    # Il presidio non e' un recinto sul percorso -- che romperebbe l'uso -- ma
    # il fatto che nessuna pagina esterna possa arrivare a questo endpoint:
    # vedi _register_guards in app_factory.py. E la scrittura produce solo
    # file .md, senza mai sovrascriverne uno esistente (output_path_for).
    #
    # Se un giorno questo diventasse raggiungibile senza il controllo
    # cross-site, o iniziasse a scrivere qualcosa di diverso da .md, l'alert
    # va riaperto: l'assunzione sarebbe cambiata.
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
        _state.message = "in attesa di file"
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
        _state.message = "ferma"
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
                    _state.last_error = "La cartella da sorvegliare non esiste piu'"
                    _state.message = "cartella da sorvegliare non valida"
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
                        _state.message = f"sto convertendo {path.name}"
                        _state.last_file = path.name
                    r = convert_file(path, options=opts)
                    with _state._lock:
                        _remember(key)
                    if r.error:
                        with _state._lock:
                            _state.last_error = r.error
                            _state.message = f"Errore: {path.name}"
                        continue
                    dest = output_path_for(outbox, path)
                    write_atomic(dest, r.markdown)
                    with _state._lock:
                        _state.processed += 1
                        _state.message = f"fatto: {path.name}"
                        _state.last_error = ""
                    if move_done:
                        done = inbox / "done"
                        done.mkdir(exist_ok=True)
                        try:
                            path.rename(done / path.name)
                        except OSError as e:
                            with _state._lock:
                                _state.last_error = f"Non riesco a spostare l'originale: {e}"
        except Exception as e:
            with _state._lock:
                _state.last_error = str(e)
                _state.message = "errore durante la sorveglianza"
        # sleep in chunks for responsive stop
        for _ in range(int(_state.interval * 10)):
            if _state._stop.is_set():
                break
            time.sleep(0.1)
    with _state._lock:
        _state.running = False
        _state.message = "ferma"
