"""OCR helpers: RapidOCR images + PDF page fallback + table extraction."""
from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Callable

from config import MAX_OCR_PAGES, OCR_DPI

# Lazy singleton. The lock matters: two concurrent requests would otherwise
# each build a RapidOCR instance (hundreds of MB of ONNX models).
_ocr = None
_ocr_lock = threading.Lock()


def get_ocr():
    global _ocr
    if _ocr is None:
        with _ocr_lock:
            if _ocr is None:
                from rapidocr_onnxruntime import RapidOCR

                _ocr = RapidOCR()
    return _ocr


ProgressCb = Callable[[int, int, str], None]  # current, total, message
CancelCb = Callable[[], bool]


def ocr_image(filepath: str | Path, language: str = "it") -> str | None:
    """Run RapidOCR on an image path. language is advisory (Latin scripts)."""
    ocr = get_ocr()
    result, _ = ocr(str(filepath))
    if not result:
        return None
    lines = [item[1] for item in result]
    # language reserved for future model selection / post-processing
    _ = language
    return "\n\n".join(lines) if lines else None


def extract_pdf_tables(filepath: str | Path) -> str:
    """Extract tables from PDF via pdfplumber → Markdown tables."""
    try:
        import pdfplumber
    except ImportError:
        return ""

    chunks: list[str] = []
    with pdfplumber.open(str(filepath)) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables() or []
            for t_idx, table in enumerate(tables):
                if not table or not any(table):
                    continue
                md = _table_to_markdown(table)
                if md:
                    chunks.append(f"### Tabella (pagina {i + 1}" + (f", #{t_idx + 1}" if t_idx else "") + ")\n\n" + md)
    return "\n\n".join(chunks)


def _table_to_markdown(table: list[list]) -> str:
    # Normalize rows
    rows = []
    for row in table:
        cells = [("" if c is None else str(c).replace("\n", " ").strip()) for c in row]
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    # If first row looks like data, synthesize header
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def ocr_pdf_fallback(
    filepath: str | Path,
    language: str = "it",
    progress: ProgressCb | None = None,
    should_cancel: CancelCb | None = None,
    max_pages: int | None = None,
    include_tables: bool = True,
) -> str | None:
    """Rasterize PDF pages and OCR each. Optionally prepend extracted tables."""
    try:
        import pdfplumber
    except ImportError as e:
        print(f"OCR PDF fallback: pdfplumber missing: {e}")
        return None

    max_pages = max_pages if max_pages is not None else MAX_OCR_PAGES

    all_text: list[str] = []
    tables_md = extract_pdf_tables(filepath) if include_tables else ""

    try:
        # Page rasters are intermediate data of a "100% local, minimal disk
        # dwell" pipeline: they belong in the OS temp dir, not next to the exe
        # (uploads/ may be read-only, and leftovers survive a crash).
        with tempfile.TemporaryDirectory(prefix="mrrao_ocr_") as tmpdir:
            tmp = Path(tmpdir)
            with pdfplumber.open(str(filepath)) as pdf:
                total = min(len(pdf.pages), max_pages)
                if len(pdf.pages) > max_pages and progress:
                    progress(0, total, f"Limite {max_pages} pagine OCR (PDF ne ha {len(pdf.pages)})")

                for i, page in enumerate(pdf.pages[:max_pages]):
                    if should_cancel and should_cancel():
                        return None
                    if progress:
                        progress(i + 1, total, f"OCR pagina {i + 1}/{total}…")

                    temp_img_path = tmp / f"page_{i}.png"
                    try:
                        page.to_image(resolution=OCR_DPI).original.save(
                            temp_img_path, format="PNG"
                        )
                        page_text = ocr_image(temp_img_path, language=language)
                        if page_text:
                            all_text.append(f"<!-- Pagina {i + 1} -->\n\n{page_text}")
                    except Exception as page_err:
                        print(f"OCR page {i + 1} error: {page_err}")
                        continue
                    finally:
                        temp_img_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"OCR PDF fallback error: {e}")
        return None

    if not all_text and not tables_md:
        return None

    header = (
        "> ℹ️ *Testo estratto tramite OCR (PDF scansionato o con poco testo nativo).*\n\n---\n\n"
    )
    parts: list[str] = []
    if tables_md:
        parts.append("## Tabelle estratte\n\n" + tables_md)
    if all_text:
        parts.append("## Testo OCR\n\n" + "\n\n---\n\n".join(all_text))
    return header + "\n\n---\n\n".join(parts)
