"""Privacy / PII scrubbing — Scrubadub + Italian detectors + granular filters."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


# ---------------------------------------------------------------------------
# Patterns (Italy + international)
# ---------------------------------------------------------------------------

# Codice Fiscale (16 alphanumeric, simplified check)
_RE_CF = re.compile(
    r"\b([A-Z]{6}\d{2}[A-EHLMPRST]\d{2}[A-Z]\d{3}[A-Z])\b",
    re.IGNORECASE,
)

# Partita IVA (IT + 11 digits, or bare 11 digits in fiscal context)
_RE_PIVA = re.compile(
    r"\b(?:IT)?(\d{11})\b",
    re.IGNORECASE,
)

# IBAN (generic + IT)
_RE_IBAN = re.compile(
    r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b",
    re.IGNORECASE,
)

# Italian / international phones
_RE_PHONE = re.compile(
    r"(?<!\w)(?:\+39[\s\-\.]?)?(?:0\d{1,4}[\s\-\.]?\d{5,8}|3\d{2}[\s\-\.]?\d{6,7})(?!\w)"
)

# Email
_RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# Amounts (EUR style)
_RE_AMOUNT = re.compile(
    r"(?:€\s*)?\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\b\s*(?:€|EUR|euro)?",
    re.IGNORECASE,
)

# Common Italian first names (subset — high-frequency)
_IT_FIRST_NAMES = {
    "mario", "luigi", "giuseppe", "giovanni", "antonio", "francesco", "marco",
    "alessandro", "andrea", "luca", "paolo", "stefano", "roberto", "riccardo",
    "davide", "matteo", "simone", "fabio", "daniele", "claudio", "massimo",
    "alessio", "nicola", "salvatore", "vincenzo", "pietro", "angelo", "carlo",
    "maria", "anna", "giulia", "francesca", "sara", "laura", "chiara", "elena",
    "valentina", "alessandra", "paola", "silvia", "elisa", "martina", "federica",
    "giorgia", "sofia", "alice", "gaia", "beatrice", "arianna", "giada",
    "luca", "enzo", "nico", "leo", "rosa", "rosa", "caterina", "donatella",
}

_IT_SURNAMES = {
    "rossi", "russo", "ferrari", "esposito", "bianchi", "romano", "colombo",
    "ricci", "marino", "greco", "bruno", "gallo", "conti", "de luca", "mancini",
    "costa", "giordano", "rizzo", "lombardi", "moretti", "barbieri", "fontana",
    "santoro", "mariani", "rinaldi", "caruso", "ferrara", "galli", "martini",
    "leone", "longo", "gentile", "martinelli", "vitale", "lombardo", "serra",
    "coppola", "de santis", "d'angelo", "marchetti", "parisi", "villa",
    "conte", "ferrero", "sala", "de angelis", "faraoni", "pellegrini",
    "rao", "bianco", "neri", "verdi",
}

_RE_IT_NAME = re.compile(
    r"\b([A-ZÀÈÉÌÒÙ][a-zàèéìòù']+)\s+([A-ZÀÈÉÌÒÙ][a-zàèéìòù']+(?:\s+[A-ZÀÈÉÌÒÙ][a-zàèéìòù']+)?)\b"
)


@dataclass
class PrivacyOptions:
    emails: bool = True
    phones: bool = True
    names: bool = True
    fiscal: bool = True  # CF, P.IVA, IBAN
    amounts: bool = False
    use_scrubadub: bool = True


@dataclass
class RedactionReport:
    counts: dict[str, int] = field(default_factory=dict)
    total: int = 0

    def add(self, kind: str, n: int = 1) -> None:
        if n <= 0:
            return
        self.counts[kind] = self.counts.get(kind, 0) + n
        self.total += n

    def to_dict(self) -> dict:
        return {"counts": dict(self.counts), "total": self.total}


def _replace_all(text: str, pattern: re.Pattern, placeholder: str, report: RedactionReport, kind: str) -> str:
    def _sub(m: re.Match) -> str:
        report.add(kind)
        return placeholder

    return pattern.sub(_sub, text)


def _scrub_italian_names(text: str, report: RedactionReport) -> str:
    def _sub(m: re.Match) -> str:
        first, last = m.group(1), m.group(2)
        fl = first.lower()
        # last token of multi-word surname
        last_tokens = last.lower().split()
        if fl in _IT_FIRST_NAMES or any(t in _IT_SURNAMES for t in last_tokens):
            if fl in _IT_FIRST_NAMES or last_tokens[-1] in _IT_SURNAMES:
                report.add("names")
                return "{{NAME}}"
        return m.group(0)

    return _RE_IT_NAME.sub(_sub, text)


def apply_privacy_filter(
    text: str,
    options: PrivacyOptions | None = None,
) -> tuple[str, RedactionReport]:
    """Apply selected redactions. Returns (cleaned_text, report)."""
    if not text:
        return text, RedactionReport()

    opts = options or PrivacyOptions()
    report = RedactionReport()
    out = text

    if opts.emails:
        out = _replace_all(out, _RE_EMAIL, "{{EMAIL}}", report, "emails")

    if opts.phones:
        out = _replace_all(out, _RE_PHONE, "{{PHONE}}", report, "phones")

    if opts.fiscal:
        out = _replace_all(out, _RE_CF, "{{CODICE_FISCALE}}", report, "codice_fiscale")
        out = _replace_all(out, _RE_IBAN, "{{IBAN}}", report, "iban")
        # P.IVA: only replace if preceded by context keywords nearby or IT prefix
        def _piva_sub(m: re.Match) -> str:
            start = max(0, m.start() - 24)
            ctx = out[start : m.start()].lower()
            raw = m.group(0)
            if raw.upper().startswith("IT") or any(
                k in ctx for k in ("p.iva", "piva", "partita", "vat", "c.f.")
            ):
                report.add("partita_iva")
                return "{{PARTITA_IVA}}"
            return raw

        out = _RE_PIVA.sub(_piva_sub, out)

    if opts.amounts:
        out = _replace_all(out, _RE_AMOUNT, "{{AMOUNT}}", report, "amounts")

    if opts.names:
        out = _scrub_italian_names(out, report)

    if opts.use_scrubadub:
        try:
            import scrubadub

            before = out
            out = scrubadub.clean(out)
            # Approximate: count placeholder-like changes
            if out != before:
                # scrubadub uses {{EMAIL}}, {{PHONE}}, {{NAME}} etc.
                for kind, token in (
                    ("emails", "{{EMAIL}}"),
                    ("phones", "{{PHONE}}"),
                    ("names", "{{NAME}}"),
                ):
                    delta = out.count(token) - before.count(token)
                    if delta > 0:
                        report.add(kind, delta)
        except Exception:
            pass

    return out, report


def options_from_form(form) -> PrivacyOptions:
    """Build PrivacyOptions from Flask request.form (or dict-like)."""
    def flag(key: str, default: bool = True) -> bool:
        if key not in form:
            return default
        val = form.get(key)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("1", "true", "yes", "on")

    # Master switch
    master = flag("privacy_filter", False)
    if not master:
        return PrivacyOptions(
            emails=False,
            phones=False,
            names=False,
            fiscal=False,
            amounts=False,
            use_scrubadub=False,
        )

    return PrivacyOptions(
        emails=flag("privacy_emails", True),
        phones=flag("privacy_phones", True),
        names=flag("privacy_names", True),
        fiscal=flag("privacy_fiscal", True),
        amounts=flag("privacy_amounts", False),
        use_scrubadub=flag("privacy_scrubadub", True),
    )


def options_from_dict(data: dict | None) -> PrivacyOptions:
    data = data or {}
    if not data.get("privacy_filter", False):
        return PrivacyOptions(
            emails=False,
            phones=False,
            names=False,
            fiscal=False,
            amounts=False,
            use_scrubadub=False,
        )
    return PrivacyOptions(
        emails=bool(data.get("privacy_emails", True)),
        phones=bool(data.get("privacy_phones", True)),
        names=bool(data.get("privacy_names", True)),
        fiscal=bool(data.get("privacy_fiscal", True)),
        amounts=bool(data.get("privacy_amounts", False)),
        use_scrubadub=bool(data.get("privacy_scrubadub", True)),
    )
