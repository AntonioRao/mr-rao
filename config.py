"""Mr. Rao — central configuration (dev + frozen portable)."""
from __future__ import annotations

import os
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
APP_TAGLINE = "Dal documento al Markdown. Offline. Firmato Rao."
APP_VERSION = "1.3.1"

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
SECRET_KEY = os.environ.get("MR_RAO_SECRET", "mr-rao-local-dev-only")
USE_TRAY = os.environ.get("MR_RAO_TRAY", "1").strip() not in ("0", "false", "no")
OPEN_BROWSER = os.environ.get("MR_RAO_OPEN_BROWSER", "1").strip() not in ("0", "false", "no")

# Security — a local server is reachable by any page the user has open in the
# browser, so the Host header is pinned (anti DNS-rebinding) and cross-site
# Origins are refused (anti CSRF). Binding 0.0.0.0 is a deliberate choice to
# expose the app, so the host allow-list opens up; the Origin check stays.
_default_hosts = "*" if HOST == "0.0.0.0" else "127.0.0.1,localhost,[::1],::1"
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
