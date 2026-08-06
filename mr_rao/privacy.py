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

# IBAN (generic + IT). Case-sensitive on purpose: lowercase "words" like
# "ab12cdefghijklm" are not IBANs. Every candidate is checked with mod-97.
_RE_IBAN = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b")

# Italian / international phones. The regex only proposes *candidates*:
# _phone_is_plausible() decides, so that bare digit runs such as a protocol
# number ("protocollo 0123456789") are not mistaken for landlines.
_RE_PHONE = re.compile(
    r"(?<!\w)(?P<prefix>\+39|0039)?[\s\-\.]?"
    r"(?P<body>0\d{1,4}[\s\-\.]?\d{5,8}|3\d{2}[\s\-\.]?\d{6,7})"
    r"(?!\w)"
)

# Context words that turn an ambiguous digit run into a phone number.
_RE_PHONE_CTX = re.compile(
    r"\b(tel|telefono|telefonico|cell|cellulare|mobile|fax|phone|recapito)\b"
    r"[\.:]?\s*$",
    re.IGNORECASE,
)

# Email
_RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# Amounts (EUR style). Candidates only — _amount_is_plausible() requires a
# currency marker, a thousands group or a fiscal context word, so that version
# numbers ("Versione 1.10") survive. The trailing currency is optional *with*
# its own whitespace, so a bare number never swallows the following space.
_RE_AMOUNT = re.compile(
    r"(?P<cur_pre>€\s*)?"
    r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\b"
    r"(?P<cur_post>\s*(?:€|EUR\b|euro\b))?",
    re.IGNORECASE,
)

# Context words that make a bare decimal an amount.
_RE_AMOUNT_CTX = re.compile(
    r"\b(importo|importi|totale|subtotale|saldo|prezzo|costo|iva|imponibile|"
    r"netto|lordo|acconto|fattura|pagamento|canone)\b\W*$",
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


def _context_before(text: str, start: int, window: int = 24) -> str:
    """The few characters preceding a match, used to disambiguate candidates."""
    return text[max(0, start - window) : start]


def iban_checksum_ok(candidate: str) -> bool:
    """ISO 13616 mod-97 check. Rejects random uppercase tokens."""
    s = candidate.replace(" ", "").upper()
    if len(s) < 15 or len(s) > 34:
        return False
    rearranged = s[4:] + s[:4]
    digits = ""
    for ch in rearranged:
        if ch.isdigit():
            digits += ch
        elif "A" <= ch <= "Z":
            digits += str(ord(ch) - 55)
        else:
            return False
    return int(digits) % 97 == 1


def _phone_is_plausible(m: re.Match) -> bool:
    """A digit run is a phone only with a +39 prefix, a separator,
    a mobile 3xx prefix, or an explicit context word."""
    if m.group("prefix"):
        return True
    body = m.group("body")
    if body.startswith("3"):  # Italian mobile
        return True
    if any(sep in body for sep in (" ", "-", ".")):
        return True
    return bool(_RE_PHONE_CTX.search(_context_before(m.string, m.start())))


def _amount_is_plausible(m: re.Match) -> bool:
    """A decimal is an amount only with a currency marker, a thousands
    group, or a fiscal context word — not every '1.10' in the text."""
    if m.group("cur_pre") or m.group("cur_post"):
        return True
    num = m.group("num")
    if num.count(".") + num.count(",") > 1:  # e.g. 1.500,00
        return True
    return bool(_RE_AMOUNT_CTX.search(_context_before(m.string, m.start())))


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

        def _phone_sub(m: re.Match) -> str:
            if not _phone_is_plausible(m):
                return m.group(0)
            report.add("phones")
            return "{{PHONE}}"

        out = _RE_PHONE.sub(_phone_sub, out)

    if opts.fiscal:
        out = _replace_all(out, _RE_CF, "{{CODICE_FISCALE}}", report, "codice_fiscale")

        def _iban_sub(m: re.Match) -> str:
            if not iban_checksum_ok(m.group(1)):
                return m.group(0)
            report.add("iban")
            return "{{IBAN}}"

        out = _RE_IBAN.sub(_iban_sub, out)

        # P.IVA: only replace if preceded by context keywords nearby or IT prefix
        def _piva_sub(m: re.Match) -> str:
            ctx = _context_before(m.string, m.start()).lower()
            raw = m.group(0)
            if raw.upper().startswith("IT") or any(
                k in ctx for k in ("p.iva", "piva", "partita", "vat", "c.f.")
            ):
                report.add("partita_iva")
                return "{{PARTITA_IVA}}"
            return raw

        out = _RE_PIVA.sub(_piva_sub, out)

    if opts.amounts:

        def _amount_sub(m: re.Match) -> str:
            if not _amount_is_plausible(m):
                return m.group(0)
            report.add("amounts")
            return "{{AMOUNT}}"

        out = _RE_AMOUNT.sub(_amount_sub, out)

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

    # Master switch. Fail-safe: an API client that omits the field gets the
    # redactions, it never gets plaintext PII by accident (same default as the CLI).
    master = flag("privacy_filter", True)
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
    if not data.get("privacy_filter", True):
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
