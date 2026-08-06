"""Core conversion pipeline: documents, images, EML → Markdown + frontmatter."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from config import APP_NAME, APP_VERSION, IMAGE_EXTENSIONS
from mr_rao.ocr_service import extract_pdf_tables, ocr_image, ocr_pdf_fallback
from mr_rao.privacy import (
    DETECTOR_FIELDS,
    PrivacyOptions,
    RedactionReport,
    apply_privacy_filter,
)

ProgressCb = Callable[[int, int, str], None]
CancelCb = Callable[[], bool]

_md = None
_md_lock = threading.Lock()


def get_markitdown():
    global _md
    if _md is None:
        with _md_lock:  # two concurrent uploads must not build two instances
            if _md is None:
                from markitdown import MarkItDown

                _md = MarkItDown()
    return _md


class Cancelled(Exception):
    """Raised at a pipeline stage boundary when the user cancelled the job."""


def _stop_if_cancelled(should_cancel: CancelCb | None) -> None:
    if should_cancel and should_cancel():
        raise Cancelled()


@dataclass
class ConvertOptions:
    engine: str = "auto"  # auto | rapidocr | markitdown
    language: str = "it"
    privacy: PrivacyOptions = field(default_factory=PrivacyOptions)
    include_tables: bool = True
    include_frontmatter: bool = True
    clean_output: bool = False  # strip HTML comments / privacy footers for LLM paste
    force_ocr_pdf: bool = False
    include_raw: bool = True  # keep pre-privacy text for diff
    extract_attachments: bool = True


@dataclass
class ConvertResult:
    markdown: str
    engine_used: str
    source_name: str
    source_ext: str
    redaction: RedactionReport = field(default_factory=RedactionReport)
    empty: bool = False
    error: str | None = None
    markdown_raw: str | None = None  # before privacy (for diff)
    attachments: list[dict] = field(default_factory=list)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _empty_message(reason: str | None = None) -> str:
    """Il messaggio quando non esce testo.

    Se la conversione e' fallita per una causa nostra, quella causa va
    detta. Attribuire al documento una colpa che e' del programma manda
    l'utente a cercare il problema dove non c'e': un .docx pieno di testo
    che riceve «non contiene testo riconoscibile» perche' manca una
    libreria e' successo davvero, e per parecchie versioni.
    """
    if reason:
        return (
            "> ⚠️ **Conversione non riuscita.**\n>\n"
            f"> {reason}\n>\n"
            "> Non dipende dal documento."
        )
    return (
        "> ⚠️ **Nessun testo estratto.**\n>\n"
        "> Il file caricato non contiene testo riconoscibile.\n>\n"
        "> **Suggerimenti:**\n"
        "> - Se è un'immagine, assicurati che il testo sia leggibile.\n"
        "> - Se è un PDF, prova **Forza RapidOCR** o abilita le tabelle.\n"
        "> - Se è protetto da password, rimuovi la protezione prima."
    )


# Pacchetto necessario per ogni formato che dichiariamo di leggere. Serve
# a due cose: dire all'utente cosa manca invece di dare la colpa al file,
# e far fallire i test quando un formato annunciato non e' installabile.
FORMAT_DEPENDENCIES: dict[str, tuple[str, str]] = {
    ".docx": ("docx", "python-docx"),
    ".doc": ("docx", "python-docx"),
    ".pptx": ("pptx", "python-pptx"),
    ".ppt": ("pptx", "python-pptx"),
    ".xlsx": ("openpyxl", "openpyxl"),
    ".xls": ("xlrd", "xlrd"),
    ".pdf": ("pdfminer", "pdfminer.six"),
}


def missing_dependency_for(ext: str) -> str | None:
    """Il pacchetto mancante per questa estensione, se manca."""
    entry = FORMAT_DEPENDENCIES.get(ext.lower())
    if not entry:
        return None
    module, package = entry
    try:
        __import__(module)
    except ImportError:
        return package
    return None


def _is_ocr(engine_used: str) -> bool:
    return "rapidocr" in (engine_used or "")


def _ocr_privacy_warning() -> str:
    """Avviso da allegare quando la redazione ha lavorato su testo OCR.

    I riconoscitori sono espressioni regolari: cercano un codice fiscale o un
    IBAN scritti *bene*. Se l'OCR legge `A01` come `AD1`, o `IBAN IT60` come
    `TBAN1TB0`, il codice non viene riconosciuto e resta nel testo — storpiato
    ma ancora sufficiente a identificare una persona.

    È il caso in cui la protezione è più debole ed è insieme quello in cui
    serve di più, perché i documenti scansionati sono spesso i più delicati.
    Chi legge il risultato deve saperlo.
    """
    return (
        "> ⚠️ *Testo ottenuto via OCR: l'anonimizzazione riconosce solo i dati "
        "letti correttamente. Se il riconoscimento ha sbagliato un carattere, "
        "un codice fiscale o un IBAN può essere sfuggito. "
        "**Controlla il confronto prima/dopo prima di condividere.***"
    )


def _togli_commenti_html(text: str) -> str:
    """Rimuove i commenti HTML scandendo il testo una volta sola.

    Qui c'era ``re.sub(r"<!--.*?-->", ...)``. Con un documento fatto di
    ``<!--`` mai chiusi il motore riparte da ogni apertura e arriva ogni volta
    in fondo: tempo quadratico sulla lunghezza. Il limite d'invio è 50 MB, che
    è abbastanza per bloccare un worker a tempo indeterminato — e il documento
    lo sceglie chi lo carica, non noi.

    Nessuna riscrittura furba dell'espressione risolve il problema, perché a
    essere quadratico è il *numero di partenze*, non il singolo tentativo.
    Due ``find`` che avanzano sempre in avanti sono lineari e si leggono meglio.
    """
    pezzi: list[str] = []
    i = 0
    while True:
        inizio = text.find("<!--", i)
        if inizio == -1:
            pezzi.append(text[i:])
            return "".join(pezzi)
        fine = text.find("-->", inizio + 4)
        if fine == -1:
            # Commento aperto e mai chiuso: si tiene com'è, non è compito
            # nostro indovinare dove finiva.
            pezzi.append(text[i:])
            return "".join(pezzi)
        pezzi.append(text[i:inizio])
        i = fine + 3
        if text.startswith("\n", i):
            i += 1


# Le note che l'applicazione stessa scrive, sempre a inizio riga. Ancorate a
# ``^`` con ``\n?`` in coda invece che in testa: davanti rendeva ambiguo dove
# comincia il match, ed era la seconda segnalazione di complessità.
_RE_NOTA_PRIVACY = re.compile(r"^> (?:🛡️|ℹ️) \*.*$\n?", re.MULTILINE)


def _strip_noise(text: str) -> str:
    """Clean copy for LLM paste: drop HTML comments and trailing privacy notes."""
    text = _togli_commenti_html(text)
    text = _RE_NOTA_PRIVACY.sub("", text)
    return text.strip()


_RE_YAML_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*\s*:")


def strip_frontmatter(markdown: str) -> str:
    """Remove the leading YAML block, if there really is one.

    "starts with ---" is not enough: a document whose first line is a Markdown
    horizontal rule would lose everything up to the next '---'. The second line
    must also look like a YAML key.
    """
    if not markdown.startswith("---"):
        return markdown
    lines = markdown.split("\n")
    if len(lines) < 3 or lines[0].strip() != "---":
        return markdown
    if not _RE_YAML_KEY.match(lines[1]):
        return markdown
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return "\n".join(lines[i + 1 :]).lstrip("\n")
    return markdown


def _yaml_str(value: str) -> str:
    """Quote a scalar so any filename is valid YAML (colons, quotes, #, ...)."""
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _frontmatter(
    source_name: str,
    source_ext: str,
    engine_used: str,
    file_hash: str,
    redaction: RedactionReport,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generator: {_yaml_str(f'{APP_NAME} {APP_VERSION}')}",
        f"source: {_yaml_str(source_name)}",
        f"format: {_yaml_str(source_ext.lstrip('.'))}",
        f"engine: {_yaml_str(engine_used)}",
        f"converted_at: {now}",
        f"source_hash: {_yaml_str(file_hash)}",
    ]
    if redaction.total:
        # Nested mapping — "redactions: 5" followed by indented keys is not valid YAML.
        lines.append("redactions:")
        lines.append(f"  total: {redaction.total}")
        for k, v in sorted(redaction.counts.items()):
            lines.append(f"  {k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


def convert_file(
    filepath: str | Path,
    original_name: str | None = None,
    options: ConvertOptions | None = None,
    progress: ProgressCb | None = None,
    should_cancel: CancelCb | None = None,
) -> ConvertResult:
    # Shallow copy: callers (batch, hotfolder) reuse a single ConvertOptions
    # across files, so this function must never write back into it.
    opts = replace(options) if options is not None else ConvertOptions()
    path = Path(filepath)
    original_name = original_name or path.name
    ext = path.suffix.lower()
    if not ext and original_name and "." in original_name:
        ext = "." + original_name.rsplit(".", 1)[-1].lower()

    engine_used = "none"
    final_text: str | None = None
    failure_reason: str | None = None
    file_hash = _file_sha256(path) if path.exists() else "unknown"
    attachments: list[dict] = []

    try:
        _stop_if_cancelled(should_cancel)

        if ext == ".eml":
            if progress:
                progress(1, 1, "Parsing thread email…")
            from mr_rao.eml_parser import extract_attachments, parse_eml

            final_text = parse_eml(path)
            engine_used = "eml_parser"
            if opts.extract_attachments:
                try:
                    attachments = extract_attachments(path)
                except Exception as e:
                    print(f"EML attachments error: {e}")
            # NOTE: no privacy override here. Whether an .eml defaults to redacted
            # is decided once at the boundary (options_from_form / CLI defaults);
            # forcing it here would both ignore an explicit "no redaction" choice
            # and leak that choice into the next file of a batch.

        elif ext in IMAGE_EXTENSIONS and opts.engine in ("auto", "rapidocr"):
            if progress:
                progress(1, 1, "OCR immagine…")
            final_text = ocr_image(path, language=opts.language)
            engine_used = "rapidocr"

        elif ext == ".pdf" and opts.engine == "rapidocr":
            # Must stay ahead of the generic branch: a PDF is not an image,
            # feeding it to ocr_image() fails with "cannot identify image file".
            if progress:
                progress(0, 1, "OCR PDF…")
            final_text = ocr_pdf_fallback(
                path,
                language=opts.language,
                progress=progress,
                should_cancel=should_cancel,
                include_tables=opts.include_tables,
            )
            engine_used = "rapidocr_pdf"

        else:
            # MarkItDown for documents
            if progress:
                progress(0, 2, "Conversione documento…")
            try:
                md_result = get_markitdown().convert(str(path))
                final_text = md_result.text_content
                engine_used = "markitdown"
            except Exception as e:
                print(f"MarkItDown conversion error: {e}")
                final_text = None
                mancante = missing_dependency_for(ext)
                if mancante:
                    failure_reason = (
                        f"Manca la libreria **{mancante}**, necessaria per "
                        f"leggere i file `{ext}`. Installala con "
                        f"`pip install {mancante}`, oppure usa il pacchetto "
                        f"portable, che la contiene."
                    )
                # Portable resilience if Magika models are missing
                if ext in {".txt", ".csv", ".md", ".json", ".xml", ".html", ".htm", ".rtf"}:
                    try:
                        final_text = path.read_text(encoding="utf-8", errors="replace")
                        engine_used = "plaintext_fallback"
                    except Exception as e2:
                        print(f"Plaintext fallback error: {e2}")

            tables_extra = ""
            if ext == ".pdf" and opts.include_tables:
                try:
                    tables_extra = extract_pdf_tables(path)
                except Exception as e:
                    print(f"Table extract error: {e}")

            # engine == "rapidocr" never reaches here: it is dispatched above.
            needs_ocr = ext == ".pdf" and (
                opts.force_ocr_pdf or not final_text or not str(final_text).strip()
            )
            if needs_ocr and ext == ".pdf":
                if progress:
                    progress(1, 2, "PDF vuoto o forzato OCR…")
                ocr_text = ocr_pdf_fallback(
                    path,
                    language=opts.language,
                    progress=progress,
                    should_cancel=should_cancel,
                    include_tables=opts.include_tables and not tables_extra,
                )
                if ocr_text:
                    final_text = ocr_text
                    engine_used = "rapidocr_pdf_fallback"
            elif tables_extra and final_text:
                final_text = final_text.rstrip() + "\n\n---\n\n## Tabelle estratte\n\n" + tables_extra
                engine_used = "markitdown+tables"
            elif tables_extra and not final_text:
                final_text = tables_extra
                engine_used = "pdf_tables"

        # Cancel is honoured at every stage boundary. A single markitdown call
        # is not interruptible from outside, so the earliest we can stop is
        # here — before the (often much slower) privacy pass over the text.
        _stop_if_cancelled(should_cancel)

        redaction = RedactionReport()
        markdown_raw: str | None = None
        # Un campo alla volta, non "almeno uno": aggiungendo un
        # riconoscitore nuovo ci si dimentica sempre di questo elenco, e il
        # sintomo e' un filtro che sembra spento quando e' acceso.
        privacy_on = bool(
            final_text
            and any(getattr(opts.privacy, name) for name in DETECTOR_FIELDS)
        )
        if privacy_on and final_text:
            if opts.include_raw:
                markdown_raw = final_text
            final_text, redaction = apply_privacy_filter(final_text, opts.privacy)
            if _is_ocr(engine_used):
                final_text = final_text.rstrip() + "\n\n" + _ocr_privacy_warning()

        empty = not final_text or not str(final_text).strip()
        if empty:
            final_text = _empty_message(failure_reason)
            empty = True

        _stop_if_cancelled(should_cancel)

        if opts.clean_output and final_text:
            final_text = _strip_noise(final_text)
            if markdown_raw:
                markdown_raw = _strip_noise(markdown_raw)

        if opts.include_frontmatter and final_text and not empty:
            fm = _frontmatter(original_name, ext, engine_used, file_hash, redaction)
            final_text = fm + final_text
            if markdown_raw is not None:
                markdown_raw = fm + markdown_raw

        return ConvertResult(
            markdown=final_text or "",
            engine_used=engine_used,
            source_name=original_name,
            source_ext=ext,
            redaction=redaction,
            empty=empty,
            markdown_raw=markdown_raw,
            attachments=attachments,
        )
    except Cancelled:
        return ConvertResult(
            markdown="",
            engine_used="cancelled",
            source_name=original_name,
            source_ext=ext,
            error="Conversione annullata",
        )
    except Exception as e:
        print(f"convert_file error: {e}")
        return ConvertResult(
            markdown="",
            engine_used=engine_used,
            source_name=original_name,
            source_ext=ext,
            error="Errore durante la conversione. Controlla il file e riprova.",
        )


def convert_bytes(
    data: bytes,
    filename: str,
    options: ConvertOptions | None = None,
    progress: ProgressCb | None = None,
    should_cancel: CancelCb | None = None,
) -> ConvertResult:
    """Write bytes to a secure temp file, convert, delete. Minimizes disk dwell time."""
    ext = Path(filename).suffix.lower()
    fd, tmp = tempfile.mkstemp(suffix=ext or ".bin", prefix="mrrao_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return convert_file(
            tmp,
            original_name=filename,
            options=options,
            progress=progress,
            should_cancel=should_cancel,
        )
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def merge_markdowns(
    results: list[ConvertResult],
    title: str = "Documento unificato",
    *,
    compare_mode: bool = False,
) -> str:
    """Merge multiple conversion results into one Markdown document.

    If compare_mode and exactly 2 results, labels them Documento A / B.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [
        "---",
        f"generator: {APP_NAME} {APP_VERSION}",
        f"type: {'compare' if compare_mode else 'merged'}",
        f"sources: {len(results)}",
        f"converted_at: {now}",
        "---",
        f"# {title}\n",
    ]
    labels = None
    if compare_mode and len(results) == 2:
        labels = ["Documento A", "Documento B"]
        parts.append(
            "> Confronto affiancato (stesso pipeline Mr. Rao su entrambi i file).\n"
        )
    for i, r in enumerate(results, 1):
        if labels:
            heading = f"## {labels[i - 1]} — `{r.source_name}`\n"
        else:
            heading = f"## {i}. {r.source_name}\n"
        parts.append(f"\n---\n\n{heading}")
        if r.error:
            parts.append(f"> Errore: {r.error}\n")
        else:
            parts.append(strip_frontmatter(r.markdown))
    return "\n".join(parts)
