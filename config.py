"""Mr. Rao — central configuration (dev + frozen portable)."""
from __future__ import annotations

import os
import secrets
import socket
import sys
from pathlib import Path


def _base_dir() -> Path:
    # PyInstaller onefile/onedir
    if getattr(sys, "frozen", False):
        # _MEIPASS = extracted bundle; exe dir for writable data
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _writable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# Brand
APP_NAME = "Mr. Rao"
APP_SLUG = "mr-rao"
APP_TAGLINE = (
    "Converti documenti, immagini e thread email in Markdown puro. "
    "Con i dati personali già rimossi. Offline, sul tuo computer."
)
APP_VERSION = "1.18.0"

# Paths
BASE_DIR = _base_dir()
WRITABLE_DIR = _writable_dir()
UPLOAD_FOLDER = WRITABLE_DIR / "uploads"
STATIC_FOLDER = BASE_DIR / "static"
TEMPLATES_FOLDER = BASE_DIR / "templates"
if not STATIC_FOLDER.exists() and (WRITABLE_DIR / "static").exists():
    STATIC_FOLDER = WRITABLE_DIR / "static"
if not TEMPLATES_FOLDER.exists() and (WRITABLE_DIR / "templates").exists():
    TEMPLATES_FOLDER = WRITABLE_DIR / "templates"

# Server
HOST = os.environ.get("MR_RAO_HOST", "127.0.0.1")
PORT = int(os.environ.get("MR_RAO_PORT", "5000"))
DEBUG = os.environ.get("MR_RAO_DEBUG", "0").strip() in ("1", "true", "True", "yes")

# Nessuna sessione, nessun cookie firmato, nessun token: oggi la chiave non la
# usa niente. Finché è così, una chiave casuale in memoria è meglio sia della
# costante che c'era sia di un file su disco: un file seguirebbe l'eseguibile
# portable dentro OneDrive, nei backup e nello zip che passa a un collega.
# Il giorno che serviranno sessioni che sopravvivono al riavvio, quel giorno
# servirà anche persisterla — non prima.
SECRET_KEY = os.environ.get("MR_RAO_SECRET") or secrets.token_hex(32)
USE_TRAY = os.environ.get("MR_RAO_TRAY", "1").strip() not in ("0", "false", "no")
OPEN_BROWSER = os.environ.get("MR_RAO_OPEN_BROWSER", "1").strip() not in ("0", "false", "no")

# La scorciatoia che redige gli appunti sul posto: `0` la spegne, qualunque
# altra cosa e' la combinazione. **Una** variabile per due cose, perche' sono
# la stessa domanda -- «quale combinazione, o nessuna» -- e tenerle separate
# permetterebbe lo stato incoerente «accesa, combinazione vuota», che si
# manifesterebbe come una scorciatoia che non risponde senza dire perche'.
# Guida, e disinnesco della somiglianza con un keylogger:
# docs/SCORCIATOIA-APPUNTI.md
_SCORCIATOIA = os.environ.get("MR_RAO_SCORCIATOIA", "ctrl+alt+r").strip()
SCORCIATOIA_ATTIVA = _SCORCIATOIA.lower() not in ("0", "false", "no", "")
SCORCIATOIA = _SCORCIATOIA if SCORCIATOIA_ATTIVA else ""

# Security — a local server is reachable by any page the user has open in the
# browser, so the Host header is pinned (anti DNS-rebinding) and cross-site
# requests are refused (anti CSRF).
_HOST_LOCALI = "127.0.0.1,localhost,[::1],::1"


def _indirizzi_di_questa_macchina() -> str:
    """Gli host con cui questa macchina risponde legittimamente a sé e alla LAN.

    Serve solo quando si sceglie di ascoltare su 0.0.0.0. Prima, in quel caso,
    l'allow-list diventava `*`: la difesa anti DNS-rebinding spariva esattamente
    quando l'app si esponeva. Una pagina ostile che si faceva risolvere sull'IP
    della macchina tornava a poter *leggere* le risposte — cioè i documenti
    convertiti, che è tutto ciò che questa applicazione ha da proteggere.

    Elencare gli indirizzi veri invece di `*` lascia passare l'accesso legittimo
    (per IP o per nome macchina) e ferma il dominio dell'attaccante, che
    nell'header `Host` porta il proprio nome e non uno di questi.

    Dietro un reverse proxy con un nome pubblico serve MR_RAO_ALLOWED_HOSTS:
    il 403 lo dice esplicitamente invece di lasciare indovinare.
    """
    ammessi = set(_HOST_LOCALI.split(","))
    try:
        nome = socket.gethostname()
        ammessi.add(nome)
        ammessi.add(nome.split(".", 1)[0])  # NetBIOS, senza dominio
        ammessi.update(socket.gethostbyname_ex(nome)[2])
    except OSError:
        # Rete non configurata o DNS muto: si resta sul locale. È il verso
        # giusto in cui sbagliare — si perde l'accesso in LAN, non la difesa.
        pass
    return ",".join(sorted(a for a in ammessi if a))


_default_hosts = _indirizzi_di_questa_macchina() if HOST == "0.0.0.0" else _HOST_LOCALI
ALLOWED_HOSTS = {
    h.strip().lower()
    for h in os.environ.get("MR_RAO_ALLOWED_HOSTS", _default_hosts).split(",")
    if h.strip()
}

# Concurrency: one thread per request would let N uploads start N OCR runs.
MAX_WORKERS = max(1, int(os.environ.get("MR_RAO_MAX_WORKERS", "2")))
MAX_JOBS_KEPT = max(4, int(os.environ.get("MR_RAO_MAX_JOBS", "50")))

# Limits
MAX_CONTENT_LENGTH = int(os.environ.get("MR_RAO_MAX_UPLOAD_MB", "50")) * 1024 * 1024
MAX_UPLOAD_MB = MAX_CONTENT_LENGTH // (1024 * 1024)
MAX_OCR_PAGES = int(os.environ.get("MR_RAO_MAX_OCR_PAGES", "50"))
# Tetto di tempo su un OCR, in secondi (0 = nessuno). Un thread Python non si
# uccide dall'esterno, quindi questo limita **le pagine**, non la singola
# pagina: una scansione mostruosa da sola arriva comunque in fondo. Serve a
# impedire che un PDF al limite delle 50 pagine tenga occupato un worker per
# mezz'ora. Il risultato parziale viene restituito, dichiarato nel testo.
MAX_OCR_SECONDS = int(os.environ.get("MR_RAO_OCR_TIMEOUT", "900"))
OCR_DPI = int(os.environ.get("MR_RAO_OCR_DPI", "250"))
JOB_TTL_SECONDS = int(os.environ.get("MR_RAO_JOB_TTL", "3600"))
MAX_ATTACHMENT_BYTES = int(os.environ.get("MR_RAO_MAX_ATTACH_MB", "15")) * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".html",
    ".htm",
    ".csv",
    ".json",
    ".xml",
    ".txt",
    ".rtf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".gif",
    ".webp",
    ".eml",
}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".gif",
    ".webp",
}

DOCUMENT_EXTENSIONS = ALLOWED_EXTENSIONS - IMAGE_EXTENSIONS - {".eml"}
