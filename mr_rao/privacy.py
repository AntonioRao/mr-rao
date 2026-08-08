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
from typing import Callable

from mr_rao.en_formats import (
    aba_routing_ok,
    abn_ok,
    itin_ok,
    mrz_check_digit_ok,
    nhs_number_ok,
    nino_ok,
    sin_ok,
    ssn_ok,
    tfn_ok,
)
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

# L'IBAN come lo stampano le banche: a gruppi di quattro. Il pattern sopra
# pretende i caratteri attaccati, quindi su "IT60 X054 2811 1010 0000 0123
# 456" — la forma piu' comune su carta intestata, bonifici e fatture — non
# trovava nulla. Qui i gruppi sono ammessi, e a scartare i falsi candidati
# ci pensa il mod-97 come sempre.
_RE_IBAN_SPAZIATO = re.compile(
    r"\b([A-Z]{2}\d{2}(?:[ \-][A-Z0-9]{2,6}){2,9})(?![\w])"
)

# Carta di pagamento: 13-19 cifre che iniziano con un IIN plausibile e
# passano il controllo di Luhn. Senza Luhn qualunque numero lungo finirebbe
# redatto; con Luhn e' il numero stesso a dire se e' una carta.
_RE_CARD = re.compile(r"(?<![\w.])([3-6]\d{3}(?:[ \-]?\d{2,6}){2,4})(?![\w])")

# Coordinate bancarie italiane senza IBAN: CIN + ABI (5) + CAB (5) + conto
# (12). Senza questo riconoscitore il numero non spariva del tutto: veniva
# spezzato e sostituito dal riconoscitore dei telefoni, quindi il rapporto
# diceva "2 telefoni" dove c'erano delle coordinate bancarie. Un conteggio
# che sbaglia categoria e' peggio di un conteggio che manca, perche' chi
# legge il rapporto si fida.
_RE_BBAN = re.compile(
    r"(?<![\w.])([A-Z])[\s\-]?(\d{5})[\s\-]?(\d{5})[\s\-]?([0-9A-Z]{12})(?![\w])"
)

# La forma discorsiva: "ABI 05428 CAB 11101 CIN X".
_RE_ABI_CAB = re.compile(
    r"(?i)\bABI[\s:]*\d{5}\b[\s,;]*(?:\bCAB[\s:]*\d{5}\b)?"
    r"(?:[\s,;]*\bCIN[\s:]*[A-Z]\b)?"
)


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

