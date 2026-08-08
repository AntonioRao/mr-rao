"""OCR helpers: RapidOCR images + PDF page fallback + table extraction."""
from __future__ import annotations

import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

from config import MAX_OCR_PAGES, MAX_OCR_SECONDS, OCR_DPI
from mr_rao.i18n import LINGUA_PREDEFINITA, t

# Lazy singleton. The lock matters: two concurrent requests would otherwise
# each build a RapidOCR instance (hundreds of MB of ONNX models).
_ocr = None
_ocr_lock = threading.Lock()


def get_ocr():
    global _ocr
    if _ocr is None:
        with _ocr_lock:
            if _ocr is None:
                # `rapidocr`, non piu' `rapidocr_onnxruntime`: il pacchetto e'
                # stato rinominato e il vecchio nome e' fermo alla 1.2.3, senza
                # piu' correzioni nemmeno di sicurezza.
                from rapidocr import RapidOCR

                # La 3.x scrive nove righe di INFO al primo uso, e fra queste
                # il percorso completo dei modelli -- che su Windows contiene
                # il nome dell'utente. Su uno strumento che esiste per non far
                # uscire i dati, un output di console incollato in una
                # segnalazione non deve dire chi sei.
                #
                # Le righe escono *durante* la costruzione, e RapidOCR si
                # riconfigura il logger mentre nasce: alzarne il livello prima
                # non serve (lo sovrascrive) e dopo e' tardi. Si spengono per
                # la sola durata dell'inizializzazione, poi si rimette tutto
                # com'era -- il `finally` c'e' perche' una disabilitazione
                # globale lasciata accesa sarebbe molto peggio del rumore.
                _zittisci_log_ocr()
                logging.disable(logging.INFO)
                try:
                    _ocr = RapidOCR()
                finally:
                    logging.disable(logging.NOTSET)
    return _ocr


def _zittisci_log_ocr() -> None:
    """Abbassa i log di RapidOCR a WARNING, senza toccare quelli di nessun altro."""
    for nome in ("RapidOCR", "rapidocr"):
        logging.getLogger(nome).setLevel(logging.WARNING)


ProgressCb = Callable[[int, int, str], None]  # current, total, message
CancelCb = Callable[[], bool]


def ocr_image(filepath: str | Path, language: str = "it") -> str | None:
    """Run RapidOCR on an image path. language is advisory (Latin scripts).

    Il risultato non e' piu' la tupla ``(result, elapse)`` della 1.2.3: la 3.x
    restituisce un ``RapidOCROutput`` con ``.txts``, ``.boxes``, ``.scores``.
    Il vecchio ``result, _ = ocr(path)`` qui alzava ``TypeError``, e il vecchio
    ``item[1]`` non esiste piu'.
    """
    ocr = get_ocr()
    out = ocr(str(filepath))
    # `.txts` e' None quando non trova niente, non una sequenza vuota.
    lines = list(getattr(out, "txts", None) or ())
    # language reserved for future model selection / post-processing
    _ = language
    return "\n\n".join(lines) if lines else None


