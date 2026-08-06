"""Core conversion pipeline: documents, images, EML → Markdown + frontmatter."""
from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from config import APP_NAME, APP_VERSION, IMAGE_EXTENSIONS
from mr_rao.ocr_service import extract_pdf_tables, ocr_image, ocr_pdf_fallback
from mr_rao.privacy import PrivacyOptions, RedactionReport, apply_privacy_filter

ProgressCb = Callable[[int, int, str], None]
CancelCb = Callable[[], bool]

_md = None


def get_markitdown():
    global _md
    if _md is None:
        from markitdown import MarkItDown

        _md = MarkItDown()
    return _md


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


def _empty_message() -> str:
    return (
        "> ⚠️ **Nessun testo estratto.**\n>\n"
        "> Il file caricato non contiene testo riconoscibile.\n>\n"
        "> **Suggerimenti:**\n"
        "> - Se è un'immagine, assicurati che il testo sia leggibile.\n"
        "> - Se è un PDF, prova **Forza RapidOCR** o abilita le tabelle.\n"
        "> - Se è protetto da password, rimuovi la protezione prima."
    )


def _strip_noise(text: str) -> str:
    """Clean copy for LLM paste: drop HTML comments and trailing privacy notes."""
    import re

    text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.DOTALL)
    text = re.sub(r"\n?> 🛡️ \*.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?> ℹ️ \*.*$", "", text, flags=re.MULTILINE)
    return text.strip()


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
        f"generator: {APP_NAME} {APP_VERSION}",
        f"source: {source_name}",
        f"format: {source_ext.lstrip('.')}",
        f"engine: {engine_used}",
        f"converted_at: {now}",
        f"source_hash: {file_hash}",
    ]
    if redaction.total:
        lines.append(f"redactions: {redaction.total}")
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
    opts = options or ConvertOptions()
    path = Path(filepath)
    original_name = original_name or path.name
    ext = path.suffix.lower()
    if not ext and original_name and "." in original_name:
        ext = "." + original_name.rsplit(".", 1)[-1].lower()

    engine_used = "none"
    final_text: str | None = None
    file_hash = _file_sha256(path) if path.exists() else "unknown"
    attachments: list[dict] = []

    try:
        if should_cancel and should_cancel():
            return ConvertResult(
                markdown="",
                engine_used="cancelled",
                source_name=original_name,
                source_ext=ext,
                error="Conversione annullata",
            )

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
            # EML always applies privacy if any privacy flag is on; default on for emails
            if not any(
                [
                    opts.privacy.emails,
                    opts.privacy.phones,
                    opts.privacy.names,
                    opts.privacy.fiscal,
                    opts.privacy.amounts,
                    opts.privacy.use_scrubadub,
                ]
            ):
                # Force sensible defaults for EML if master was off but it's email
                opts.privacy = PrivacyOptions()

        elif opts.engine == "rapidocr" or (
            opts.engine == "auto" and ext in IMAGE_EXTENSIONS
        ):
            if progress:
                progress(1, 1, "OCR immagine…")
            final_text = ocr_image(path, language=opts.language)
            engine_used = "rapidocr"

        elif opts.engine == "rapidocr" and ext == ".pdf":
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

            tables_extra = ""
            if ext == ".pdf" and opts.include_tables:
                try:
                    tables_extra = extract_pdf_tables(path)
                except Exception as e:
                    print(f"Table extract error: {e}")

            needs_ocr = ext == ".pdf" and (
                opts.force_ocr_pdf
                or opts.engine == "rapidocr"
                or not final_text
                or not str(final_text).strip()
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

        redaction = RedactionReport()
        markdown_raw: str | None = None
        privacy_on = bool(
            final_text
            and (
                opts.privacy.emails
                or opts.privacy.phones
                or opts.privacy.names
                or opts.privacy.fiscal
                or opts.privacy.amounts
                or opts.privacy.use_scrubadub
            )
        )
        if privacy_on and final_text:
            if opts.include_raw:
                markdown_raw = final_text
            final_text, redaction = apply_privacy_filter(final_text, opts.privacy)

        empty = not final_text or not str(final_text).strip()
        if empty:
            final_text = _empty_message()
            empty = True

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
            body = r.markdown
            if body.startswith("---"):
                end = body.find("\n---", 3)
                if end != -1:
                    body = body[end + 4 :].lstrip("\n")
            parts.append(body)
    return "\n".join(parts)


def unique_upload_path(upload_dir: Path, original_filename: str) -> tuple[Path, str]:
    """Return (path, safe_original_basename) with UUID prefix to avoid collisions."""
    from werkzeug.utils import secure_filename

    original_ext = Path(original_filename).suffix.lower() if "." in original_filename else ""
    safe = secure_filename(original_filename)
    if not safe:
        safe = f"file{original_ext}"
    name = f"{uuid.uuid4().hex[:12]}_{safe}"
    return upload_dir / name, Path(original_filename).name