# L'indirizzo scritto per non farsi trovare dai raccoglitori automatici:
# "mario [at] esempio [dot] it". Chi lo scrive cosi' lo fa apposta perche'
# non sembri un'email — e infatti al riconoscitore non sembrava.
_RE_EMAIL_OFFUSCATA = re.compile(
    r"(?i)\b[A-Za-z0-9._%+\-]+\s*"
    r"(?:\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\}|\bchiocciola\b|\s+at\s+)\s*"
    r"[A-Za-z0-9\-]+"
    r"(?:\s*(?:\[\s*(?:dot|punto)\s*\]|\(\s*(?:dot|punto)\s*\)|\bpunto\b|\bdot\b|\.)\s*"
    r"[A-Za-z0-9\-]+)+"
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
#
# Le etichette sono divise in due gruppi perche' non valgono uguale.
# "password:" non ha altri significati; "chiave:" in italiano ne ha
# parecchi, e infatti "chiave: importante da ricordare" finiva sostituito.
_RE_SECRET_KV = re.compile(
    r"(?i)\b(password|passwd|pwd|parola d'ordine|token|api[_\- ]?key|"
    r"secret|client[_\- ]?secret|access[_\- ]?key|chiave (?:privata|segreta|api|di accesso))\b"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<val>[^\s,;\"']{6,})"
)

# Etichette ambigue: il valore deve anche *sembrare* una credenziale.
_RE_SECRET_KV_DEBOLE = re.compile(
    r"(?i)\b(chiave|credenziali|codice di accesso|passphrase)\b"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<val>[^\s,;\"']{6,})"
)


def _secret_value_is_plausible(valore: str) -> bool:
    """Una parola italiana non e' una credenziale.

    Serve solo per le etichette ambigue: una credenziale mescola cifre e
    lettere, contiene simboli, oppure e' lunga in un modo che le parole
    non sono.
    """
    if len(valore) >= 16:
        return True
    if any(c.isdigit() for c in valore) and any(c.isalpha() for c in valore):
        return True
    return any(not c.isalnum() for c in valore)


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
# Le formule di chiusura italiane. Quello che segue e' una persona: e'
# l'unico contesto in cui un cognome da solo vale come prova.
_CHIUSURE_IT = (
    r"cordiali\s+saluti|distinti\s+saluti|cordialmente|in\s+fede|"
    r"un\s+caro\s+saluto|cari\s+saluti|molti\s+saluti|saluti|ossequi|"
    r"grazie\s+e\s+saluti|resto\s+a\s+disposizione|a\s+presto"
)
_RE_FIRMA_IT = re.compile(
    rf"(?i:{_CHIUSURE_IT})[,.]?[ \t]*(?:\r?\n\s*|[ \t]+)"
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

_RE_NAME_BEFORE_EMAIL = re.compile(
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})(?P<sep>\s*[<\(\[]?\s*)\{{\{{EMAIL\}}\}}"
)
_RE_NAME_AFTER_EMAIL = re.compile(
    rf"\{{\{{EMAIL\}}\}}(?P<sep>\s*[<\(\[]\s*)(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Una sequenza *intera* di parole maiuscole, non una finestra di due o tre.
#
# Con la finestra, "Riferimento Del Piero Alessandro" veniva agganciata a
# partire da "Riferimento": tre parole consumate, dentro una sola del nome,
# e le altre lasciate indietro come parole isolate. Risultato:
# "Riferimento Del {{NAME}} {{NAME}}" — la particella fuori e il nome
# spezzato in due. Prendendo la sequenza intera e decidendo *dentro* quali
# tratti sono nomi, il problema non si pone: e' la stessa ragione per cui
# conviene rilevare gli intervalli prima e sostituirli dopo.
_RE_NAME_RUN = re.compile(rf"(?<!\w){_TOK}(?:{_SP}{_TOK})*(?!\w)")

# Oltre questa lunghezza non e' un nome: e' un titolo scritto in maiuscolo.
_MAX_TOKEN_NOME = 4

# Un nome scritto TUTTO MAIUSCOLO. Il pattern normale pretende almeno una
# minuscola — e' cosi' che esclude in un colpo solo acronimi, numeri romani
# e i segnaposto gia' inseriti — e questo lo rende cieco a "MARIO ROSSI",
# che nelle firme e nelle intestazioni delle mail e' frequentissimo.
# Trovato su una mail vera: quattro sequenze intatte su un testo in cui
# tutto il resto era stato sostituito.
_TOK_UP = r"[A-ZÀ-ÖØ-Þ]{3,}"
_RE_NAME_PAIR_UPPER = re.compile(rf"(?<![\w{{]){_TOK_UP}(?:{_SP}{_TOK_UP}){{1,2}}(?![\w}}])")

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
        # Cognomi frequentissimi che sono anche parole comuni. In coppia
        # restano riconoscibili ("Mario Costa"); da soli no, altrimenti
        # ogni "Costa" a inizio frase diventa una persona.
        "costa", "sala", "serra", "rocca", "croce", "prato", "riva", "villa",
        "gatto", "gatti", "gallo", "galli", "lupo", "lupi", "mele", "meli",
        "pesce", "oliva", "sordi", "grassi", "bianco", "bianchi", "verdi",
        "neri", "rossi", "russo", "greco", "moro", "biondi", "longo",
        "marino", "leone", "leoni", "monaco", "corona", "campana", "colomba",
        "fontana", "torre", "porta", "sacco", "cassa", "carta", "banca",
        "arena", "cava", "chiesa", "corso", "piazza", "valle", "monte",
        "ponte", "porto", "punta", "ripa", "sasso", "selva", "vetta",
    }
)


# ---------------------------------------------------------------------------
# Pacchetti
# ---------------------------------------------------------------------------
#
# Un riconoscitore o vale ovunque, o vale in un Paese solo. La distinzione
# non esisteva da nessuna parte: dentro l'unico interruttore ``fiscal``
# convivevano l'IBAN — mod-97, valido in tutti i Paesi SEPA — e il codice
# fiscale, che esiste solo qui. Chi voleva usare Mr. Rao su un documento
# straniero doveva prendersi anche i riconoscitori italiani, oppure
# rinunciare pure all'IBAN.
#
# I nomi restano quelli dei codici lingua ISO 639-1, cosi' il giorno in cui
# l'interfaccia avra' un selettore di lingua i due vocabolari coincidono.
CORE = "core"
IT = "it"
EN = "en"

PACCHETTI_NOTI: tuple[str, ...] = (CORE, IT, EN)


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
    #
    # **Spenta di default dalla 1.7.2** (#5). Era accesa, e su documenti
    # veri il conto e' questo: 8904 sostituzioni sbagliate su venti moduli
    # dell'Agenzia delle Entrate in bianco, 14376 su otto Gazzette
    # storiche, 2888 su novantanove moduli fiscali statunitensi. Tutti
    # documenti che non contengono un solo dato personale: mangiava
    # «Redditi Persone Fisiche», «Quadro RN», «Imposta Lorda».
    #
    # Non se n'era accorto nessuno perche' il banco a due corpora li
    # avevamo scritti noi, e un corpus scritto a mano contiene solo le
    # trappole a cui chi lo scrive ha pensato.
    name_guess: bool = False
    # Quali famiglie di riconoscitori eseguire. Il valore predefinito e' il
    # comportamento di sempre: nucleo universale piu' formati italiani.
    # Un documento inglese vorra' ``(CORE,)`` oggi e ``(CORE, EN)`` domani;
    # uno studio italiano che segue un cliente estero li vorra' entrambi.
    pacchetti: tuple[str, ...] = (CORE, IT, EN)
    # Prosa o modulo. La stessa regola ha segno opposto sulle due
    # popolazioni, e non e' un'opinione -- e' misurato su 127 documenti
    # amministrativi (verita' di riferimento zero) e 1500 email vere:
    #
    #   riscontro singolo negli elenchi   moduli: falsi pos.   email: nomi
    #   -> sospetto                                    1 637        2 823
    #   -> sostituzione                                4 376        3 432
    #
    # Su un modulo «sospetto» toglie 2 739 errori; su una lettera costa
    # 609 nomi che restano nel documento. Un valore solo peggiora una
    # delle due meta' per far contenta l'altra.
    #
    # ``None`` = non si sa. In quel caso si sceglie la prudenza sul
    # documento (sospetto) e non sul richiamo, perche' un falso positivo
    # si vede leggendo l'uscita, un nome lasciato in chiaro no.
    prosa: bool | None = None


@dataclass
class RedactionReport:
    counts: dict[str, int] = field(default_factory=dict)
    total: int = 0
    # Cio' che *assomiglia* a un dato personale ed e' rimasto nel testo.
    # Un riconoscitore che non trova nulla e un documento che non contiene
    # nulla producono lo stesso numero — zero — e sono due situazioni
    # opposte. I sospetti distinguono il silenzio dalla pulizia.
    suspects: list[dict] = field(default_factory=list)

    def add(self, kind: str, n: int = 1) -> None:
        if n <= 0:
            return
        self.counts[kind] = self.counts.get(kind, 0) + n
        self.total += n

    def suspect(self, kind: str, sample: str, why: str) -> None:
        self.suspects.append({"kind": kind, "sample": _mask(sample), "why": why})

    def to_dict(self) -> dict:
        return {
            "counts": dict(self.counts),
            "total": self.total,
            "suspects": list(self.suspects),
            "suspects_total": len(self.suspects),
        }


def _mask(s: str) -> str:
    """Quanto basta a ritrovarlo nel documento, non a leggerlo."""
    s = s.strip()
    if len(s) <= 4:
        return "•" * len(s)
    return f"{s[:2]}{'•' * (len(s) - 4)}{s[-2:]}"


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


# Tabelle del carattere di controllo del codice fiscale (DM 23/12/1976).
# I caratteri in posizione dispari pesano diversamente da quelli in
# posizione pari: e' quello che rende il controllo capace di accorgersi
# anche di due caratteri scambiati fra loro.
_CF_DISPARI = {
    **{c: v for c, v in zip("0123456789", (1, 0, 5, 7, 9, 13, 15, 17, 19, 21))},
    **{
        c: v
        for c, v in zip(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            (1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11,
             3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23),
        )
    },
}
_CF_PARI = {
    **{c: int(c) for c in "0123456789"},
    **{c: i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")},
}


def cf_check_char_ok(candidate: str) -> bool:
    """Carattere di controllo del codice fiscale.

    Non serve a rifiutare: un codice fiscale con la struttura giusta viene
    sostituito comunque, perche' su un dato personale l'errore va fatto
    nella direzione prudente. Serve a **sapere**: se la struttura torna e
    il carattere di controllo no, quasi sempre il documento arriva da un
    OCR che ha storpiato un carattere — e allora conviene guardare se ha
    storpiato anche qualcos'altro.
    """
    s = re.sub(r"[\s\-.]", "", candidate).upper()
    if len(s) != 16 or not s.isalnum():
        return False
    try:
        totale = sum(
            (_CF_DISPARI if i % 2 == 0 else _CF_PARI)[c]
            for i, c in enumerate(s[:15])
        )
    except KeyError:
        return False
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[totale % 26] == s[15]


def piva_check_ok(candidate: str) -> bool:
    """Cifra di controllo della partita IVA (undici cifre, Luhn all'italiana).

    Stessa scelta del codice fiscale: non rifiuta, informa. Undici cifre in
    un contesto fiscale restano sostituite comunque; se il controllo non
    torna, il numero diventa un sospetto — perche' o non era una partita
    IVA, o il documento e' storpiato.
    """
    p = re.sub(r"[\s\-.]", "", candidate)
    if len(p) != 11 or not p.isdigit():
        return False
    totale = 0
    for i, c in enumerate(p[:10]):
        n = int(c)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        totale += n
    return (10 - totale % 10) % 10 == int(p[10])


# ---------------------------------------------------------------------------
# Tolleranza agli errori dell'OCR, tenuta a bada dai checksum
# ---------------------------------------------------------------------------

# Le confusioni tipiche del riconoscimento ottico, nelle due direzioni.
# Non servono a indovinare: servono a proporre un candidato che poi deve
# passare il *suo* controllo matematico. E' l'unico modo di essere
# tolleranti senza aprire la porta ai falsi positivi.
_A_CIFRA = {
    "O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "E": "3",
    "A": "4", "S": "5", "G": "6", "T": "7", "B": "8", "J": "3",
}
_A_LETTERA = {
    "0": "O", "1": "I", "2": "Z", "3": "E", "4": "A", "5": "S", "6": "G",
    "7": "T", "8": "B",
}

# Confusioni fra lettere. Sembrano superflue — sono gia' lettere — ma la
# piu' frequente di tutte e' proprio questa: la elle minuscola letta al
# posto della i maiuscola. "IT60" diventa "lT60", che di lettere ne ha
# ancora due e quindi supera ogni controllo di forma, e fallisce il mod-97.
_FRA_LETTERE = {"l": "I", "|": "I", "¦": "I", "ı": "I", "…": "I"}

# Struttura del codice fiscale: L = lettera, D = cifra.
_CF_FORMA = "LLLLLLDDLDDLDDDL"

MAX_CORREZIONI_OCR = 2


def _coerce(token: str, forma: str) -> tuple[str, int] | None:
    """Porta ogni carattere nella classe che la struttura richiede.

    Restituisce (candidato, quante correzioni) oppure None se ne servono
    troppe: oltre due non e' piu' un errore di lettura, e' un altro dato.
    """
    if len(token) != len(forma):
        return None
    fuori = []
    corretti = 0
    for c, atteso in zip(token.upper(), forma):
        if atteso == "D":
            if c.isdigit():
                fuori.append(c)
                continue
            sostituto = _A_CIFRA.get(c)
        else:
            if c.isalpha():
                fuori.append(c)
                continue
            sostituto = _A_LETTERA.get(c)
        if sostituto is None:
            return None
        fuori.append(sostituto)
        corretti += 1
        if corretti > MAX_CORREZIONI_OCR:
            return None
    return "".join(fuori), corretti


def cf_ocr_recover(token: str) -> str | None:
    """Un codice fiscale storpiato dall'OCR, se il controllo lo conferma."""
    esito = _coerce(token, _CF_FORMA)
    if not esito:
        return None
    candidato, corretti = esito
    if corretti == 0 or not _RE_CF.fullmatch(candidato):
        return None
    return candidato if cf_check_char_ok(candidato) else None


def iban_ocr_recover(token: str) -> str | None:
    """Un IBAN storpiato dall'OCR, se il mod-97 lo conferma."""
    pulito = re.sub(r"\s", "", token)
    if not 15 <= len(pulito) <= 34:
        return None
    # Almeno una delle due iniziali dev'essere gia' una lettera.
    #
    # Senza questo vincolo il numero d'ordine 5551234567890123 diventava
    # "SS51234567890123" con due correzioni, e quel candidato il mod-97 lo
    # supera. Il checksum protegge dai candidati sbagliati, non da uno
    # spazio di candidati troppo largo: se puoi trasformare qualunque
    # sequenza di cifre in un IBAN, prima o poi ne azzecchi uno.
    if not any(c.isalpha() for c in pulito[:2]):
        return None
    forma = "LLDD" + "A" * (len(pulito) - 4)
    fuori = []
    corretti = 0
    for grezzo, atteso in zip(pulito, forma):
        c = grezzo.upper()
        if atteso == "A":  # alfanumerico: va bene qualunque cosa
            fuori.append(c)
            continue
        if atteso == "L":
            if grezzo in _FRA_LETTERE:
                sostituto = _FRA_LETTERE[grezzo]
            elif c.isalpha():
                fuori.append(c)
                continue
            else:
                sostituto = _A_LETTERA.get(c)
        else:
            if c.isdigit():
                fuori.append(c)
                continue
            sostituto = _A_CIFRA.get(c)
        if sostituto is None:
            return None
        corretti += 1
        if corretti > MAX_CORREZIONI_OCR:
            return None
        fuori.append(sostituto)
    candidato = "".join(fuori)
    if corretti == 0 or not candidato.isalnum():
        return None
    return candidato if iban_checksum_ok(candidato) else None


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

    prefix = m.group("prefix")
    if prefix:
        # Lo "00" internazionale e' anche l'inizio di moltissimi numeri di
        # pratica: "0034578921" e' un protocollo, e il pattern lo leggeva
        # come una chiamata in Spagna (00-34, poi sei cifre). Trovato su un
        # documento amministrativo inglese vero, dove ogni sostituzione e'
        # per definizione un errore.
        #
        # La differenza e' come sono scritti: un numero internazionale per
        # esteso ha quasi sempre una spaziatura -- "0044 7700 900412" --
        # mentre un codice di riferimento e' un blocco unico. Il "+" resta
        # affidabile senza altre prove, perche' dentro un numero di
        # protocollo non ci finisce.
        #
        # Il separatore va cercato in **tutta** la corrispondenza, non solo
        # nel corpo: in "0039 3391234567" lo spazio sta fra prefisso e
        # corpo, e guardare il solo corpo faceva rifiutare un numero vero.
        tutto = m.group(0)
        sep_ovunque = any(s in tutto for s in (" ", "-", "."))
        if prefix.startswith("00") and not sep_ovunque and not ctx:
            return False
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
    # Anche le parole che fermano il riconoscitore di indirizzi: "via
    # Corriere Espresso" non e' un indirizzo, e non e' neanche una
    # persona. Un presidio dentro un riconoscitore non protegge gli altri.
    t = token.lower().strip("'’-")
    return t in COMMON_CAPITALIZED or t in _ADDRESS_STOPWORDS


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


# Parole che dicono «questa sequenza e' un ente, non una persona».
# Trovate sui documenti veri, non immaginate: la sezione dell'otto per
# mille di un modello Redditi ne e' fatta quasi per intero.
_ENTITY_WORDS = frozenset(
    {
        "chiesa", "chiese", "parrocchia", "diocesi", "curia", "arcidiocesi",
        "congregazione", "confessione", "unione", "comunita", "comunità",
        "associazione", "associazioni", "fondazione", "fondazioni",
        "istituto", "istituti", "ente", "enti", "organizzazione", "onlus",
        "societa", "società", "cooperativa", "consorzio", "azienda",
        "agenzia", "ministero", "dipartimento", "direzione", "ufficio",
        "comune", "provincia", "regione", "prefettura", "questura",
        "camera", "tribunale", "procura", "corte", "commissione",
        "universita", "università", "ospedale", "banca", "cassa",
        "federazione", "confederazione", "sindacato", "partito",
        "repubblica", "stato", "governo", "presidenza", "segreteria",
        "gazzetta", "bollettino", "registro", "albo", "elenco",
    }
)


def _is_entity_word(token: str) -> bool:
    return token.lower().strip("'’-.,;:") in _ENTITY_WORDS


def _looks_like_word(token: str) -> bool:
    t = token.lower().strip("'’-")
    if len(t) < 5:
        return False
    return t.endswith(_WORDLIKE_SUFFIXES)


# Forme che *assomigliano* a un dato a struttura fissa. Girano sul testo
# gia' redatto: quello che e' stato sostituito non c'e' piu', quindi cio'
# che resta e' davvero rimasto.
_RE_QUASI_CF = re.compile(r"(?<![\w-])[A-Z0-9]{16}(?![\w-])")

# Per il recupero serve tollerare anche la minuscola: la elle minuscola
# letta al posto della i maiuscola e' la confusione piu' frequente di tutte.
_RE_FUZZY_CF = re.compile(r"(?<![\w-])[A-Za-z0-9]{16}(?![\w-])")

# Per l'IBAN il pattern dei sospetti non basta: pretende due cifre in
# terza e quarta posizione, e quelle sono proprio le posizioni che l'OCR
# storpia ("IT60" letto "IT6O"). Qui si accetta qualunque sequenza
# alfanumerica lunga come un IBAN, purche' almeno una delle due iniziali
# sia gia' una lettera; a scartarla ci pensa il mod-97.
_RE_FUZZY_IBAN = re.compile(
    r"(?<![\w-])(?=[A-Za-z0-9]?[A-Za-z])[A-Za-z0-9]{15,34}(?![\w-])"
)

# Le prime due lettere sono quelle che l'OCR sbaglia piu' spesso: "IT60"
# letto "lT60" o "1T6O". Qui non si pretende la maiuscola, altrimenti il
# sospetto non scatterebbe proprio nel caso che lo motiva.
_RE_QUASI_IBAN = re.compile(
    r"(?<![\w-])[A-Za-z0-9]{2}\d{2}[A-Za-z0-9]{11,30}(?![\w-])"
)

_RE_QUASI_CARTA = re.compile(r"(?<![\w.])(?:\d[ \-]?){15,16}(?![\w])")

# Un recapito storpiato: dopo "cell." o "tel." una sequenza che mescola
# cifre e lettere non e' un numero, ma quasi sempre lo era prima della
# scansione.
_RE_QUASI_TEL = re.compile(
    r"(?i)\b(?:tel|cell|cellulare|telefono|fax|recapito)\b\.?\s*[:\-]?\s*"
    r"(?P<val>[0-9A-Za-z][0-9A-Za-z \-.]{5,18}[0-9A-Za-z])"
)


def find_suspects(text: str, report: RedactionReport, opts: PrivacyOptions) -> None:
    """Segnala cio' che somiglia a un dato personale ed e' rimasto.

    E' la risposta al limite piu' serio del motore: sul testo prodotto da
    un OCR i riconoscitori cercano forme *valide* e trovano forme *quasi*
    valide — `A01` letto `AD1`, `IT60` letto `1T6O` — e il dato resta nel
    testo, ancora perfettamente leggibile da una persona.

    Non si puo' sostituire senza certezza, o si redige mezzo documento.
    Ma si puo' dire dove guardare: "3 redatti, 2 sospetti" e' una frase
    onesta, "3 redatti" da sola no.
    """
    if not text:
        return

    if opts.phones:
        for m in _RE_QUASI_TEL.finditer(text):
            tok = m.group("val")
            if sum(c.isdigit() for c in tok) >= 5 and any(c.isalpha() for c in tok):
                report.suspect(
                    "telefono",
                    tok,
                    "preceduto da una parola di contatto ma contiene lettere: "
                    "possibile lettura OCR sbagliata",
                )

    if opts.fiscal:
        # Il quasi-codice-fiscale e' italiano; il quasi-IBAN e la
        # quasi-carta valgono ovunque, quindi restano fuori dal pacchetto.
        if IT in opts.pacchetti:
            for m in _RE_QUASI_CF.finditer(text):
                tok = m.group(0)
                lettere = sum(c.isalpha() for c in tok)
                cifre = sum(c.isdigit() for c in tok)
                # Un hash o un identificativo non hanno questa proporzione.
                if 6 <= lettere <= 11 and 5 <= cifre <= 10:
                    report.suspect(
                        "codice_fiscale",
                        tok,
                        "sedici caratteri con la proporzione di un codice "
                        "fiscale, ma la struttura non torna: possibile "
                        "lettura OCR sbagliata",
                    )
        for m in _RE_QUASI_IBAN.finditer(text):
            tok = m.group(0)
            if sum(c.isalpha() for c in tok) < 3 or sum(c.isdigit() for c in tok) < 8:
                continue
            report.suspect(
                "iban",
                tok,
                "ha la forma di un IBAN ma non supera il controllo mod-97",
            )
        for m in _RE_QUASI_CARTA.finditer(text):
            cifre = re.sub(r"\D", "", m.group(0))
            if len(cifre) in (15, 16):
                report.suspect(
                    "carta",
                    m.group(0),
                    "sedici cifre che non superano il controllo di Luhn",
                )


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

    def _kv_debole(m: re.Match) -> str:
        if not _secret_value_is_plausible(m.group("val")):
            return m.group(0)
        report.add("secrets")
        return m.group(1) + m.group("sep") + "{{SECRET}}"

    text = _RE_SECRET_KV.sub(_kv, text)
    return _RE_SECRET_KV_DEBOLE.sub(_kv_debole, text)


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


def _scrub_names(
    text: str, report: RedactionReport, guess: bool, prosa: bool | None = None
) -> str:
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
        # Una sola parola maiuscola davanti a un indirizzo non basta a
        # farne un nome: davanti a un'email ci finisce di tutto, a
        # partire dai verbi. "Contatta mario@x.it" faceva sparire il
        # verbo. Serve una coppia — nome e cognome — oppure una parola
        # che negli elenchi ci sia davvero.
        if len(tokens) == 1:
            solo = tokens[0].lower().strip("'’-")
            if solo not in FIRST_NAMES and solo not in SURNAMES:
                return m.group(0)
        report.add("names")
        prefix = (" ".join(dropped) + " ") if dropped else ""
        return m.group(0).replace(name, prefix + "{{NAME}}", 1)

    text = _RE_NAME_BEFORE_EMAIL.sub(_email_name_sub, text)
    text = _RE_NAME_AFTER_EMAIL.sub(_email_name_sub, text)

    # 2-bis. La firma. Una formula di chiusura dichiara che quello che
    # segue e' una persona, ed e' l'unico posto dove un cognome da solo --
    # «Cordiali saluti, Esposito» -- e' davvero un cognome e non la parola
    # «esposito». Senza questa regola, portare gli elenchi da «sostituisce»
    # a «segnala» avrebbe fatto sopravvivere le firme, che sono il punto in
    # cui il nome compare quasi sempre.
    def _firma_sub(m: re.Match) -> str:
        name = m.group("name")
        tokens = [t.lower().strip("'’-.,;:") for t in name.split()]
        if not tokens or all(_is_common_word(t) or _is_entity_word(t) for t in tokens):
            return m.group(0)
        report.add("names")
        return m.group(0).replace(name, "{{NAME}}", 1)

    text = _RE_FIRMA_IT.sub(_firma_sub, text)

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
        # Una parola d'ente da' un nome all'intera sequenza, e quel nome
        # non e' di una persona: «CHIESA EVANGELICA VALDESE» e' un ente,
        # non un cognome, e sui moduli dell'otto per mille compare a
        # decine. E' lo stesso presidio che nel pacchetto inglese impedisce
        # a «Green Lane Logistics» di diventare una persona -- li' lo fanno
        # i tipi di via, qui le parole di ente.
        if any(_is_entity_word(t) for t in tokens):
            return m.group(0)
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
            # **Due** riscontri, non uno.
            #
            # Prima bastava che *una* parola della sequenza stesse negli
            # elenchi perche' l'intera sequenza sparisse. Su un modulo
            # amministrativo e' quasi sempre vero per caso: gli elenchi
            # contengono 2181 cognomi, e molti sono anche parole comuni --
            # Chiesa, Costa, Monte, Villa, Ponte, Sala, Carta, Banca.
            # «Imposta Lorda» spariva perche' una delle due somigliava a un
            # cognome.
            #
            # Nome e cognome adiacenti, entrambi riconosciuti, sono invece
            # una prova vera: e' la stessa regola che nel pacchetto inglese
            # decide «Sarah Whitfield». Il riscontro singolo non si butta,
            # diventa un **sospetto**: il documento resta intatto e chi
            # legge sa dove guardare.
            noti = sum(1 for t in run if t in FIRST_NAMES or t in SURNAMES)
            guessed = guess and not any(_looks_like_word(t) for t in run)
            lungo_giusto = 2 <= len(run) <= _MAX_TOKEN_NOME
            # Su prosa un riscontro solo basta: «da Ludovica Sbrancagnoli»
            # in una frase e' quasi sempre una persona, e pretendere due
            # riscontri costerebbe 609 nomi su 1500 email vere. Su un
            # modulo lo stesso riscontro e' quasi sempre un'etichetta, e
            # accettarlo costa 2 739 sostituzioni sbagliate.
            bastano = 1 if prosa else 2
            if lungo_giusto and (noti >= bastano or guessed):
                report.add("names")
                pieces.append(("{{NAME}}", j - 1))
            else:
                if lungo_giusto and noti == 1 and not prosa:
                    report.suspect(
                        "nome",
                        " ".join(tokens[i:j]),
                        "una sola parola risulta negli elenchi dei nomi: "
                        "non basta a dire che sia una persona, ma potrebbe "
                        "esserlo",
                    )
                original = tokens[i]
                for k in range(i + 1, j):
                    original += seps[k - 1] + tokens[k]
                pieces.append((original, j - 1))
            i = j

        out = pieces[0][0]
        for prev, cur in zip(pieces, pieces[1:]):
            out += seps[prev[1]] + cur[0]
        return out

    text = _RE_NAME_RUN.sub(_pair_sub, text)
    text = _RE_NAME_PAIR_UPPER.sub(_pair_sub, text)

    # 5. Nome o cognome isolato ("Ciao Marco,", una firma con il solo
    #    cognome). Solo se non e' anche una parola comune: "Rosa" da sola
    #    resta un fiore, "Costa" da sola resta un costo.
    def _lone_sub(m: re.Match) -> str:
        tok = m.group(0).lower().strip("'’-")
        # Sotto le quattro lettere una parola isolata non e' una prova.
        # «Re» e' un cognome italiano vero, ed e' anche una parola, un
        # titolo e mezza abbreviazione: su un modello Redditi in bianco
        # veniva sostituito cinque volte. Stessa sorte per «Rao», che sta
        # nel nostro stesso nome.
        #
        # Un elenco di eccezioni non basterebbe: i cognomi corti che sono
        # anche parole sono decine, e ne salterebbero fuori altri a ogni
        # documento nuovo. Meglio una regola che si spiega in una riga.
        #
        # Il prezzo: un cognome corto scritto da solo, senza titolo e
        # senza indirizzo accanto, non viene piu' preso. Era l'appiglio
        # piu' debole che avevamo, ed e' quello che sbagliava di piu'.
        if len(tok) < 4:
            return m.group(0)
        if tok in _AMBIGUOUS_ALONE or tok in COMMON_CAPITALIZED:
            return m.group(0)
        # Il veto morfologico c'era gia', ma girava solo sulle coppie e non
        # sulla parola isolata -- che e' l'appiglio piu' debole dei due, e
        # avrebbe quindi dovuto essere il piu' protetto. Le terminazioni
        # italiane (-zione, -mento, -ale) dicono «questa e' una parola»
        # meglio di qualunque elenco di eccezioni scritto a mano, che va
        # allungato a ogni documento nuovo.
        if _looks_like_word(tok):
            return m.group(0)
        if tok not in FIRST_NAMES and tok not in SURNAMES:
            return m.group(0)
        # Una parola sola, in elenco, senza nient'altro intorno: e' il
        # segnale piu' debole che abbiamo, e sostituire su quello vuol dire
        # cancellare «Costa», «Monte» e «Villa» ogni volta che compaiono in
        # un documento amministrativo. Diventa un sospetto: il documento
        # resta leggibile e chi lo controlla sa dove guardare.
        report.suspect(
            "nome",
            m.group(0),
            "risulta negli elenchi dei nomi ma non ha nulla intorno che "
            "dica che sia una persona: nessun titolo, nessuna firma, "
            "nessun indirizzo accanto",
        )
        return m.group(0)

    return _RE_LONE_TOKEN.sub(_lone_sub, text)


def _scrub_emails(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    out = _replace_all(text, _RE_EMAIL, "{{EMAIL}}", report, "emails")
    return _replace_all(out, _RE_EMAIL_OFFUSCATA, "{{EMAIL}}", report, "emails")


def _scrub_cf(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        # Si sostituisce comunque: su un dato personale l'errore va fatto
        # nella direzione prudente. Ma se la struttura torna e il carattere
        # di controllo no, quasi sempre il testo viene da un OCR che ha
        # storpiato un carattere -- e allora ne avra' storpiati altri, che
        # nessun riconoscitore ha visto.
        if not cf_check_char_ok(m.group(1)):
            report.suspect(
                "codice_fiscale",
                m.group(1),
                "sostituito, ma il carattere di controllo non torna: "
                "il documento potrebbe contenere altri dati storpiati",
            )
        report.add("codice_fiscale")
        return "{{CODICE_FISCALE}}"

    return _RE_CF.sub(_sub, text)


def _scrub_iban(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if not iban_checksum_ok(m.group(1)):
            return m.group(0)
        report.add("iban")
        return "{{IBAN}}"

    out = _RE_IBAN.sub(_sub, text)
    return _RE_IBAN_SPAZIATO.sub(_sub, out)


def _scrub_cards(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if not luhn_ok(m.group(1)):
            return m.group(0)
        report.add("cards")
        return "{{CARD}}"

    return _RE_CARD.sub(_sub, text)


def _scrub_bban(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    # Prima dei telefoni: 22 cifre di coordinate bancarie hanno la stessa
    # forma di due numeri di telefono attaccati.
    def _sub(m: re.Match) -> str:
        ctx = _context_before(m.string, m.start(), 40).lower()
        if not any(k in ctx for k in ("bban", "coordinate", "c/c", "conto", "cin ")):
            return m.group(0)
        report.add("bban")
        return "{{BBAN}}"

    out = _RE_BBAN.sub(_sub, text)
    return _replace_all(out, _RE_ABI_CAB, "{{BBAN}}", report, "bban")


# Recupero dei codici storpiati dall'OCR. Gira dopo i riconoscitori esatti,
# su cio' che e' rimasto, e sostituisce *solo* se il checksum del candidato
# corretto torna. E' quello che permette di essere tolleranti senza aprire
# ai falsi positivi: non decide un'euristica, decide l'aritmetica.
def _scrub_fuzzy_cf(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if cf_ocr_recover(m.group(0)) is None:
            return m.group(0)
        report.add("codice_fiscale")
        report.add("ocr_corretti")
        return "{{CODICE_FISCALE}}"

    return _RE_FUZZY_CF.sub(_sub, text)


def _scrub_fuzzy_iban(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if iban_ocr_recover(m.group(0)) is None:
            return m.group(0)
        report.add("iban")
        report.add("ocr_corretti")
        return "{{IBAN}}"

    return _RE_FUZZY_IBAN.sub(_sub, text)


def _scrub_piva(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    # Only replace if preceded by context keywords nearby or IT prefix.
    def _sub(m: re.Match) -> str:
        ctx = _context_before(m.string, m.start()).lower()
        raw = m.group(0)
        if raw.upper().startswith("IT") or any(
            k in ctx for k in ("p.iva", "piva", "partita", "vat", "c.f.")
        ):
            # Stessa scelta del codice fiscale: sostituisce comunque, e se
            # la cifra di controllo non torna lo dice.
            if not piva_check_ok(m.group(1)):
                report.suspect(
                    "partita_iva",
                    m.group(1),
                    "sostituita, ma la cifra di controllo non torna: "
                    "o non era una partita IVA, o il documento e' storpiato",
                )
            report.add("partita_iva")
            return "{{PARTITA_IVA}}"
        return raw

    return _RE_PIVA.sub(_sub, text)


def _scrub_phones(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if not _phone_is_plausible(m):
            return m.group(0)
        report.add("phones")
        return "{{PHONE}}"

    return _RE_PHONE.sub(_sub, text)


def _scrub_amounts(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        if not _amount_is_plausible(m):
            return m.group(0)
        report.add("amounts")
        return "{{AMOUNT}}"

    return _RE_AMOUNT.sub(_sub, text)


# ---------------------------------------------------------------------------
# Pacchetto EN: gli identificativi anglosassoni
# ---------------------------------------------------------------------------
#
# La regola che decide qui e' una sola, e viene da una misura: su 20.000
# sequenze casuali di nove cifre, il controllo strutturale del SSN ne accetta
# quasi il novanta per cento. Non e' un validatore, e' un filtro di forma.
# Quindi **niente si sostituisce sulle cifre nude**: o c'e' la punteggiatura
# che identifica il formato (i trattini 3-2-4 del SSN), o c'e' una parola di
# contesto accanto. Dove invece esiste un checksum vero -- NHS mod-11,
# routing 3-7-1, SIN Luhn -- il validatore fa meta' del lavoro e il contesto
# copre l'altra meta'.
#
# Senza questa regola il pacchetto EN redigerebbe numeri di protocollo,
# codici articolo e riferimenti di fattura: esattamente il difetto che il
# corpus amministrativo esiste per intercettare.

_RE_SSN = re.compile(r"(?<![\w-])(\d{3}-\d{2}-\d{4})(?![\w-])")
# Due lettere qualsiasi, non solo quelle ammesse: le esclusioni di HMRC le
# applica ``nino_ok``. Metterle nel pattern sembra piu' efficiente e invece
# rompe la regola della casa -- il pattern propone, il validatore decide --
# e soprattutto rende invisibile il caso che conta: un NINO vero con le due
# lettere storpiate dall'OCR non somiglierebbe piu' a niente, e non
# finirebbe nemmeno fra i sospetti.
_RE_NINO = re.compile(
    r"(?<![\w])([A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D])(?![\w])"
)
# Dieci cifre, nella spaziatura 3-3-4 in cui l'NHS le stampa oppure attaccate.
_RE_NHS = re.compile(r"(?<![\w-])(\d{3}[ -]?\d{3}[ -]?\d{4})(?![\w-])")
_RE_NOVE_CIFRE = re.compile(r"(?<![\w-])(\d{3}[ -]?\d{3}[ -]?\d{3}|\d{9})(?![\w-])")

_CTX_NHS = ("nhs", "health number", "patient number")
_CTX_ROUTING = ("routing", "aba", "rtn", "transit number")
_CTX_SIN = ("sin", "social insurance", "numero di assicurazione sociale")


def _con_contesto(m: re.Match, parole: tuple[str, ...], finestra: int = 40) -> bool:
    ctx = _context_before(m.string, m.start(), finestra).lower()
    return any(p in ctx for p in parole)


def _scrub_en_ssn(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """SSN e ITIN, solo nella forma trattinata 3-2-4.

    Nove cifre attaccate non si toccano: sarebbero indistinguibili da un
    numero di pratica. I trattini nelle posizioni giuste sono l'unica cosa
    che rende il formato riconoscibile, e le esclusioni della SSA (aree
    000, 666, 900-999; gruppo 00; seriale 0000) fanno il resto.

    L'ITIN va provato per primo: comincia per 9, che ``ssn_ok`` rifiuta.
    """
    def _sub(m: re.Match) -> str:
        raw = m.group(1)
        if itin_ok(raw):
            report.add("itin")
            return "{{ITIN}}"
        if ssn_ok(raw):
            report.add("ssn")
            return "{{SSN}}"
        # La forma c'e' ma la SSA quel numero non l'ha mai emesso: non si
        # sostituisce, e lo si dice.
        report.suspect(
            "ssn",
            raw,
            "ha la forma di un SSN ma cade in un intervallo mai assegnato: "
            "o non e' un SSN, o e' storpiato",
        )
        return raw

    return _RE_SSN.sub(_sub, text)


def _scrub_en_nino(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """National Insurance Number britannico.

    Nessun checksum, ma le esclusioni di HMRC -- D, F, I, Q, U, V mai come
    prima o seconda lettera, O mai come seconda, sette prefissi mai
    allocati -- tolgono buona parte dello spazio delle lettere, e la forma
    «due lettere, sei cifre, una lettera fra A e D» in un testo normale non
    capita per caso.
    """
    def _sub(m: re.Match) -> str:
        if not nino_ok(m.group(1)):
            # La forma c'e' ma il prefisso non e' fra quelli allocati.
            # Succede in due casi opposti: qualcuno ha copiato l'esempio di
            # gov.uk (che usa QQ apposta, perche' non viene mai emesso),
            # oppure un OCR ha storpiato le lettere di un NINO vero. Il
            # secondo caso e' il motivo per cui va segnalato.
            report.suspect(
                "nino",
                m.group(1),
                "ha la forma di un National Insurance Number ma il prefisso "
                "non e' mai stato allocato: o e' un esempio, o e' storpiato",
            )
            return m.group(0)
        report.add("nino")
        return "{{NINO}}"

    return _RE_NINO.sub(_sub, text)


def _scrub_en_nhs(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """NHS number: mod-11, ma serve comunque il contesto.

    Il mod-11 lascia passare circa una sequenza di dieci cifre su nove: da
    solo redigerebbe numeri di fattura. Con la parola «NHS» accanto invece
    e' quasi certo, ed e' cosi' che compare nei documenti veri.
    """
    def _sub(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_NHS) or not nhs_number_ok(m.group(1)):
            return m.group(0)
        report.add("nhs_number")
        return "{{NHS_NUMBER}}"

    return _RE_NHS.sub(_sub, text)


def _scrub_en_nove_cifre(
    text: str, report: RedactionReport, opts: PrivacyOptions
) -> str:
    """Routing bancario statunitense e SIN canadese.

    Stessa lunghezza, checksum diversi, e nessuno dei due si puo' cercare
    senza contesto: nove cifre sono la forma piu' comune che esista in un
    documento amministrativo. Sono un passo solo perche' competono per lo
    stesso testo, e chi decide e' la parola che sta davanti.
    """
    def _sub(m: re.Match) -> str:
        raw = m.group(1)
        if _con_contesto(m, _CTX_ROUTING) and aba_routing_ok(raw):
            report.add("routing_number")
            return "{{ROUTING_NUMBER}}"
        if _con_contesto(m, _CTX_SIN) and sin_ok(raw):
            report.add("sin")
            return "{{SIN}}"
        return raw

    return _RE_NOVE_CIFRE.sub(_sub, text)


# ---------------------------------------------------------------------------
# Indirizzi inglesi, e il codice postale che ci sta dentro
# ---------------------------------------------------------------------------
#
# Il discriminante e' **il numero civico**, e non e' un dettaglio.
#
# In italiano l'indirizzo comincia con la parola: «via», «piazza», «corso».
# In inglese finisce con essa -- Street, Road, Lane, Way -- e quelle parole
# formano anche i nomi delle cose: «the loading bay on Church Road», «the
# Sterling Way depot», «Green Lane Logistics», «the Young Street office».
# Sono tutte nel corpus amministrativo, e un riconoscitore che si fermasse
# al tipo di via le redigerebbe tutte e quattro.
#
# Un indirizzo vero porta il civico davanti. E' l'unica differenza
# strutturale affidabile fra «47 Baker Street» e «Baker Street».

_EN_TIPI_VIA = (
    r"street|st|road|rd|avenue|ave|lane|ln|close|drive|way|court|ct|place|pl|"
    r"square|sq|terrace|gardens|gdns|crescent|cres|row|walk|mews|boulevard|"
    r"blvd|highway|hwy|parkway|pkwy|circle|cir|trail"
)

# Il codice postale britannico, nella forma che compare nella posta
# ordinaria. La regex ufficiale del governo ha anche i rami dei territori
# d'oltremare, che accettano cose come "AB 12": in un documento
# amministrativo quella forma capita per caso.
_UK_POSTCODE = r"[A-Z]{1,2}\d[A-Z\d]?[ ]?\d[A-Z]{2}"
_US_ZIP = r"\d{5}(?:-\d{4})?"

_RE_EN_ADDRESS = re.compile(
    r"(?<![\w/-])"
    r"\d{1,5}[A-Za-z]?"                                   # il civico
    rf"{_SP}(?:{_TOK}{_SP}){{0,3}}(?i:{_EN_TIPI_VIA})\b"   # ... Baker Street
    rf"(?:{_SP}(?i:NE|NW|SE|SW|N|S|E|W)\b)?"              # ... Avenue NW
    rf"(?:,[ \t]*[^,\n]{{1,40}}){{0,3}}"                  # interno, citta'
    rf"(?:[ \t]+(?:{_UK_POSTCODE}|{_US_ZIP}))?"           # e il codice postale
)

# Un codice postale rimasto fuori da un indirizzo completo. Da solo non si
# tocca: la forma britannica somiglia a un codice articolo. Serve una
# parola che dica che li' c'e' un recapito.
_RE_EN_POSTCODE = re.compile(rf"(?<![\w-])({_UK_POSTCODE})(?![\w-])")
_CTX_INDIRIZZO = (
    "postcode", "post code", "zip", "address", "residing", "resident",
    "delivery", "registered office", "correspondence",
)


def _scrub_en_addresses(
    text: str, report: RedactionReport, opts: PrivacyOptions
) -> str:
    def _sub(m: re.Match) -> str:
        report.add("addresses")
        return "{{ADDRESS}}"

    out = _RE_EN_ADDRESS.sub(_sub, text)

    def _sub_cap(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_INDIRIZZO):
            return m.group(0)
        report.add("addresses")
        return "{{POSTCODE}}"

    return _RE_EN_POSTCODE.sub(_sub_cap, out)


# ---------------------------------------------------------------------------
# Australia, e i documenti di viaggio
# ---------------------------------------------------------------------------

_RE_ABN = re.compile(r"(?<![\w-])(\d{2}[ ]?\d{3}[ ]?\d{3}[ ]?\d{3}|\d{11})(?![\w-])")
_RE_TFN = re.compile(r"(?<![\w-])(\d{3}[ ]?\d{3}[ ]?\d{2,3})(?![\w-])")

_CTX_ABN = ("abn", "australian business number")
_CTX_TFN = ("tfn", "tax file number")

# Le righe in fondo a un passaporto: solo maiuscole, cifre e il riempitivo
# "<". Il doppio riempitivo e' cio' che nessun'altra riga di testo ha, ed e'
# quello che rende la ricerca sicura.
#
# Si cerca il **blocco**, non la singola riga, e la ragione e' che la prima
# riga -- quella che contiene cognome e nome -- finisce con i riempitivi,
# non con una cifra di controllo. Cercando riga per riga, quella non
# avrebbe superato nessun controllo: sarebbe diventata un sospetto, e il
# nome sarebbe rimasto nel documento. Cioe' il difetto peggiore possibile,
# proprio sulla riga che conta di piu'.
_RE_MRZ = re.compile(r"(?m)^(?:[A-Z0-9<]{28,44}\r?\n){1,2}[A-Z0-9<]{28,44}$")


def _scrub_en_au(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """ABN e TFN australiani.

    Entrambi hanno un checksum vero -- mod-89 e mod-11 -- ma entrambi sono
    solo cifre: senza la sigla accanto si redigerebbero i totali di una
    fattura. Il checksum riduce il rumore, il contesto lo azzera.
    """
    def _sub_abn(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_ABN) or not abn_ok(m.group(1)):
            return m.group(0)
        report.add("abn")
        return "{{ABN}}"

    def _sub_tfn(m: re.Match) -> str:
        if not _con_contesto(m, _CTX_TFN) or not tfn_ok(m.group(1)):
            return m.group(0)
        report.add("tfn")
        return "{{TFN}}"

    out = _RE_ABN.sub(_sub_abn, text)
    return _RE_TFN.sub(_sub_tfn, out)


def _scrub_mrz(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    """La zona a lettura automatica di un passaporto o di una carta.

    Non si cerca il numero del documento: da solo non ha nulla che lo
    distingua da un codice qualsiasi. Si cerca la **riga** -- solo
    maiuscole, cifre e riempitivi, con almeno un doppio "<" -- e poi la
    cifra di controllo ICAO conferma che non e' una stringa qualunque.

    Vale la pena perche' una riga MRZ contiene cognome, nome,
    cittadinanza, data di nascita, sesso e scadenza tutti insieme: e' il
    pezzo di testo piu' denso di dati personali che possa capitare in un
    documento scansionato.
    """
    def _sub(m: re.Match) -> str:
        blocco = m.group(0)
        if "<<" not in blocco:
            return blocco
        # I campi che portano la propria cifra di controllo subito accanto:
        # numero del documento (posizioni 1-10), data di nascita (14-20),
        # scadenza (22-28). Non si usa la cifra composita di fine riga
        # perche' quella si calcola su pezzi **non contigui**, e darle in
        # pasto la riga intera la fa sempre fallire.
        campi = ((0, 10), (13, 20), (21, 28))
        righe = blocco.splitlines()
        if not any(
            mrz_check_digit_ok(r[a:b])
            for r in righe
            for a, b in campi
            if len(r) >= b and r[b - 1].isdigit()
        ):
            report.suspect(
                "mrz",
                blocco.replace("\n", " "),
                "ha la forma della zona a lettura automatica di un documento "
                "ma nessuna cifra di controllo torna: possibile lettura OCR "
                "sbagliata, e li' dentro ci sono nome, nascita e cittadinanza",
            )
            return blocco
        report.add("mrz")
        return "{{MRZ}}"

    return _RE_MRZ.sub(_sub, text)


# ---------------------------------------------------------------------------
# Nomi inglesi: solo dove il testo dice che e' un nome
# ---------------------------------------------------------------------------
#
# Qui non c'e' nessun elenco di nomi, ed e' una scelta.
#
# In italiano l'euristica «due parole maiuscole che non sono parole
# italiane» regge perche' -zione, -mento e -ale sono terminazioni di parole
# e non di cognomi. In inglese quella separazione non esiste: -son, -ton,
# -er sono entrambe le cose. E le parole inglesi comunissime che sono anche
# nomi -- Mark, Bill, Grace, Will, May, June, Rose, Brown, Green, Baker,
# Price, Young, Church, Sterling -- rendono qualunque elenco una macchina
# per falsi positivi. Misurato: il motore italiano applicato a un documento
# amministrativo inglese produceva 22 sostituzioni su un testo senza un
# solo dato personale, e 22 su un modulo fiscale statunitense in bianco.
#
# Quindi si sostituisce **solo dove il testo dichiara che quella e' una
# persona**: un titolo davanti, una formula di apertura o di chiusura, un
# indirizzo di posta accanto. Sono regole di contesto pure, che non
# costano un byte di dati e non sbagliano quasi mai.
#
# Il prezzo e' dichiarato: un nome in mezzo a una frase, senza titolo e
# senza firma, **sopravvive**. Per prenderlo servirebbe un modello, che
# violerebbe la promessa del prodotto (issue #4). Chi vuole quel richiamo
# la' sa dove chiederlo; chi legge il report vede il divario nei sospetti
# invece di scoprirlo dopo.

# «Rev.» e «Hon.» erano in questo elenco e sono stati tolti dopo averli
# visti mordere su documenti veri: su un modulo fiscale statunitense in
# bianco, «(Rev. January 2011)» -- cioe' *revised* -- diventava
# «(Rev. {{NAME}} 2011)». Un titolo che vale anche come abbreviazione di
# un'altra parola non e' una prova di contesto: e' un'ambiguita'.
_EN_TITOLI = (
    r"mr|mrs|ms|miss|mx|dr|prof|professor|sir|dame|"
    r"capt|captain|lord|lady|madam"
)

# Parole che seguono un titolo o un «Dear» senza essere nomi di persona.
# Senza questo elenco «Dear Sir», «Dear All» e «Dear Team» diventerebbero
# tre falsi positivi in cima a ogni lettera formale.
_EN_NON_NOMI = frozenset(
    {
        "sir", "sirs", "madam", "madams", "all", "team", "teams",
        "colleagues", "colleague", "customer", "customers", "client",
        "clients", "friend", "friends", "both", "everyone", "everybody",
        "member", "members", "resident", "residents", "parent", "parents",
        "student", "students", "applicant", "applicants", "reader",
    }
)

_RE_EN_TITLE_NAME = re.compile(
    rf"(?<!\w)(?i:{_EN_TITOLI})\.?{_SP}(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# «Dear James,» — l'apertura epistolare e' la dichiarazione piu' esplicita
# che esista: quello che segue e' una persona, o e' una delle formule
# generiche di _EN_NON_NOMI.
_RE_EN_DEAR = re.compile(
    rf"(?<!\w)(?i:dear|attn|attention|c/o)[:.]?{_SP}"
    rf"(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# La firma: una formula di chiusura, un a capo, e il nome. E' il punto in
# cui in una mail di lavoro il nome compare praticamente sempre, e dove
# nessun'altra regola lo prenderebbe -- non ha titolo davanti e non ha
# l'indirizzo accanto.
_EN_CHIUSURE = (
    r"(?:kind|best|warm|kindest)?\s*regards|"
    r"yours\s+(?:sincerely|faithfully|truly)|sincerely(?:\s+yours)?|"
    r"best\s+wishes|many\s+thanks|with\s+thanks|thanks\s+and\s+regards"
)
_RE_EN_FIRMA = re.compile(
    rf"(?i:{_EN_CHIUSURE})[,.]?[ \t]*\r?\n\s*(?P<name>{_TOK}(?:{_SP}{_TOK}){{0,2}})"
)

# Un nome attaccato a un indirizzo gia' sostituito. A differenza
# dell'italiano non si accetta **mai** una parola sola: senza elenchi non
# c'e' modo di distinguere «Contact {{EMAIL}}» da «Sarah {{EMAIL}}», e il
# verbo verrebbe redatto. Due parole maiuscole davanti a un indirizzo sono
# invece quasi sempre nome e cognome.
_RE_EN_NOME_PRIMA_EMAIL = re.compile(
    rf"(?P<name>{_TOK}{_SP}{_TOK}(?:{_SP}{_TOK})?)"
    rf"(?P<sep>\s*[<\(\[]\s*)\{{\{{EMAIL\}}\}}"
)
_RE_EN_NOME_DOPO_EMAIL = re.compile(
    rf"\{{\{{EMAIL\}}\}}(?P<sep>\s*[<\(\[]\s*)"
    rf"(?P<name>{_TOK}{_SP}{_TOK}(?:{_SP}{_TOK})?)"
)


def _en_nome_utile(name: str) -> str | None:
    """Toglie dalla coda le parole che non sono nomi, e dice se resta nulla."""
    tokens = name.split()
    while tokens and tokens[-1].lower().strip(".,;:'’-") in _EN_NON_NOMI:
        tokens.pop()
    if not tokens:
        return None
    if tokens[0].lower().strip(".,;:'’-") in _EN_NON_NOMI:
        return None
    return " ".join(tokens)


def _scrub_en_names(text: str, report: RedactionReport, opts: PrivacyOptions) -> str:
    def _sub(m: re.Match) -> str:
        name = m.group("name")
        utile = _en_nome_utile(name)
        if utile is None:
            return m.group(0)
        report.add("names")
        # Si sostituisce solo la parte utile: la coda ("Thank you" dopo la
        # virgola non ci arriva, ma un titolo di coda si').
        return m.group(0).replace(name, "{{NAME}}" + name[len(utile):], 1)

    for pattern in (
        _RE_EN_TITLE_NAME,
        _RE_EN_DEAR,
        _RE_EN_FIRMA,
        _RE_EN_NOME_PRIMA_EMAIL,
        _RE_EN_NOME_DOPO_EMAIL,
    ):
        text = pattern.sub(_sub, text)
    return text


@dataclass(frozen=True)
class Passo:
    """Un riconoscitore nella sequenza, con il pacchetto che lo possiede.

    ``nome`` non e' decorativo: e' l'identificativo con cui i test dicono
    quale passo intendono, e non deve cambiare quando cambia il nome della
    funzione.
    """

    nome: str
    pacchetto: str
    campo: str  # il campo di PrivacyOptions che lo accende
    priorita: int
    esegui: Callable[[str, RedactionReport, PrivacyOptions], str]


# **L'ordine di questa lista e' il comportamento del motore.** Non e'
# casuale: i segreti per primi (una chiave privata contiene di tutto), gli
# URL prima delle email (un indirizzo dentro un link non deve spezzare il
# link), i codici prima dei telefoni (una partita IVA e' undici cifre), i
# nomi per ultimi, quando i segnaposto gia' inseriti fanno da contesto.
# Spostare una riga qui cambia cio' che esce: il banco golden se ne accorge.
#
# La **priorita' e' del tipo di dato, non del pacchetto**: un codice fiscale
# (it) e un SSN (en) devono girare insieme, prima dei telefoni, perche' e'
# quello che oggi impedisce a un telefono di mangiarsi una partita IVA. Se
# l'ordine seguisse i pacchetti, aggiungerne un terzo lo romperebbe -- e si
# vedrebbe come una redazione sbagliata, non come un errore di ordinamento.
SEQUENZA: tuple[Passo, ...] = (
    Passo("secrets", CORE, "secrets", 10, lambda t, r, o: _scrub_secrets(t, r)),
    Passo("urls", CORE, "urls", 20, lambda t, r, o: _scrub_urls(t, r)),
    Passo("emails", CORE, "emails", 30, _scrub_emails),
    # La riga MRZ di un passaporto contiene cognome, nome, cittadinanza,
    # data di nascita e scadenza tutti insieme: va tolta intera, prima che
    # gli altri riconoscitori la smontino a pezzi e ne lascino meta'.
    Passo("mrz", EN, "fiscal", 39, _scrub_mrz),
    # I codici: 40-49. L'ordine interno conta -- i riconoscitori esatti
    # prima di quelli tolleranti all'OCR, che girano su cio' che e' rimasto.
    Passo("codice_fiscale", IT, "fiscal", 40, _scrub_cf),
    Passo("iban", CORE, "fiscal", 41, _scrub_iban),
    Passo("cards", CORE, "fiscal", 42, _scrub_cards),
    Passo("bban", IT, "fiscal", 43, _scrub_bban),
    Passo("codice_fiscale_ocr", IT, "fiscal", 44, _scrub_fuzzy_cf),
    Passo("iban_ocr", CORE, "fiscal", 45, _scrub_fuzzy_iban),
    Passo("partita_iva", IT, "fiscal", 46, _scrub_piva),
    # Gli identificativi anglosassoni stanno nella stessa fascia dei codici
    # italiani, non dopo: e' la ragione per cui la priorita' e' del tipo di
    # dato. Un SSN deve essere deciso prima che il riconoscitore dei
    # telefoni veda nove cifre e le prenda per un recapito.
    Passo("ssn", EN, "fiscal", 47, _scrub_en_ssn),
    Passo("nino", EN, "fiscal", 47, _scrub_en_nino),
    Passo("nhs_number", EN, "fiscal", 48, _scrub_en_nhs),
    Passo("routing_sin", EN, "fiscal", 49, _scrub_en_nove_cifre),
    Passo("abn_tfn", EN, "fiscal", 49, _scrub_en_au),
    Passo("date_nascita", IT, "dates", 50, lambda t, r, o: _scrub_birth_dates(t, r)),
    # Il pattern e' internazionale (prefisso +CC, parola di contesto anche
    # in inglese); restano italiane solo le due scorciatoie senza contesto,
    # cellulare 3xx e fisso 0xx, dentro _phone_is_plausible. Vanno separate
    # quando arrivera' il pacchetto inglese con le regole NANP.
    Passo("phones", CORE, "phones", 60, _scrub_phones),
    # Euro e parole italiane: "importo", "imponibile", "canone".
    Passo("amounts", IT, "amounts", 65, _scrub_amounts),
    Passo("addresses", IT, "addresses", 70, lambda t, r, o: _scrub_addresses(t, r)),
    Passo("addresses_en", EN, "addresses", 71, _scrub_en_addresses),
    Passo(
        "names", IT, "names", 90,
        lambda t, r, o: _scrub_names(t, r, guess=o.name_guess, prosa=o.prosa),
    ),
    # Stessa fascia dei nomi italiani: se i due pacchetti sono accesi
    # insieme gira prima quello italiano, che e' piu' aggressivo, e questo
    # raccoglie cio' che resta.
    Passo("names_en", EN, "names", 91, _scrub_en_names),
)


def apply_privacy_filter(
    text: str,
    options: PrivacyOptions | None = None,
) -> tuple[str, RedactionReport]:
    """Apply selected redactions. Returns (cleaned_text, report).

    I riconoscitori, il loro ordine e il pacchetto a cui appartengono stanno
    tutti in ``SEQUENZA``. Qui resta solo la regola di esecuzione: un passo
    gira se il suo pacchetto e' fra quelli scelti **e** se il suo
    interruttore e' acceso. Erano due cose diverse scritte come una sola.
    """
    if not text:
        return text, RedactionReport()

    opts = options or PrivacyOptions()
    report = RedactionReport()
    out = text

    attivi = set(opts.pacchetti)
    # Ordinamento stabile: a parita' di priorita' vale l'ordine di
    # dichiarazione in SEQUENZA, che e' l'ordine dei pacchetti core -> it.
    for passo in sorted(SEQUENZA, key=lambda p: p.priorita):
        if passo.pacchetto not in attivi:
            continue
        if not getattr(opts, passo.campo):
            continue
        out = passo.esegui(out, report, opts)

    find_suspects(out, report, opts)
    return out, report


# I campi booleani esposti da form, JSON e profili, con il loro valore
# predefinito. Tenerli in un posto solo evita che l'interfaccia e il motore
# vadano fuori sincrono quando se ne aggiunge uno.
# I pacchetti nazionali, come interruttori. Il nucleo non c'e': vale
# ovunque e non si spegne, spegnerlo vorrebbe dire rinunciare a IBAN e
# carte su qualunque documento.
#
# Sono campi separati da FIELD_DEFAULTS perche' rispondono a una domanda
# diversa: quelli dicono *quali dati* nascondere, questi *di quale Paese*.
# Un utente puo' volere tutti i riconoscitori accesi su documenti solo
# italiani, o solo gli indirizzi su documenti di due Paesi.
PACK_FIELD_DEFAULTS: dict[str, bool] = {
    IT: True,
    EN: True,
}


def _pacchetti_da(flag) -> tuple[str, ...]:
    """Costruisce la tupla dei pacchetti a partire da due booleani."""
    scelti = [p for p, d in PACK_FIELD_DEFAULTS.items() if flag("privacy_pack_" + p, d)]
    return (CORE, *scelti)


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
    "name_guess": False,
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
        pacchetti=_pacchetti_da(flag),
        **{k: flag("privacy_" + k, d) for k, d in FIELD_DEFAULTS.items()},
    )


def options_from_dict(data: dict | None) -> PrivacyOptions:
    data = data or {}
    if not data.get("privacy_filter", True):
        return no_redaction()
    return PrivacyOptions(
        pacchetti=_pacchetti_da(lambda k, d: bool(data.get(k, d))),
        **{k: bool(data.get("privacy_" + k, d)) for k, d in FIELD_DEFAULTS.items()},
    )
