"""Parse .eml files into structured Markdown (thread-aware, IT/EN)."""
from __future__ import annotations

import re
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup

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


def list_attachments(msg) -> list[tuple[str, int]]:
    attachments: list[tuple[str, int]] = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                fname = part.get_filename() or "(allegato senza nome)"
                size = len(part.get_payload(decode=True) or b"")
                attachments.append((fname, size))
    return attachments


def extract_attachments(filepath: str | Path, max_bytes: int | None = None) -> list[dict]:
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
            entry["reason"] = f"oltre {limit // (1024 * 1024)} MB"
        else:
            entry["content_base64"] = base64.b64encode(raw).decode("ascii")
        out.append(entry)
    return out


def parse_eml(filepath: str | Path) -> str:
    """Read .eml and produce structured Markdown for the full thread."""
    filepath = Path(filepath)
    with open(filepath, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    md_lines: list[str] = []

    subject = msg["subject"] or "(nessun oggetto)"
    from_addr = msg["from"] or "(mittente sconosciuto)"
    to_addr = msg["to"] or "(destinatario sconosciuto)"
    cc_addr = msg.get("cc", "")
    date_str = msg["date"] or "(data sconosciuta)"

    md_lines.append(f"# 📧 {subject}\n")
    md_lines.append("| Campo | Valore |")
    md_lines.append("|-------|--------|")
    md_lines.append(f"| **Da** | {from_addr} |")
    md_lines.append(f"| **A** | {to_addr} |")
    if cc_addr:
        md_lines.append(f"| **CC** | {cc_addr} |")
    md_lines.append(f"| **Data** | {date_str} |")
    md_lines.append("")

    attachments = list_attachments(msg)
    if attachments:
        md_lines.append("### 📎 Allegati")
        for fname, size in attachments:
            md_lines.append(f"- `{fname}` ({size / 1024:.1f} KB)")
        md_lines.append("")

    md_lines.append("---\n")

    body = get_email_body(msg)
    if body:
        segments = split_thread(body)
        for i, segment in enumerate(segments):
            if i == 0:
                md_lines.append("### ✉️ Ultimo messaggio\n")
            else:
                md_lines.append("\n---\n")
                md_lines.append(f"### 💬 Messaggio precedente #{i}\n")
            cleaned = re.sub(r"\n{3,}", "\n\n", segment.strip())
            md_lines.append(cleaned)
            md_lines.append("")
    else:
        md_lines.append("> ⚠️ *Nessun contenuto testuale trovato nel file .eml.*")

    # La nota in fondo NON si aggiunge qui. Questo testo passa dal filtro
    # privacy, e «Mr.» è un titolo esattamente come «Dott.» o «Ing.»: il
    # risultato era «Mr. {{NAME}}» — il tool che anonimizza se stesso — e
    # soprattutto **una redazione in più nel conteggio**, su ogni email.
    # Il numero che chiediamo all'utente di controllare non può contenere noi.
    # La nota la mette convert_file a valle: vedi nota_elaborazione().
    return "\n".join(md_lines)


def nota_elaborazione() -> str:
    """La riga in fondo alle email convertite.

    Va aggiunta **dopo** il filtro privacy, mai prima: è testo nostro, non
    contenuto dell'utente, e non ha niente da farsi riconoscere dentro.
    """
    return (
        "\n---\n\n"
        "> 🛡️ *Documento elaborato da Mr. Rao. "
        "Se il filtro privacy è attivo, i dati personali sono stati sostituiti "
        "con segnaposto.*"
    )
