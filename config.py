"""Mr. Rao — central configuration."""
from __future__ import annotations

import os
from pathlib import Path

# Brand
APP_NAME = "Mr. Rao"
APP_SLUG = "mr-rao"
APP_TAGLINE = "Dal documento al Markdown. Offline. Firmato Rao."
APP_VERSION = "1.0.0"

# Paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
STATIC_FOLDER = BASE_DIR / "static"
TEMPLATES_FOLDER = BASE_DIR / "templates"

# Server
HOST = os.environ.get("MR_RAO_HOST", "127.0.0.1")
PORT = int(os.environ.get("MR_RAO_PORT", "5000"))
DEBUG = os.environ.get("MR_RAO_DEBUG", "0").strip() in ("1", "true", "True", "yes")
SECRET_KEY = os.environ.get("MR_RAO_SECRET", "mr-rao-local-dev-only")

# Limits
MAX_CONTENT_LENGTH = int(os.environ.get("MR_RAO_MAX_UPLOAD_MB", "50")) * 1024 * 1024
MAX_OCR_PAGES = int(os.environ.get("MR_RAO_MAX_OCR_PAGES", "50"))
OCR_DPI = int(os.environ.get("MR_RAO_OCR_DPI", "250"))
JOB_TTL_SECONDS = int(os.environ.get("MR_RAO_JOB_TTL", "3600"))

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
