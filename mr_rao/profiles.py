"""Conversion presets for common workflows."""
from __future__ import annotations

from mr_rao.converter import ConvertOptions
from mr_rao.privacy import PrivacyOptions

PROFILES: dict[str, dict] = {
    "default": {
        "label": "Predefinito",
        "description": "Bilanciato: privacy on, tabelle, frontmatter",
        "engine": "auto",
        "language": "it",
        "privacy_filter": True,
        "privacy_emails": True,
        "privacy_phones": True,
        "privacy_names": True,
        "privacy_fiscal": True,
        "privacy_amounts": False,
        "include_tables": True,
        "include_frontmatter": True,
        "clean_output": False,
        "force_ocr_pdf": False,
        "include_raw": True,
    },
    "email_legali": {
        "label": "Email legali",
        "description": "EML/thread: privacy massima, output pulito per AI",
        "engine": "auto",
        "language": "it",
        "privacy_filter": True,
        "privacy_emails": True,
        "privacy_phones": True,
        "privacy_names": True,
        "privacy_fiscal": True,
        "privacy_amounts": True,
        "include_tables": False,
        "include_frontmatter": True,
        "clean_output": True,
        "force_ocr_pdf": False,
        "include_raw": True,
    },
    "fatture": {
        "label": "Fatture / contabili",
        "description": "PDF con tabelle; CF/P.IVA/IBAN redatti, importi visibili",
        "engine": "auto",
        "language": "it",
        "privacy_filter": True,
        "privacy_emails": True,
        "privacy_phones": True,
        "privacy_names": True,
        "privacy_fiscal": True,
        "privacy_amounts": False,
        "include_tables": True,
        "include_frontmatter": True,
        "clean_output": False,
        "force_ocr_pdf": False,
        "include_raw": True,
    },
    "solo_ocr": {
        "label": "Solo OCR",
        "description": "Forza RapidOCR (scansioni e immagini)",
        "engine": "rapidocr",
        "language": "it",
        "privacy_filter": False,
        "privacy_emails": False,
        "privacy_phones": False,
        "privacy_names": False,
        "privacy_fiscal": False,
        "privacy_amounts": False,
        "include_tables": True,
        "include_frontmatter": False,
        "clean_output": True,
        "force_ocr_pdf": True,
        "include_raw": False,
    },
    "llm_ready": {
        "label": "Pronto per LLM",
        "description": "Privacy on, senza frontmatter, copia pulita",
        "engine": "auto",
        "language": "it",
        "privacy_filter": True,
        "privacy_emails": True,
        "privacy_phones": True,
        "privacy_names": True,
        "privacy_fiscal": True,
        "privacy_amounts": False,
        "include_tables": True,
        "include_frontmatter": False,
        "clean_output": True,
        "force_ocr_pdf": False,
        "include_raw": True,
    },
    "no_privacy": {
        "label": "Nessuna redazione",
        "description": "Testo integrale (uso strettamente locale)",
        "engine": "auto",
        "language": "it",
        "privacy_filter": False,
        "privacy_emails": False,
        "privacy_phones": False,
        "privacy_names": False,
        "privacy_fiscal": False,
        "privacy_amounts": False,
        "include_tables": True,
        "include_frontmatter": True,
        "clean_output": False,
        "force_ocr_pdf": False,
        "include_raw": False,
    },
}


def list_profiles() -> list[dict]:
    return [
        {"id": pid, "label": p["label"], "description": p["description"]}
        for pid, p in PROFILES.items()
    ]


def get_profile(profile_id: str) -> dict | None:
    return PROFILES.get(profile_id)


def options_from_profile(profile_id: str) -> ConvertOptions | None:
    p = PROFILES.get(profile_id)
    if not p:
        return None
    privacy_on = bool(p.get("privacy_filter"))
    return ConvertOptions(
        engine=p.get("engine", "auto"),
        language=p.get("language", "it"),
        privacy=PrivacyOptions(
            emails=bool(p.get("privacy_emails")) if privacy_on else False,
            phones=bool(p.get("privacy_phones")) if privacy_on else False,
            names=bool(p.get("privacy_names")) if privacy_on else False,
            fiscal=bool(p.get("privacy_fiscal")) if privacy_on else False,
            amounts=bool(p.get("privacy_amounts")) if privacy_on else False,
            use_scrubadub=privacy_on,
        ),
        include_tables=bool(p.get("include_tables", True)),
        include_frontmatter=bool(p.get("include_frontmatter", True)),
        clean_output=bool(p.get("clean_output", False)),
        force_ocr_pdf=bool(p.get("force_ocr_pdf", False)),
        include_raw=bool(p.get("include_raw", True)),
    )
