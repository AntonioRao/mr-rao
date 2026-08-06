"""Default Documenti folders + native Windows folder picker for local use."""
from __future__ import annotations

import os
import threading
from pathlib import Path

# Serialize native dialogs (tkinter is not re-entrant across threads).
_dialog_lock = threading.Lock()

# Under the current user's Documents:
#   Documenti\Mr Rao\Da convertire   → watch inbox
#   Documenti\Mr Rao\Convertiti      → watch outbox / .md output
FOLDER_APP = "Mr Rao"
FOLDER_INBOX = "Da convertire"
FOLDER_OUTBOX = "Convertiti"


def documents_dir() -> Path:
    """Windows user Documents (or ~/Documents fallback)."""
    # Prefer USERPROFILE\Documents (works even with OneDrive redirected paths
    # when the known-folder is not available via ctypes).
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    candidates = [
        home / "Documents",
        home / "Documenti",  # some Italian locale layouts
        Path.home() / "Documents",
    ]
    # OneDrive known path
    od = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
    if od:
        candidates.insert(0, Path(od) / "Documents")
        candidates.insert(1, Path(od) / "Documenti")

    for c in candidates:
        if c.is_dir():
            return c

    # Create classic Documents if missing
    docs = home / "Documents"
    docs.mkdir(parents=True, exist_ok=True)
    return docs


def default_watch_paths() -> tuple[Path, Path]:
    root = documents_dir() / FOLDER_APP
    inbox = root / FOLDER_INBOX
    outbox = root / FOLDER_OUTBOX
    return inbox, outbox


def ensure_default_watch_folders() -> dict[str, str]:
    """Create default inbox/outbox under Documenti\\Mr Rao if missing."""
    inbox, outbox = default_watch_paths()
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    return {
        "documents": str(documents_dir()),
        "app_root": str(inbox.parent),
        "inbox": str(inbox),
        "outbox": str(outbox),
    }


def browse_folder(initial: str | None = None, title: str = "Scegli cartella") -> str | None:
    """Open a native folder dialog (tkinter). Returns path or None if cancelled.

    Must run on a thread that can talk to the UI; we use a lock and withdraw
    the root window. On headless/non-Windows environments returns None.
    """
    with _dialog_lock:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception:
            return None

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            init = initial if initial and Path(initial).is_dir() else str(documents_dir())
            path = filedialog.askdirectory(
                parent=root,
                initialdir=init,
                title=title,
                mustexist=True,
            )
            return path or None
        finally:
            try:
                root.destroy()
            except Exception:
                pass
