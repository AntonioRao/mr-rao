# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Cartelle di lavoro predefinite + selettore nativo di cartelle (uso locale).

Regola non negoziabile: Mr. Rao promette «100% locale, zero cloud», quindi le
cartelle di lavoro predefinite non devono finire dentro OneDrive, Dropbox o
simili. Su Windows con Known Folder Move «Documenti» È la cartella OneDrive,
quindi non basta cambiare l'ordine dei candidati: va riconosciuta la
sincronizzazione e, in quel caso, si ripiega su una cartella locale.
"""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path

# I dialog nativi (tkinter) non sono rientranti tra thread.
_dialog_lock = threading.Lock()

FOLDER_APP = "Mr Rao"
FOLDER_INBOX = "Da convertire"
FOLDER_OUTBOX = "Convertiti"

# Nomi di cartella che indicano una radice sincronizzata col cloud.
_RE_CLOUD = re.compile(
    r"^(onedrive|dropbox|google\s?drive|icloud\s?drive|nextcloud|owncloud|pcloud|mega|box|sync\.com)",
    re.IGNORECASE,
)

# Variabili d'ambiente che puntano a radici sincronizzate.
_CLOUD_ENV = ("OneDrive", "OneDriveCommercial", "OneDriveConsumer", "Dropbox")


def cloud_roots() -> list[Path]:
    roots: list[Path] = []
    for var in _CLOUD_ENV:
        val = os.environ.get(var)
        if val:
            try:
                roots.append(Path(val).resolve())
            except OSError:
                continue
    return roots


def is_cloud_synced(path: str | Path) -> bool:
    """True se il percorso sta dentro una radice sincronizzata col cloud."""
    try:
        p = Path(path).resolve()
    except OSError:
        return False
    for root in cloud_roots():
        try:
            p.relative_to(root)
            return True
        except ValueError:
            continue
    return any(_RE_CLOUD.match(part) for part in p.parts)


def local_documents_dir() -> Path | None:
    """Documenti dell'utente, ma solo se NON è una cartella sincronizzata.

    Si guarda **una** home: `USERPROFILE` se c'è, altrimenti `HOME` /
    `Path.home()`. Un terzo candidato su `Path.home()` mentre
    `USERPROFILE` punta altrove (OneDrive redirezionato nei test, o un
    profilo spostato) pescava i Documenti di *un altro* albero e li
    trattava come locali. Su macOS `Path.home()` e `USERPROFILE` non
    coincidono: è così che la suite, verde su Windows, è diventata rossa
    sul runner Apple Silicon.
    """
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
    for candidate in (home / "Documents", home / "Documenti"):
        if candidate.is_dir() and not is_cloud_synced(candidate):
            return candidate
    return None


def app_data_dir() -> Path:
    """Cartella dati locale, mai sincronizzata: l'ultima spiaggia sicura."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / FOLDER_APP
    return Path.home() / f".{FOLDER_APP.lower().replace(' ', '-')}"


def folders_root() -> tuple[Path, str]:
    """Radice delle cartelle di lavoro + motivo della scelta (per la UI)."""
    override = os.environ.get("MR_RAO_FOLDER_ROOT")
    if override:
        return Path(override).expanduser(), "impostata con MR_RAO_FOLDER_ROOT"

    docs = local_documents_dir()
    if docs is not None:
        return docs / FOLDER_APP, "cartella Documenti locale"

    return (
        app_data_dir(),
        "Documenti risulta sincronizzata col cloud: uso una cartella locale "
        "per non far uscire i file dal computer",
    )


def default_watch_paths() -> tuple[Path, Path]:
    root, _ = folders_root()
    return root / FOLDER_INBOX, root / FOLDER_OUTBOX


def describe_default_folders() -> dict[str, object]:
    """Percorsi predefiniti senza crearli (per le risposte in sola lettura)."""
    root, reason = folders_root()
    inbox, outbox = default_watch_paths()
    return {
        "app_root": str(root),
        "inbox": str(inbox),
        "outbox": str(outbox),
        "reason": reason,
        "cloud_synced": is_cloud_synced(root),
        "exists": inbox.is_dir() and outbox.is_dir(),
    }


def ensure_default_watch_folders() -> dict[str, object]:
    """Crea le cartelle predefinite se mancano. Solo da richieste che
    modificano stato: una GET non deve toccare il disco."""
    inbox, outbox = default_watch_paths()
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    info = describe_default_folders()
    info["exists"] = True
    return info


def browse_folder(initial: str | None = None, title: str = "Scegli cartella") -> str | None:
    """Apre il selettore di cartelle di sistema. Restituisce il percorso, o
    None se l'utente annulla **o se non c'è un ambiente grafico** (server
    headless, container): in quel caso tkinter fallisce alla creazione della
    finestra, non all'import, quindi va protetta anche quella.
    """
    with _dialog_lock:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception:
            return None

        try:
            root = tk.Tk()
        except Exception:  # nessun display / Tcl assente
            return None

        try:
            root.withdraw()
            root.attributes("-topmost", True)
            # CodeQL py/path-injection (alert 8): `initial` arriva dalla
            # richiesta, ma qui decide soltanto *dove si apre* una finestra di
            # dialogo. Non legge, non scrive, non crea niente: il percorso che
            # conta e' quello che la persona sceglie cliccando, e senza quel
            # clic la funzione restituisce None.
            init = initial if initial and Path(initial).is_dir() else str(folders_root()[0])
            path = filedialog.askdirectory(
                parent=root, initialdir=init, title=title, mustexist=True
            )
            return path or None
        except Exception:
            return None
        finally:
            try:
                root.destroy()
            except Exception:
                pass