def extract_pdf_tables(
    filepath: str | Path, lingua: str = LINGUA_PREDEFINITA
) -> str:
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
                    intestazione = (
                        t("doc_tabella_pagina_indice", lingua, n=i + 1, k=t_idx + 1)
                        if t_idx
                        else t("doc_tabella_pagina", lingua, n=i + 1)
                    )
                    chunks.append(f"### {intestazione}\n\n" + md)
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
    max_seconds: float | None = None,
    lingua: str = LINGUA_PREDEFINITA,
) -> str | None:
    """Rasterize PDF pages and OCR each. Optionally prepend extracted tables.

    ``max_seconds`` limita il tempo complessivo (0 o None → il valore di
    configurazione; 0 in configurazione → nessun limite). Il controllo sta
    accanto a quello di annullamento, cioè **fra una pagina e l'altra**: è
    l'unico punto interrompibile, perché un thread Python non si uccide da
    fuori. Allo scadere si restituisce ciò che si è letto finora, dicendolo
    nel testo — un risultato troncato in silenzio sarebbe peggio di nessuno.
    """
    try:
        import pdfplumber
    except ImportError as e:
        print(f"OCR PDF fallback: pdfplumber missing: {e}")
        return None

    max_pages = max_pages if max_pages is not None else MAX_OCR_PAGES
    limite = MAX_OCR_SECONDS if max_seconds is None else max_seconds
    scadenza = (time.monotonic() + limite) if limite and limite > 0 else None
    # None = mai scaduto. Un contatore da solo non basterebbe: se il tempo
    # finisce prima della prima pagina il conteggio è 0, che è indistinguibile
    # da "tutto bene" — e l'avviso non comparirebbe proprio nel caso peggiore.
    interrotto_per_tempo: int | None = None

    all_text: list[str] = []
    total = 0
    tables_md = extract_pdf_tables(filepath, lingua) if include_tables else ""

    try:
        # Page rasters are intermediate data of a "100% local, minimal disk
        # dwell" pipeline: they belong in the OS temp dir, not next to the exe
        # (uploads/ may be read-only, and leftovers survive a crash).
        with tempfile.TemporaryDirectory(prefix="mrrao_ocr_") as tmpdir:
            tmp = Path(tmpdir)
            with pdfplumber.open(str(filepath)) as pdf:
                total = min(len(pdf.pages), max_pages)
                if len(pdf.pages) > max_pages and progress:
                    progress(
                        0,
                        total,
                        t(
                            "prog_ocr_limite_pagine",
                            lingua,
                            max=max_pages,
                            totale=len(pdf.pages),
                        ),
                    )

                for i, page in enumerate(pdf.pages[:max_pages]):
                    if should_cancel and should_cancel():
                        return None
                    if scadenza is not None and time.monotonic() > scadenza:
                        interrotto_per_tempo = i
                        if progress:
                            progress(
                                i,
                                total,
                                t("prog_ocr_limite_tempo", lingua, n=i, tot=total),
                            )
                        break
                    if progress:
                        progress(
                            i + 1,
                            total,
                            t("prog_ocr_pagina", lingua, n=i + 1, tot=total),
                        )

                    temp_img_path = tmp / f"page_{i}.png"
                    try:
                        page.to_image(resolution=OCR_DPI).original.save(
                            temp_img_path, format="PNG"
                        )
                        page_text = ocr_image(temp_img_path, language=language)
                        if page_text:
                            etichetta = t("doc_pagina", lingua, n=i + 1)
                            all_text.append(f"<!-- {etichetta} -->\n\n{page_text}")
                    except Exception as page_err:
                        print(f"OCR page {i + 1} error: {page_err}")
                        continue
                    finally:
                        temp_img_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"OCR PDF fallback error: {e}")
        return None

    if not all_text and not tables_md and interrotto_per_tempo is None:
        return None
    # Scaduto senza aver letto niente si restituisce comunque l'avviso: il
    # messaggio "nessun testo riconoscibile" manderebbe a cercare il problema
    # nel documento, che invece era solo lento.

    # La forma `> ℹ️ *…*` la riconosce `_RE_NOTA_PRIVACY` (converter.py) e la
    # sua gemella in app.js: emoji e `> ` iniziale restano fuori dalla
    # traduzione proprio perche' sono la chiave con cui le note si tolgono.
    header = f"> ℹ️ *{t('doc_ocr_avviso', lingua)}*\n\n---\n\n"
    if interrotto_per_tempo is not None:
        # In cima, non in fondo: chi legge un documento troncato deve saperlo
        # prima di fidarsi di quello che c'è scritto — e prima di credere che
        # l'anonimizzazione dei dati personali abbia visto tutto il documento.
        titolo = t(
            "doc_ocr_troncato_titolo", lingua, n=interrotto_per_tempo, tot=total
        )
        header = (
            f"> ⚠️ **{titolo}**\n"
            f"> {t('doc_ocr_troncato_corpo', lingua)}\n\n"
        ) + header
    parts: list[str] = []
    if tables_md:
        parts.append(f"## {t('doc_tabelle_estratte', lingua)}\n\n" + tables_md)
    if all_text:
        parts.append(
            f"## {t('doc_testo_ocr', lingua)}\n\n" + "\n\n---\n\n".join(all_text)
        )
    return header + "\n\n---\n\n".join(parts)
