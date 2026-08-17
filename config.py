# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
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


def _exe_dir() -> Path:
    """La cartella dell'eseguibile.

    Ci stanno gli asset accanto al programma, e nel **portable** ci stanno
    anche i dati: e' quello che rende il portable portable — la chiavetta si
    porta via tutto insieme.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _in_pacchetto() -> bool:
    """Il programma sta girando dentro un pacchetto MSIX?

    **Perche' questa domanda esiste, e cosa e' costata.** Un pacchetto MSIX
    si installa in `C:\\Program Files\\WindowsApps\\...`, che e' protetta da
    ACL e **non e' scrivibile nemmeno da un processo elevato**. Fino alla
    1.20.0 la cartella scrivibile era sempre quella dell'eseguibile: nel
    portable e' giusto, dentro un pacchetto e' fatale. `create_app()` crea
    la cartella degli upload **all'importazione**, quindi il `mkdir`
    sollevava `PermissionError` prima che il programma stampasse una riga.
    Dalla certificazione dello Store e' tornato indietro come *«The product
    crashes at launch»*, che e' esattamente cio' che era.

    Non si guarda il percorso, si chiede a Windows: `GetCurrentPackageFullName`
    risponde `APPMODEL_ERROR_NO_PACKAGE` (15700) quando il processo non e'
    impacchettato. Cercare la stringa «WindowsApps» dentro il percorso
    funzionerebbe quasi sempre, e «quasi» qui vuol dire che una cartella
    chiamata cosi' per caso cambierebbe il comportamento del programma.

    Il ripiego sul percorso resta, ma solo se l'API non c'e': su una
    Windows troppo vecchia per i pacchetti la risposta giusta e' comunque
    «no».
    """
    if sys.platform != "win32":
        return False
    # I due controlli sono in **or**, e non e' pigrizia: i due errori
    # possibili non costano uguale. Dire «impacchettato» quando non lo e'
    # manda i dati nel profilo dell'utente invece che accanto
    # all'eseguibile — un fastidio. Dire «non impacchettato» quando lo e'
    # riporta il crash all'avvio che ha fatto fallire la certificazione.
    # Fra un fastidio e un programma che non parte non c'e' partita.
    if "\\windowsapps\\" in str(sys.executable).lower():
        return True
    try:
        import ctypes
        from ctypes import wintypes

        lunghezza = wintypes.UINT(0)
        # Primo giro con un buffer nullo: serve solo a distinguere «nessun
        # pacchetto» da «pacchetto, e il nome e' lungo cosi'».
        esito = ctypes.windll.kernel32.GetCurrentPackageFullName(
            ctypes.byref(lunghezza), None
        )
        # 15700 = APPMODEL_ERROR_NO_PACKAGE
        return esito != 15700
    except (AttributeError, OSError):
        # L'API non c'e': Windows precedente ai pacchetti. La risposta
        # giusta li' e' comunque «no».
        return False


def _writable_dir() -> Path:
    """Dove il programma puo' scrivere. **Non sempre dove sta.**

    Dentro un pacchetto la cartella d'installazione e' di sola lettura, e i
    dati vanno nel profilo dell'utente. Fuori, resta accanto
    all'eseguibile: e' il comportamento del portable, ed e' voluto.
    """
    if _in_pacchetto():
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "Mr. Rao"
        # Nemmeno LOCALAPPDATA: non e' una situazione in cui valga la pena
        # morire, e la cartella temporanea e' scrivibile per definizione.
        import tempfile

        return Path(tempfile.gettempdir()) / "Mr. Rao"
    return _exe_dir()


# Brand
APP_NAME = "Mr. Rao"
APP_SLUG = "mr-rao"
APP_TAGLINE = (
    "Converti documenti, immagini e thread email in Markdown puro. "
    "Con i dati personali già rimossi. Offline, sul tuo computer."
)
APP_VERSION = "1.27.1"

# Paths
BASE_DIR = _base_dir()
EXE_DIR = _exe_dir()
WRITABLE_DIR = _writable_dir()
UPLOAD_FOLDER = WRITABLE_DIR / "uploads"
STATIC_FOLDER = BASE_DIR / "static"
TEMPLATES_FOLDER = BASE_DIR / "templates"
# Il ripiego degli asset guarda `EXE_DIR`, **non** `WRITABLE_DIR`.
#
# Erano la stessa cosa finche' il programma scriveva accanto a se stesso.
# Da quando dentro un pacchetto i dati vanno nel profilo dell'utente non lo
# sono piu': cercare `static/` in `%LOCALAPPDATA%` vorrebbe dire cercarla
# dove non c'e' mai stata, e l'interfaccia si aprirebbe senza foglio di
# stile. Gli asset stanno dove sta il programma; i dati dove si puo'
# scrivere. Sono due domande diverse e adesso hanno due risposte.
if not STATIC_FOLDER.exists() and (EXE_DIR / "static").exists():
    STATIC_FOLDER = EXE_DIR / "static"
if not TEMPLATES_FOLDER.exists() and (EXE_DIR / "templates").exists():
    TEMPLATES_FOLDER = EXE_DIR / "templates"

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

# Una finestra dell'applicazione invece di una scheda del browser. Stessa
# interfaccia e stesso server locale: cambia il contorno, e cambia cosa si
# vede nella barra delle applicazioni.
#
# Acceso di serie, ma **non e' una promessa**: se il motore di rendering di
# sistema non c'e', `mr_rao.finestra.disponibile()` dice di no e si apre il
# browser come sempre. Metterlo a `0` sceglie il browser anche dove la finestra
# si potrebbe aprire.
USA_FINESTRA = os.environ.get("MR_RAO_FINESTRA", "1").strip() not in ("0", "false", "no")

# La scorciatoia che redige gli appunti sul posto: `0` la spegne, qualunque
# altra cosa e' la combinazione. **Una** variabile per due cose, perche' sono
# la stessa domanda -- «quale combinazione, o nessuna» -- e tenerle separate
# permetterebbe lo stato incoerente «accesa, combinazione vuota», che si
# manifesterebbe come una scorciatoia che non risponde senza dire perche'.
# Guida, e disinnesco della somiglianza con un keylogger:
# docs/SCORCIATOIA-APPUNTI.md
_SCORCIATOIA = os.environ.get("MR_RAO_SCORCIATOIA", "ctrl+alt+r").strip()
# ctypes.WinDLL: solo Windows. Fuori da win32 la scorciatoia non esiste
# (un True qui fa cadere tray.py su AttributeError all'avvio).
SCORCIATOIA_ATTIVA = (
    sys.platform == "win32"
    and _SCORCIATOIA.lower() not in ("0", "false", "no", "")
)
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
    # `.md` e `.markdown`: mancavano, ed era una dimenticanza, non una
    # scelta. Il resto del programma il Markdown lo conosceva gia' — sta fra
    # le estensioni di prosa e fra quelle del ripiego a testo semplice — ma
    # da qui non passava, quindi **Mr. Rao non sapeva rileggere la propria
    # uscita**: il formato che produce era l'unico che non accettava.
    # Trovato passando i documenti veri di una scrivania: dodici file su
    # trentadue rifiutati con un `400`, tutti `.md`.
    ".md",
    ".markdown",
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
