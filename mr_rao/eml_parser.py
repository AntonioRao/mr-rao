"""Parse .eml files into structured Markdown (thread-aware, IT/EN)."""
from __future__ import annotations

import re
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup

from mr_rao.i18n import LINGUA_PREDEFINITA, t

# Reply / quote start patterns (IT + EN)
_REPLY_PATTERNS = [
    re.compile(r"^\s*On .+wrote:\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*Il giorno .+ha scritto:\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^-{3,}\s*(Original Message|Messaggio [Oo]riginale)\s*-{3,}\s*$",
        re.MULTILINE,
    ),
    re.compile(r"^\s*Da:\s*.+\n\s*Inviato:\s*.+\n\s*A:\s*.+", re.MULTILINE),
    re.compile(r"^\s*From:\s*.+\n\s*Sent:\s*.+\n\s*To:\s*.+", re.MULTILINE),
]


# Tutto cio' che non ha senso dentro un documento di testo: i controlli C0
# (il tab, \x09, resta) e il DEL. Gli a capo si trattano a parte, sotto.
_CONTROLLI = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def intestazione_su_una_riga(valore) -> str:
    """Riduce il valore di un'intestazione a una riga sola, pulita.

    Le intestazioni le scrive chi manda la mail, non noi: con la codifica
    RFC 2047 (`=?utf-8?B?...?=`) dentro un oggetto ci sta qualunque byte, a
    capo e caratteri di controllo compresi, e Python li restituisce tali e
    quali. Nel titolo `#` un a capo chiude il titolo e tutto il resto diventa
    testo del documento: abbastanza per scrivere sopra la tabella una finta
    riga «| **Da** | ... |» e far leggere un mittente che non esiste.
    """
    testo = _CONTROLLI.sub("", str(valore).replace("\r", "\n"))
    return " ".join(parte.strip() for parte in testo.split("\n") if parte.strip())


def cella_tabella(valore) -> str:
    """Come sopra, ma per una cella: la barra verticale va protetta.

    `| **Da** | Mario | Rossi <m@x.it> |` ha tre celle in una tabella a due
    colonne. Chi la disegna butta via l'eccedenza, e l'indirizzo del mittente
    sparisce dal documento: non e' un difetto estetico, e' un dato che manca.
    Basta un nome visualizzato con dentro un `|`, senza alcuna codifica.
    """
    return intestazione_su_una_riga(valore).replace("|", "\\|")


