"""Riconoscimento e sostituzione dei dati personali (formati italiani).

Ogni riconoscitore e' un'espressione regolare accompagnata da un validatore:
il pattern propone, il validatore decide. E' quello che tiene bassi i falsi
positivi senza rinunciare alla copertura — un IBAN si accetta solo se il
mod-97 torna, una carta solo se passa Luhn, un numero e' un telefono solo
con prefisso, separatore o parola di contesto.

Per i nomi di persona gli elenchi non bastano mai, quindi valgono anche le
regole di contesto: un titolo professionale davanti, un indirizzo di posta
accanto, un nome proprio riconosciuto che tira dentro la parola successiva.
L'ultima regola — due parole maiuscole che non sono parole italiane — e'
la piu' aggressiva, e infatti si puo' spegnere da sola (``name_guess``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from mr_rao.it_names import COMMON_CAPITALIZED, FIRST_NAMES, SURNAMES


# ---------------------------------------------------------------------------
# Codici e conti
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

# Carta di pagamento: 13-19 cifre che iniziano con un IIN plausibile e
# passano il controllo di Luhn. Senza Luhn qualunque numero lungo finirebbe
# redatto; con Luhn e' il numero stesso a dire se e' una carta.
_RE_CARD = re.compile(r"(?<![\w.])([3-6]\d{3}(?:[ \-]?\d{2,6}){2,4})(?![\w])")


# ---------------------------------------------------------------------------
# Contatti
# ---------------------------------------------------------------------------

# URL. Solo con schema esplicito o con "www.": e' il confine che si
# riconosce a occhio, e non trasforma ogni "nome.it" del testo in un link.
_RE_URL = re.compile(
    r"\b(?:https?|ftp|ftps)://[^\s<>\"'`\]\)]+"
    r"|(?<![\w.])www\.[^\s<>\"'`\]\)]+",
    re.IGNORECASE,
)

# Un numero di telefono e' una sequenza di 6-15 cifre con separatori interni
# facoltativi, eventualmente preceduta da un prefisso internazionale. Il
# pattern propone soltanto: _phone_is_plausible() decide, perche' un numero
# di protocollo e una data hanno esattamente la stessa forma.
_RE_PHONE = re.compile(
    r"(?<![\w.+])"
    r"(?P<prefix>(?:\+|00)(?P<cc>\d{1,3})[\s.\-]?)?"
    r"(?P<body>\d(?:[\s.\-]?\d){5,14})"
    r"(?![\w])"
)

# Parole che trasformano una sequenza ambigua in un recapito.
_RE_PHONE_CTX = re.compile(
    r"\b(tel|telefono|telefonico|telefonica|cell|cel|cellulare|mobile|mob|"
    r"fax|phone|recapito|centralino|whatsapp)\b"
    r"\.?\s*(?:n\.?|nr\.?|numero)?\s*[:\-]?\s*$",
    re.IGNORECASE,
)

# Una data scritta con i separatori ha la stessa forma di un numero di
# telefono: "01.02.2024" sono otto cifre che iniziano per zero.
_RE_DATELIKE = re.compile(
    r"^\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4}$|^\d{4}[.\-]\d{1,2}[.\-]\d{1,2}$"
)

# Email
_RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)


# ---------------------------------------------------------------------------
# Importi
# ---------------------------------------------------------------------------

# Candidates only — _amount_is_plausible() requires a currency marker, a
# thousands group or a fiscal context word, so that version numbers survive.
_RE_AMOUNT = re.compile(
    r"(?P<cur_pre>€\s*)?"
    r"\b(?P<num>\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\b"
    r"(?P<cur_post>\s*(?:€|EUR\b|euro\b))?",
    re.IGNORECASE,
)

_RE_AMOUNT_CTX = re.compile(
    r"\b(importo|importi|totale|subtotale|saldo|prezzo|costo|iva|imponibile|"
    r"netto|lordo|acconto|fattura|pagamento|canone)\b\W*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Segreti tecnici
# ---------------------------------------------------------------------------

# Chiavi, token e password. Sono dati personali di un altro tipo — quelli
# che non ci si accorge di incollare insieme al resto del documento.
_RE_SECRETS = [
    ("private_key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    )),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    ("aws_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}\b")),
    ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{20,}")),
]

# Il caso generico: "password: ...", "api_key = ...". Sostituisce il valore
# e lascia l'etichetta, cosi' si capisce cosa e' stato tolto.
_RE_SECRET_KV = re.compile(
    r"(?i)\b(password|passwd|pwd|parola d'ordine|token|api[_\- ]?key|"
    r"secret|client[_\- ]?secret|access[_\- ]?key|chiave|credenziali)\b"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<val>[^\s,;\"']{6,})"
)


# ---------------------------------------------------------------------------
# Date di nascita
# ---------------------------------------------------------------------------

_MESI = (
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|"
    r"ottobre|novembre|dicembre"
)

_RE_DATE = re.compile(
    rf"\b\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{2,4}}\b|\b\d{{1,2}}\s+(?i:{_MESI})\s+\d{{4}}\b"
)

_RE_BIRTH_CTX = re.compile(
    r"(?i)\b(nat[oaie]|nascit[ao]|born|d\.?o\.?b\.?|compleanno)\b[^\n]{0,20}$"
)


# ---------------------------------------------------------------------------
# Indirizzi
# ---------------------------------------------------------------------------

# "Via", "Piazza", "Corso"... sono anche parole comuni ("via email", "nel
# corso della riunione"): l'indirizzo si riconosce perche' subito dopo c'e'
# almeno una parola con l'iniziale maiuscola.
_ADDRESS_KW = (
    r"via|viale|v\.le|vicolo|vico|piazza|p\.zza|p\.za|piazzale|largo|corso|"
    r"c\.so|strada|stradale|contrada|c\.da|localita|località|loc|frazione|"
    r"fraz|borgo|lungomare|lungotevere|lungarno|salita|discesa|traversa|"
    r"circonvallazione|rotonda|galleria|passeggiata|riviera|calle|molo|"
    r"banchina|villaggio|residenza|rione|viottolo|sentiero"
)

# Parole che seguono la parola-chiave senza fare un indirizzo: "via PEC",
# "Via Aerea". Sono maiuscole, quindi il vincolo sull'iniziale non basta.
_ADDRESS_STOPWORDS = frozenset(
    {
        "pec", "email", "mail", "e-mail", "fax", "telefono", "posta",
        "raccomandata", "internet", "web", "aerea", "terra", "mare",
        "telematica", "ordinaria", "breve", "crucis", "libera", "cavo",
        "satellite", "corriere", "telefax", "sms", "lattea",
    }
)

# Un pezzo di nome proprio: iniziale maiuscola e almeno una minuscola.
# Il vincolo sulla minuscola esclude in un colpo solo gli acronimi (PEC,
# SPA), i numeri romani (II) e i segnaposto gia' inseriti ({{EMAIL}}).
_TOK = r"[A-ZÀ-ÖØ-Þ][\w'’\-]*[a-zà-öø-ÿ][\w'’\-]*"

# Articoli e preposizioni che stanno dentro un nome di strada.
_CONN = (
    r"(?:d[ei]|del|dello|della|dei|degli|delle|dal|dalla|da|la|lo|le|il|"
    r"san|santa|sant'|santo|santi|ss\.)"
)

_RE_ADDRESS = re.compile(
    rf"(?<!\w)(?i:{_ADDRESS_KW})\.?\s+"
    rf"(?P<body>(?:{_CONN}\s+)*"
    rf"(?:\w+['’])?{_TOK}"
    rf"(?:\s+(?:{_CONN}\s+|e\s+)?(?:\w+['’])?{_TOK}){{0,3}})"
    rf"(?P<roman>\s+[IVXLC]{{1,5}}(?![\w]))?"
    rf"(?P<civ>\s*,?\s*(?:n\.?|nr\.?|snc|km)?\s*\d{{1,4}}"
    rf"(?:\s*[/\-]\s*[A-Za-z0-9]{{1,3}})?)?"
    rf"(?P<cap>\s*[,\-–]?\s*\d{{5}}\s+{_TOK}(?:\s+{_TOK})?)?"
)


# ---------------------------------------------------------------------------
# Nomi di persona
# ---------------------------------------------------------------------------

_TITLES = (
    r"sig|sig\.ra|sig\.na|signor|signora|signorina|dott|dott\.ssa|dr|dr\.ssa|"
    r"dottor|dottore|dottoressa|ing|ingegner|ingegnere|avv|avvocato|"
    r"avvocatessa|geom|geometra|arch|architetto|prof|prof\.ssa|professor|"
    r"professore|professoressa|rag|ragionier|ragioniere|on|onorevole|"
    r"egr|gent|mr|mrs|ms"
)

# Fra un nome e il suo cognome ci puo' essere uno spazio, non un a capo:
# usare \s farebbe attraversare le righe e incollerebbe la firma alla riga
# successiva, con il risultato che una parola comune trovata li' fa cadere
# tutto il riconoscimento.
_SP = r"[ \t]+"

_RE_TITLE_NAME = re.compile(
    rf"(?<!\w)(?i:{_TITLES})\.?{_SP}(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Un nome accanto a un indirizzo di posta: "Mario Rossi <mario@x.it>",
# "mario@x.it (Mario Rossi)". Gira dopo la sostituzione delle email, quindi
# quello che cerca e' il segnaposto.
_RE_NAME_BEFORE_EMAIL = re.compile(
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})(?P<sep>\s*[<\(\[]?\s*)\{{\{{EMAIL\}}\}}"
)
_RE_NAME_AFTER_EMAIL = re.compile(
    rf"\{{\{{EMAIL\}}\}}(?P<sep>\s*[<\(\[]\s*)(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

_RE_NAME_PAIR = re.compile(rf"(?<!\w){_TOK}(?:{_SP}{_TOK}){{1,2}}(?!\w)")

_RE_LONE_TOKEN = re.compile(rf"(?<!\w){_TOK}(?!\w)")

# Nomi propri che sono anche parole comuni: da soli non bastano.
_AMBIGUOUS_ALONE = frozenset(
    {
        "rosa", "celeste", "vera", "grazia", "pace", "speranza", "gioia",
        "perla", "aurora", "neve", "ambra", "letizia", "allegra", "prima",
        "primo", "secondo", "santa", "santo", "natale", "felice", "vittoria",
        "fortunato", "benedetto", "giusto", "amato", "diana", "iris", "viola",
        "stella", "luna", "alba", "italo", "italia", "domenica", "sabato",
        "marzo", "agosto", "maggio", "conte", "modesto", "candido", "bruno",
        "franco", "sereno", "fiore", "fede", "vero", "divo", "duce",
    }
)


@dataclass
class PrivacyOptions:
    emails: bool = True
    phones: bool = True
    names: bool = True
    fiscal: bool = True  # CF, P.IVA, IBAN, carte di pagamento
    amounts: bool = False
    urls: bool = True
    addresses: bool = True
    secrets: bool = True
    dates: bool = False  # solo date accanto a un contesto di nascita
    # Euristica del cognome: due parole maiuscole che non sono parole
    # italiane sono quasi sempre nome e cognome. Copre i cognomi che nessun
    # elenco contiene, ma e' anche la regola che puo' sbagliare: si spegne
    # da sola, senza rinunciare al resto del riconoscimento dei nomi.
    name_guess: bool = True


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


def luhn_ok(candidate: str) -> bool:
    """Controllo di Luhn (ISO/IEC 7812). Un numero lungo qualsiasi lo
    supera una volta su dieci: unito al vincolo sul primo digit e sulla
    lunghezza, basta a distinguere una carta da un codice interno."""
    digits = [int(c) for c in candidate if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _phone_is_plausible(m: re.Match) -> bool:
    """Decide se una sequenza di cifre e' un numero di telefono.

    Accetta con prefisso internazionale, con prefisso di cellulare italiano
    (3xx) o con una parola di contesto davanti; per i fissi pretende anche
    un separatore, cosi' un numero di protocollo di dieci cifre resta al
    suo posto.
    """
    body = m.group("body")
    if _RE_DATELIKE.match(body.strip()):
        return False

    digits = re.sub(r"\D", "", body)
    n = len(digits)
    has_sep = any(sep in body for sep in (" ", "-", "."))
    ctx = bool(_RE_PHONE_CTX.search(_context_before(m.string, m.start())))

    if m.group("prefix"):
        return 6 <= n <= (11 if m.group("cc") == "39" else 14)

    if ctx:
        return 6 <= n <= 13

    if digits.startswith("3") and 9 <= n <= 10:  # cellulare italiano
        return True

    if digits.startswith("0") and 8 <= n <= 11 and has_sep:  # fisso italiano
        return True

    return False


def _amount_is_plausible(m: re.Match) -> bool:
    """A decimal is an amount only with a currency marker, a thousands
    group, or a fiscal context word — not every '1.10' in the text."""
    if m.group("cur_pre") or m.group("cur_post"):
        return True
    num = m.group("num")
    if num.count(".") + num.count(",") > 1:  # e.g. 1.500,00
        return True
    return bool(_RE_AMOUNT_CTX.search(_context_before(m.string, m.start())))


def _is_common_word(token: str) -> bool:
    return token.lower().strip("'’-") in COMMON_CAPITALIZED


# Terminazioni tipiche di sostantivi e aggettivi italiani. Nessun elenco di
# parole puo' essere completo, ma la morfologia non ha bisogno di elenchi:
# "Industriale" e "Tecnico" finiscono come finiscono le parole, non come
# finiscono i cognomi. Vale solo per l'euristica: un cognome riconosciuto
# resta un cognome anche se termina in -ale (Vitale, Natale).
_WORDLIKE_SUFFIXES = (
    "zione", "zioni", "sione", "sioni", "mento", "menti", "aggio", "aggi",
    "anza", "enza", "ismo", "ista", "isti", "iste", "tore", "trice", "trici",
    "ale", "ali", "are", "ile", "ili", "ico", "ica", "ici", "iche",
    "oso", "osa", "osi", "ose", "ivo", "iva", "ivi", "ive", "bile", "bili",
    "ezza", "ezze", "orio", "oria", "ario", "aria", "esimo", "evole",
    "ura", "ure", "udine", "eria", "ficio", "logia", "grafia", "metro",
)


def _looks_like_word(token: str) -> bool:
    t = token.lower().strip("'’-")
    if len(t) < 5:
        return False
    return t.endswith(_WORDLIKE_SUFFIXES)


def _scrub_urls(text: str, report: RedactionReport) -> str:
    def _sub(m: re.Match) -> str:
        raw = m.group(0)
        trail = ""
        while raw and raw[-1] in ".,;:!?)]}'\"":
            trail = raw[-1] + trail
            raw = raw[:-1]
        if not raw:
            return m.group(0)
        report.add("urls")
        return "{{URL}}" + trail

    return _RE_URL.sub(_sub, text)


def _scrub_secrets(text: str, report: RedactionReport) -> str:
    for kind, pattern in _RE_SECRETS:
        text = _replace_all(text, pattern, "{{SECRET}}", report, "secrets")

    def _kv(m: re.Match) -> str:
        report.add("secrets")
        return m.group(1) + m.group("sep") + "{{SECRET}}"

    return _RE_SECRET_KV.sub(_kv, text)


def _scrub_birth_dates(text: str, report: RedactionReport) -> str:
    def _sub(m: re.Match) -> str:
        if not _RE_BIRTH_CTX.search(_context_before(m.string, m.start(), 40)):
            return m.group(0)
        report.add("dates")
        return "{{DATE}}"

    return _RE_DATE.sub(_sub, text)


def _scrub_addresses(text: str, report: RedactionReport) -> str:
    def _sub(m: re.Match) -> str:
        first = m.group("body").split()[0].lower().strip(".,'’")
        if first in _ADDRESS_STOPWORDS:
            return m.group(0)
        report.add("addresses")
        return "{{ADDRESS}}"

    return _RE_ADDRESS.sub(_sub, text)


def _scrub_names(text: str, report: RedactionReport, guess: bool) -> str:
    """Sostituisce i nomi di persona, dal segnale piu' forte al piu' debole."""

    # 1. Titolo professionale: "il geom. Nazzareno Sbrolli".
    def _title_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        while tokens and _is_common_word(tokens[-1]):
            tokens.pop()
        if not tokens:
            return m.group(0)
        kept = " ".join(tokens)
        report.add("names")
        return m.group(0).replace(name, "{{NAME}}" + name[len(kept):], 1)

    text = _RE_TITLE_NAME.sub(_title_sub, text)

    # 2. Nome accanto a un indirizzo di posta.
    def _email_name_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = name.split()
        dropped = []
        while tokens and _is_common_word(tokens[0]):
            dropped.append(tokens.pop(0))
        if not tokens:
            return m.group(0)
        report.add("names")
        prefix = (" ".join(dropped) + " ") if dropped else ""
        return m.group(0).replace(name, prefix + "{{NAME}}", 1)

    text = _RE_NAME_BEFORE_EMAIL.sub(_email_name_sub, text)
    text = _RE_NAME_AFTER_EMAIL.sub(_email_name_sub, text)

    # 3. Elenchi (nome proprio o cognome noto) e, se abilitata,
    #    4. euristica: due parole maiuscole che non sono parole italiane.
    def _pair_sub(m: re.Match) -> str:
        # Il pattern e' avido: "Studio Legale Trentini" arriva qui tutto
        # insieme. Una parola comune in mezzo non deve far cadere il
        # riconoscimento dell'intera sequenza, quindi si lavora sui tratti
        # continui di parole che comuni non sono, e il resto si ricompone
        # con gli spazi originali.
        parts = re.split(rf"({_SP})", m.group(0))
        tokens, seps = parts[0::2], parts[1::2]
        common = [_is_common_word(t) for t in tokens]

        pieces: list[tuple[str, int]] = []  # (testo, indice ultimo token)
        i = 0
        while i < len(tokens):
            if common[i]:
                pieces.append((tokens[i], i))
                i += 1
                continue
            j = i
            while j < len(tokens) and not common[j]:
                j += 1
            run = [t.lower().strip("'’-") for t in tokens[i:j]]
            known = any(t in FIRST_NAMES or t in SURNAMES for t in run)
            guessed = guess and not any(_looks_like_word(t) for t in run)
            if len(run) >= 2 and (known or guessed):
                report.add("names")
                pieces.append(("{{NAME}}", j - 1))
            else:
                original = tokens[i]
                for k in range(i + 1, j):
                    original += seps[k - 1] + tokens[k]
                pieces.append((original, j - 1))
            i = j

        out = pieces[0][0]
        for prev, cur in zip(pieces, pieces[1:]):
            out += seps[prev[1]] + cur[0]
        return out

    text = _RE_NAME_PAIR.sub(_pair_sub, text)

    # 5. Nome proprio isolato ("Ciao Marco,"). Solo se non e' anche una
    #    parola comune: "Rosa" da sola resta un fiore.
    def _lone_sub(m: re.Match) -> str:
        tok = m.group(0).lower().strip("'’-")
        if tok in _AMBIGUOUS_ALONE or tok in COMMON_CAPITALIZED:
            return m.group(0)
        if tok not in FIRST_NAMES:
            return m.group(0)
        report.add("names")
        return "{{NAME}}"

    return _RE_LONE_TOKEN.sub(_lone_sub, text)


def apply_privacy_filter(
    text: str,
    options: PrivacyOptions | None = None,
) -> tuple[str, RedactionReport]:
    """Apply selected redactions. Returns (cleaned_text, report).

    L'ordine non e' casuale: i segreti per primi (una chiave privata contiene
    di tutto), gli URL prima delle email (un indirizzo dentro un link non
    deve spezzare il link), i codici prima dei telefoni (una partita IVA e'
    undici cifre), i nomi per ultimi, quando i segnaposto gia' inseriti
    fanno da contesto.
    """
    if not text:
        return text, RedactionReport()

    opts = options or PrivacyOptions()
    report = RedactionReport()
    out = text

    if opts.secrets:
        out = _scrub_secrets(out, report)

    if opts.urls:
        out = _scrub_urls(out, report)

    if opts.emails:
        out = _replace_all(out, _RE_EMAIL, "{{EMAIL}}", report, "emails")

    if opts.fiscal:
        out = _replace_all(out, _RE_CF, "{{CODICE_FISCALE}}", report, "codice_fiscale")

        def _iban_sub(m: re.Match) -> str:
            if not iban_checksum_ok(m.group(1)):
                return m.group(0)
            report.add("iban")
            return "{{IBAN}}"

        out = _RE_IBAN.sub(_iban_sub, out)

        def _card_sub(m: re.Match) -> str:
            if not luhn_ok(m.group(1)):
                return m.group(0)
            report.add("cards")
            return "{{CARD}}"

        out = _RE_CARD.sub(_card_sub, out)

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

    if opts.dates:
        out = _scrub_birth_dates(out, report)

    if opts.phones:

        def _phone_sub(m: re.Match) -> str:
            if not _phone_is_plausible(m):
                return m.group(0)
            report.add("phones")
            return "{{PHONE}}"

        out = _RE_PHONE.sub(_phone_sub, out)

    if opts.amounts:

        def _amount_sub(m: re.Match) -> str:
            if not _amount_is_plausible(m):
                return m.group(0)
            report.add("amounts")
            return "{{AMOUNT}}"

        out = _RE_AMOUNT.sub(_amount_sub, out)

    if opts.addresses:
        out = _scrub_addresses(out, report)

    if opts.names:
        out = _scrub_names(out, report, guess=opts.name_guess)

    return out, report


# I campi booleani esposti da form, JSON e profili, con il loro valore
# predefinito. Tenerli in un posto solo evita che l'interfaccia e il motore
# vadano fuori sincrono quando se ne aggiunge uno.
FIELD_DEFAULTS: dict[str, bool] = {
    "emails": True,
    "phones": True,
    "names": True,
    "fiscal": True,
    "amounts": False,
    "urls": True,
    "addresses": True,
    "secrets": True,
    "dates": False,
    "name_guess": True,
}

# I campi che accendono davvero una sostituzione. ``name_guess`` non c'e':
# non e' un riconoscitore, e' un modo di riconoscere i nomi.
DETECTOR_FIELDS: tuple[str, ...] = tuple(
    k for k in FIELD_DEFAULTS if k != "name_guess"
)


def no_redaction() -> PrivacyOptions:
    """Tutti i riconoscitori spenti.

    Serve un modo solo di dirlo. Elencare i campi a mano nel punto in cui
    servono significa che il giorno in cui se ne aggiunge uno quel punto
    resta indietro — e siccome i valori predefiniti sono accesi, il difetto
    si manifesta come una redazione che avviene quando non dovrebbe.
    """
    return PrivacyOptions(**{k: False for k in FIELD_DEFAULTS})


def only(*fields: str) -> PrivacyOptions:
    """Solo i riconoscitori indicati, tutti gli altri spenti.

    Costruire ``PrivacyOptions`` elencando i campi da spegnere sembra
    equivalente e non lo e': i campi non nominati restano accesi, e un test
    che crede di isolare un riconoscitore ne sta misurando cinque.
    """
    unknown = set(fields) - set(FIELD_DEFAULTS)
    if unknown:
        raise ValueError(f"riconoscitori inesistenti: {sorted(unknown)}")
    return PrivacyOptions(**{k: (k in fields) for k in FIELD_DEFAULTS})


def options_from_form(form) -> PrivacyOptions:
    """Build PrivacyOptions from Flask request.form (or dict-like)."""
    def flag(key: str, default: bool) -> bool:
        if key not in form:
            return default
        val = form.get(key)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("1", "true", "yes", "on")

    # Master switch. Fail-safe: an API client that omits the field gets the
    # redactions, it never gets plaintext PII by accident (same default as the CLI).
    if not flag("privacy_filter", True):
        return no_redaction()

    return PrivacyOptions(
        **{k: flag("privacy_" + k, d) for k, d in FIELD_DEFAULTS.items()}
    )


def options_from_dict(data: dict | None) -> PrivacyOptions:
    data = data or {}
    if not data.get("privacy_filter", True):
        return no_redaction()
    return PrivacyOptions(
        **{k: bool(data.get("privacy_" + k, d)) for k, d in FIELD_DEFAULTS.items()}
    )
