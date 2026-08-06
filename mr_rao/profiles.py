"""Conversion presets for common workflows.

Ogni profilo elenca solo cio' che cambia rispetto ai valori predefiniti del
motore (``privacy.FIELD_DEFAULTS``). Cosi' un riconoscitore nuovo entra in
tutti i profili il giorno stesso in cui nasce, invece di restare spento in
cinque preset su sei perche' qualcuno ha dimenticato una riga.
"""
from __future__ import annotations

from mr_rao.converter import ConvertOptions
from mr_rao.privacy import FIELD_DEFAULTS, PrivacyOptions

PROFILES: dict[str, dict] = {
    "default": {
        "label": "Predefinito",
        "description": "Bilanciato: privacy on, tabelle, frontmatter",
        "engine": "auto",
        "language": "it",
        "privacy_filter": True,
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
        "privacy_amounts": True,
        "privacy_dates": True,
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
        "privacy_amounts": False,
        # Una fattura e' piena di ragioni sociali: l'euristica del cognome
        # farebbe piu' danni che bene, e i dati che contano davvero
        # (IBAN, P.IVA, codice fiscale) hanno un riconoscitore proprio.
        "privacy_name_guess": False,
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


def privacy_flags(profile: dict) -> dict[str, bool]:
    """I flag privacy effettivi del profilo, difetti del motore compresi."""
    if not profile.get("privacy_filter"):
        return {k: False for k in FIELD_DEFAULTS}
    return {
        k: bool(profile.get("privacy_" + k, d)) for k, d in FIELD_DEFAULTS.items()
    }


def options_from_profile(profile_id: str) -> ConvertOptions | None:
    p = PROFILES.get(profile_id)
    if not p:
        return None
    return ConvertOptions(
        engine=p.get("engine", "auto"),
        language=p.get("language", "it"),
        privacy=PrivacyOptions(**privacy_flags(p)),
        include_tables=bool(p.get("include_tables", True)),
        include_frontmatter=bool(p.get("include_frontmatter", True)),
        clean_output=bool(p.get("clean_output", False)),
        force_ocr_pdf=bool(p.get("force_ocr_pdf", False)),
        include_raw=bool(p.get("include_raw", True)),
    )
