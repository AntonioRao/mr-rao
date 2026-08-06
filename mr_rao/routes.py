"""Flask routes for Mr. Rao web API."""
from __future__ import annotations

import threading
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request

from config import ALLOWED_EXTENSIONS, APP_NAME, APP_VERSION, IMAGE_EXTENSIONS
from mr_rao.converter import ConvertOptions, convert_bytes, merge_markdowns
from mr_rao.jobs import job_store
from mr_rao.privacy import options_from_form

bp = Blueprint("main", __name__)


def _parse_options_from_request() -> ConvertOptions:
    form = request.form
    engine = form.get("engine", "auto")
    if engine == "paddleocr":
        engine = "rapidocr"
    privacy = options_from_form(form)
    # EML always gets privacy defaults if master not set — handled in converter
    return ConvertOptions(
        engine=engine,
        language=form.get("language", "it"),
        privacy=privacy,
        include_tables=str(form.get("include_tables", "true")).lower() in ("1", "true", "yes", "on"),
        include_frontmatter=str(form.get("include_frontmatter", "true")).lower()
        in ("1", "true", "yes", "on"),
        clean_output=str(form.get("clean_output", "false")).lower() in ("1", "true", "yes", "on"),
        force_ocr_pdf=str(form.get("force_ocr_pdf", "false")).lower() in ("1", "true", "yes", "on"),
    )


def _validate_filename(filename: str) -> tuple[str | None, str | None]:
    if not filename:
        return None, "Nessun file selezionato"
    original_ext = Path(filename).suffix.lower() if "." in filename else ""
    if original_ext not in ALLOWED_EXTENSIONS:
        return None, (
            f'Tipo di file "{original_ext}" non supportato. '
            "Formati: PDF, DOCX, XLSX, PPTX, HTML, CSV, TXT, EML e immagini."
        )
    return original_ext, None


@bp.route("/")
def index():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        app_version=APP_VERSION,
    )


@bp.route("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "app": APP_NAME,
            "version": APP_VERSION,
            "engines": ["markitdown", "rapidocr", "eml_parser"],
            "image_extensions": sorted(IMAGE_EXTENSIONS),
            "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        }
    )


def _run_job_single(job_id: str, data: bytes, filename: str, options: ConvertOptions) -> None:
    job = job_store.get(job_id)
    if not job:
        return
    with job.lock:
        job.status = "running"
        job.message = "Avvio conversione…"

    def progress(c, t, msg):
        job.set_progress(c, t, msg)

    result = convert_bytes(
        data,
        filename,
        options=options,
        progress=progress,
        should_cancel=job.should_cancel,
    )
    with job.lock:
        if job.cancel_flag:
            job.status = "cancelled"
            job.message = "Annullato"
            return
        if result.error:
            job.status = "error"
            job.error = result.error
            job.message = result.error
        else:
            job.status = "done"
            job.message = "Completato"
            job.progress = job.total
            job.result = {
                "markdown": result.markdown,
                "engine": result.engine_used,
                "filename": result.source_name,
                "empty": result.empty,
                "redaction": result.redaction.to_dict(),
            }


def _run_job_batch(
    job_id: str,
    items: list[tuple[bytes, str]],
    options: ConvertOptions,
    merge: bool,
    merge_title: str,
) -> None:
    job = job_store.get(job_id)
    if not job:
        return
    with job.lock:
        job.status = "running"
        job.total = len(items)
        job.message = "Batch in corso…"

    results = []
    for i, (data, filename) in enumerate(items):
        if job.should_cancel():
            with job.lock:
                job.status = "cancelled"
                job.message = "Annullato"
            return
        job.set_progress(i, len(items), f"File {i + 1}/{len(items)}: {filename}")

        def progress(c, t, msg, _i=i, _n=len(items), _f=filename):
            # Map inner progress into batch slot
            job.set_progress(_i, _n, f"{_f}: {msg}")

        r = convert_bytes(
            data,
            filename,
            options=options,
            progress=progress,
            should_cancel=job.should_cancel,
        )
        results.append(r)

    if job.should_cancel():
        with job.lock:
            job.status = "cancelled"
            job.message = "Annullato"
        return

    if merge:
        merged = merge_markdowns(results, title=merge_title)
        redaction_total = sum(r.redaction.total for r in results)
        with job.lock:
            job.status = "done"
            job.progress = len(items)
            job.message = "Merge completato"
            job.result = {
                "markdown": merged,
                "engine": "merge",
                "filename": merge_title + ".md",
                "empty": False,
                "redaction": {"total": redaction_total, "counts": {}},
                "files": [
                    {
                        "filename": r.source_name,
                        "engine": r.engine_used,
                        "error": r.error,
                        "redaction": r.redaction.to_dict(),
                    }
                    for r in results
                ],
            }
    else:
        with job.lock:
            job.status = "done"
            job.progress = len(items)
            job.message = "Batch completato"
            job.result = {
                "batch": True,
                "items": [
                    {
                        "markdown": r.markdown,
                        "engine": r.engine_used,
                        "filename": r.source_name,
                        "empty": r.empty,
                        "error": r.error,
                        "redaction": r.redaction.to_dict(),
                    }
                    for r in results
                ],
            }