def html_to_text(html_content: str) -> str:
    """Convert HTML to readable plain text via BeautifulSoup."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "head"]):
            tag.decompose()
        for br in soup.find_all("br"):
            br.replace_with("\n")
        for p in soup.find_all("p"):
            p.insert_before("\n")
            p.insert_after("\n")
        text = soup.get_text()
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception:
        return re.sub(r"<[^>]+>", "", html_content)


def get_email_body(msg) -> str | None:
    if msg.is_multipart():
        text_parts: list[str] = []
        html_parts: list[str] = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue
            try:
                payload = part.get_content()
            except Exception:
                continue
            if isinstance(payload, str):
                if content_type == "text/plain":
                    text_parts.append(payload)
                elif content_type == "text/html":
                    html_parts.append(payload)
        if text_parts:
            return "\n\n".join(text_parts)
        if html_parts:
            return html_to_text("\n".join(html_parts))
        return None

    content_type = msg.get_content_type()
    try:
        payload = msg.get_content()
    except Exception:
        return None
    if isinstance(payload, str):
        if content_type == "text/html":
            return html_to_text(payload)
        return payload
    return None


def _strip_quote_markers(text: str) -> str:
    cleaned: list[str] = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("> "):
            cleaned.append(stripped[2:])
        elif stripped.startswith(">"):
            cleaned.append(stripped[1:])
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def _earliest_match(body: str) -> re.Match | None:
    """Return the match closest to the start of the string."""
    best: re.Match | None = None
    for pattern in _REPLY_PATTERNS:
        m = pattern.search(body)
        if m and (best is None or m.start() < best.start()):
            best = m
    return best


def split_thread(body: str, _depth: int = 0, _max_depth: int = 40) -> list[str]:
    """Split email body into conversation segments (newest → oldest)."""
    if not body or not body.strip() or _depth >= _max_depth:
        return [body.strip()] if body and body.strip() else []

    match = _earliest_match(body)
    if not match:
        return [body.strip()]

    before = body[: match.start()].strip()
    remaining = body[match.start() :]

    segments: list[str] = []
    if before:
        segments.append(before)

    cleaned = _strip_quote_markers(remaining)
    # Drop the first line if it's only the reply header
    lines = cleaned.split("\n")
    if lines:
        # Skip header-ish first lines already matched
        rest = "\n".join(lines[1:]).strip() if len(lines) > 1 else cleaned
        # Avoid infinite recursion if content does not shrink
        if rest and rest != body.strip():
            segments.extend(split_thread(rest, _depth + 1, _max_depth))
        elif rest:
            segments.append(rest)
    return segments or [body.strip()]


def list_attachments(msg, lingua: str = LINGUA_PREDEFINITA) -> list[tuple[str, int]]:
    attachments: list[tuple[str, int]] = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                # Il nome dell'allegato lo dichiara il mittente dentro il
                # Content-Disposition: puo' contenere un a capo e spezzare
                # l'elenco in due voci, una delle quali senza nome.
                fname = intestazione_su_una_riga(part.get_filename() or "") or t(
                    "doc_allegato_senza_nome", lingua
                )
                size = len(part.get_payload(decode=True) or b"")
                attachments.append((fname, size))
    return attachments


def extract_attachments(
    filepath: str | Path,
    max_bytes: int | None = None,
    lingua: str = LINGUA_PREDEFINITA,
) -> list[dict]:
    """Extract attachment payloads as base64 for download in the UI.

    Skips oversized parts (default from config.MAX_ATTACHMENT_BYTES).
    """
    import base64

    from config import MAX_ATTACHMENT_BYTES

    limit = max_bytes if max_bytes is not None else MAX_ATTACHMENT_BYTES
    filepath = Path(filepath)
    with open(filepath, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    out: list[dict] = []
    if not msg.is_multipart():
        return out
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition", ""))
        if "attachment" not in content_disposition:
            continue
        fname = part.get_filename() or "allegato.bin"
        raw = part.get_payload(decode=True) or b""
        mime = part.get_content_type() or "application/octet-stream"
        entry = {
            "filename": fname,
            "size": len(raw),
            "mime": mime,
            "skipped": False,
            "content_base64": None,
        }
        if len(raw) > limit:
            entry["skipped"] = True
            entry["reason"] = t(
                "doc_allegato_oltre", lingua, n=limit // (1024 * 1024)
            )
        else:
            entry["content_base64"] = base64.b64encode(raw).decode("ascii")
        out.append(entry)
    return out


def parse_eml(filepath: str | Path, lingua: str = LINGUA_PREDEFINITA) -> str:
    """Read .eml and produce structured Markdown for the full thread.

    ``lingua`` e' quella del *lavoro* di conversione, non della pagina: qui
    ci arriva anche la cartella sorvegliata, che di richieste HTTP non ne
    vede nessuna.
    """
    filepath = Path(filepath)
    with open(filepath, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    md_lines: list[str] = []

    # Nessuna di queste cinque righe e' testo nostro: le scrive chi manda la
    # mail. Vanno ripulite *prima* di entrare in un titolo o in una cella,
    # non dopo -- vedi intestazione_su_una_riga() e cella_tabella().
    subject = intestazione_su_una_riga(msg["subject"] or "") or t(
        "doc_nessun_oggetto", lingua
    )
    from_addr = cella_tabella(msg["from"] or "") or t("doc_mittente_sconosciuto", lingua)
    to_addr = cella_tabella(msg["to"] or "") or t("doc_destinatario_sconosciuto", lingua)
    cc_addr = cella_tabella(msg.get("cc", "") or "")
    date_str = cella_tabella(msg["date"] or "") or t("doc_data_sconosciuta", lingua)

    md_lines.append(f"# 📧 {subject}\n")
    md_lines.append(f"| {t('doc_campo', lingua)} | {t('doc_valore', lingua)} |")
    md_lines.append("|-------|--------|")
    md_lines.append(f"| **{t('doc_da', lingua)}** | {from_addr} |")
    md_lines.append(f"| **{t('doc_a', lingua)}** | {to_addr} |")
    if cc_addr:
        md_lines.append(f"| **{t('doc_cc', lingua)}** | {cc_addr} |")
    md_lines.append(f"| **{t('doc_data', lingua)}** | {date_str} |")
    md_lines.append("")

    attachments = list_attachments(msg, lingua)
    if attachments:
        md_lines.append(f"### 📎 {t('doc_allegati', lingua)}")
        for fname, size in attachments:
            md_lines.append(f"- `{fname}` ({size / 1024:.1f} KB)")
        md_lines.append("")

    md_lines.append("---\n")

    body = get_email_body(msg)
    if body:
        segments = split_thread(body)
        for i, segment in enumerate(segments):
            if i == 0:
                md_lines.append(f"### ✉️ {t('doc_ultimo_messaggio', lingua)}\n")
            else:
                md_lines.append("\n---\n")
                md_lines.append(
                    f"### 💬 {t('doc_messaggio_precedente', lingua, n=i)}\n"
                )
            cleaned = re.sub(r"\n{3,}", "\n\n", segment.strip())
            md_lines.append(cleaned)
            md_lines.append("")
    else:
        md_lines.append(f"> ⚠️ *{t('doc_eml_senza_testo', lingua)}*")

    # La nota in fondo NON si aggiunge qui. Questo testo passa dal filtro
    # privacy, e «Mr.» è un titolo esattamente come «Dott.» o «Ing.»: il
    # risultato era «Mr. {{NAME}}» — il tool che anonimizza se stesso — e
    # soprattutto **una redazione in più nel conteggio**, su ogni email.
    # Il numero che chiediamo all'utente di controllare non può contenere noi.
    # La nota la mette convert_file a valle: vedi nota_elaborazione().
    return "\n".join(md_lines)


def nota_elaborazione(lingua: str = LINGUA_PREDEFINITA) -> str:
    """La riga in fondo alle email convertite.

    Va aggiunta **dopo** il filtro privacy, mai prima: è testo nostro, non
    contenuto dell'utente, e non ha niente da farsi riconoscere dentro.

    La forma `> 🛡️ *…*` non è decorazione: `_RE_NOTA_PRIVACY` in
    converter.py e la sua gemella in app.js riconoscono le note *da lì*.
    Costruirla qui, in tutte le lingue, è quello che tiene le due
    espressioni valide anche in inglese.
    """
    return "\n---\n\n" + f"> 🛡️ *{t('doc_nota_elaborazione', lingua)}*"
