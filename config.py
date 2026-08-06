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
APP_VERSION = "1.1.0"

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

# Limits
MAX_CONTENT_LENGTH = int(os.environ.get("MR_RAO_MAX_UPLOAD_MB", "50")) * 1024 * 1024
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