@bp.route("/api/convert", methods=["POST"])
def convert_api():
    """Start async conversion job (single file). Returns job_id."""
    if "file" not in request.files:
        return jsonify({"error": "Nessun file trovato nella richiesta"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nessun file selezionato"}), 400

    _, err = _validate_filename(file.filename)
    if err:
        return jsonify({"error": err}), 400

    options = _parse_options_from_request()
    # Auto-enable privacy for EML if master off — converter handles defaults when empty;
    # for EML force privacy master on for safety unless explicitly all off with privacy_filter=false
    # and privacy_eml_override
    if Path(file.filename).suffix.lower() == ".eml":
        if request.form.get("privacy_filter", "true").lower() != "false":
            from mr_rao.privacy import PrivacyOptions

            if not any(
                [
                    options.privacy.emails,
                    options.privacy.phones,
                    options.privacy.names,
                    options.privacy.fiscal,
                ]
            ):
                options.privacy = PrivacyOptions()

    data = file.read()
    if not data:
        return jsonify({"error": "File vuoto"}), 400
    if len(data) > current_app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"error": "File troppo grande"}), 400

    job = job_store.create()
    t = threading.Thread(
        target=_run_job_single,
        args=(job.id, data, file.filename, options),
        daemon=True,
    )
    t.start()
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/batch", methods=["POST"])
def convert_batch():
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files:
        return jsonify({"error": "Nessun file nella richiesta"}), 400

    options = _parse_options_from_request()
    merge = str(request.form.get("merge", "false")).lower() in ("1", "true", "yes", "on")
    merge_title = request.form.get("merge_title", "Documento unificato")

    items: list[tuple[bytes, str]] = []
    for f in files:
        if not f or not f.filename:
            continue
        _, err = _validate_filename(f.filename)
        if err:
            return jsonify({"error": f"{f.filename}: {err}"}), 400
        data = f.read()
        if data:
            items.append((data, f.filename))

    if not items:
        return jsonify({"error": "Nessun file valido"}), 400

    job = job_store.create()
    t = threading.Thread(
        target=_run_job_batch,
        args=(job.id, items, options, merge, merge_title),
        daemon=True,
    )
    t.start()
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/sync", methods=["POST"])
def convert_sync():
    """Synchronous convert (CLI-friendly / simple clients)."""
    if "file" not in request.files:
        return jsonify({"error": "Nessun file trovato nella richiesta"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Nessun file selezionato"}), 400
    _, err = _validate_filename(file.filename)
    if err:
        return jsonify({"error": err}), 400

    options = _parse_options_from_request()
    data = file.read()
    result = convert_bytes(data, file.filename, options=options)
    if result.error:
        return jsonify({"error": result.error}), 500
    return jsonify(
        {
            "markdown": result.markdown,
            "engine": result.engine_used,
            "filename": result.source_name,
            "empty": result.empty,
            "redaction": result.redaction.to_dict(),
        }
    )


@bp.route("/api/jobs/<job_id>", methods=["GET"])
def job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        return jsonify({"error": "Job non trovato"}), 404
    return jsonify(job.to_public())


@bp.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def job_cancel(job_id: str):
    if not job_store.cancel(job_id):
        return jsonify({"error": "Job non trovato"}), 404
    return jsonify({"ok": True, "id": job_id})


@bp.route("/api/paste-image", methods=["POST"])
def paste_image():
    """Accept clipboard image as multipart file named file."""
    return convert_api()
