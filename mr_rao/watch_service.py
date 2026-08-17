# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
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
from mr_rao.i18n import t


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
    # Anche questi messaggi finiscono sotto gli occhi di chi guarda la
    # pagina, e il thread che li scrive non ha nessuna richiesta intorno:
    # la lingua gliela porta ConvertOptions, come al testo dei documenti.
    message: str = field(default_factory=lambda: t("watch_msg_non_attivo"))
    options: ConvertOptions = field(default_factory=ConvertOptions)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # dict, not set: insertion order lets us drop the oldest keys. A long-running
    # hotfolder would otherwise grow this forever.
    _seen: dict[str, float] = field(default_factory=dict, repr=False)
    # L'impronta vista al giro precedente, per ogni file ancora nella cartella:
    # e' cosi' che si capisce se un file e' fermo o sta ancora arrivando.
    # Non cresce come _seen: contiene solo i file che ci sono adesso.
    _in_arrivo: dict[str, tuple[int, int]] = field(default_factory=dict, repr=False)

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


def _impronta(path: Path) -> tuple[int, int] | None:
    """Dimensione e orario di modifica: cosa serve per dire «questo file e' fermo».

    La sola dimensione non basta. Un file riscritto in casa -- stessa
    lunghezza, contenuto diverso -- la lascia identica, e l'orario di modifica
    era gia' li' sotto gli occhi: la cartella sorvegliata lo usa da sempre
    nella chiave per non riconvertire due volte lo stesso file.

    None se il file e' sparito fra un'occhiata e l'altra: succede, ed e' un
    esito normale, non un errore.
    """
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns)


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
    # cartella monitorata deve poter stare nei Documenti o su un disco di
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
        _state.message = t("watch_msg_in_attesa", _state.options.lingua)
        _state._seen.clear()
        _state._in_arrivo.clear()
        # Segnale di stop *nuovo*, non lo stesso riazzerato: `stop_watch()`
        # aspetta il thread precedente al massimo 3 secondi, e una conversione
        # piu' lunga di cosi' (un PDF con OCR ci mette molto di piu') lo lascia
        # vivo. Con un segnale condiviso, quel `clear()` gli diceva di
        # ricominciare: il vecchio giro tornava a lavorare sullo stato del
        # nuovo, e restavano due cartelle sorvegliate al posto di una --
        # per sempre, fino al prossimo stop. Ora il segnale gia' alzato resta
        # alzato per chi lo stava guardando, e quel thread muore appena finisce
        # il file che aveva per le mani.
        _state._stop = threading.Event()
        stop = _state._stop
        _state.running = True
        # `thread`, non `t`: `t` e' la funzione delle traduzioni, e una
        # variabile locale con lo stesso nome la renderebbe irraggiungibile
        # *in tutta la funzione* -- anche nelle righe qui sopra, che vengono
        # prima dell'assegnamento.
        thread = threading.Thread(
            target=_loop, args=(stop,), daemon=True, name="mr-rao-watch"
        )
        _state._thread = thread
        thread.start()
    return get_watch_state()


def stop_watch() -> dict[str, Any]:
    with _state._lock:
        _state._stop.set()
        _state.running = False
        _state.message = t("watch_msg_non_attivo", _state.options.lingua)
        thread = _state._thread
    if thread and thread.is_alive():
        thread.join(timeout=3.0)
    with _state._lock:
        _state._thread = None
    return get_watch_state()


def _loop(stop: threading.Event) -> None:
    """Il giro di sorveglianza. `stop` e' il segnale *di questo giro*: se ne
    parte un altro, questo resta alzato e chi lo sta guardando esce."""
    while not stop.is_set():
        try:
            with _state._lock:
                inbox = Path(_state.inbox)
                outbox = Path(_state.outbox)
                opts = _state.options
                move_done = _state.move_done
            if not inbox.is_dir():
                with _state._lock:
                    _state.last_error = t("watch_err_cartella_sparita", opts.lingua)
                    _state.message = t("watch_msg_cartella_non_valida", opts.lingua)
            else:
                candidati: set[str] = set()
                for path in sorted(inbox.iterdir()):
                    if stop.is_set():
                        break
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                        continue
                    # skip done subfolder
                    if path.parent.name.lower() == "done":
                        continue
                    impronta = _impronta(path)
                    if impronta is None:
                        continue
                    candidati.add(path.name)
                    key = f"{path.name}:{impronta[1]}"
                    with _state._lock:
                        if key in _state._seen:
                            continue
                    # Il file puo' essere ancora in arrivo: una copia da disco
                    # di rete, uno scanner, un client di posta che salva un
                    # allegato scrivono a pezzi, con pause in mezzo. Prima si
                    # campionava la sola dimensione a 0,35 s di distanza, senza
                    # uscire dal giro: una pausa piu' lunga di cosi' -- del
                    # tutto ordinaria -- e un file scritto a meta' passava per
                    # fermo, finiva convertito, e nella cartella di uscita
                    # restava un .md con dentro mezzo documento. Ben formato,
                    # quindi invisibile.
                    #
                    # Ora l'impronta dev'essere la stessa del giro precedente:
                    # la finestra di quiete diventa l'intervallo di
                    # sorveglianza, che l'utente puo' allungare, invece di una
                    # costante che nessuna impostazione riusciva a toccare.
                    # Un file appena arrivato aspetta un giro in piu': e' il
                    # prezzo, ed e' meno caro di mezzo documento.
                    with _state._lock:
                        precedente = _state._in_arrivo.get(path.name)
                        _state._in_arrivo[path.name] = impronta
                    if precedente != impronta:
                        continue
                    with _state._lock:
                        _state.message = t("watch_msg_convertendo", opts.lingua, nome=path.name)
                        _state.last_file = path.name
                    r = convert_file(path, options=opts)
                    with _state._lock:
                        _remember(key)
                    if r.error:
                        with _state._lock:
                            _state.last_error = r.error
                            _state.message = t("watch_msg_errore_file", opts.lingua, nome=path.name)
                        continue
                    dest = output_path_for(outbox, path)
                    write_atomic(dest, r.markdown)
                    with _state._lock:
                        _state.processed += 1
                        _state.message = t("watch_msg_fatto", opts.lingua, nome=path.name)
                        _state.last_error = ""
                    if move_done:
                        done = inbox / "done"
                        done.mkdir(exist_ok=True)
                        try:
                            path.rename(done / path.name)
                        except OSError as e:
                            with _state._lock:
                                _state.last_error = t("watch_err_spostamento", opts.lingua, motivo=e)
                # Le impronte dei file che non ci sono piu' non servono a
                # nessuno: qui la memoria resta grande quanto la cartella.
                with _state._lock:
                    for sparito in set(_state._in_arrivo) - candidati:
                        del _state._in_arrivo[sparito]
        except Exception as e:
            with _state._lock:
                _state.last_error = str(e)
                _state.message = t("watch_msg_errore", _state.options.lingua)
        # sleep in chunks for responsive stop
        for _ in range(int(_state.interval * 10)):
            if stop.is_set():
                break
            time.sleep(0.1)
    with _state._lock:
        # Solo se la sorveglianza in piedi e' ancora la nostra: un giro
        # vecchio, uscito in ritardo perche' stava finendo un file, non deve
        # spegnere sulla carta quello appena acceso.
        if _state._stop is not stop:
            return
        _state.running = False
        _state.message = t("watch_msg_non_attivo", _state.options.lingua)
