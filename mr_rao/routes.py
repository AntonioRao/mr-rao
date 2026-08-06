"""Flask routes for Mr. Rao web API."""
from __future__ import annotations

import threading
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request

from config import (
    ALLOWED_EXTENSIONS,
    APP_NAME,
    APP_VERSION,
    IMAGE_EXTENSIONS,
    MAX_UPLOAD_MB,
    MAX_WORKERS,
)
from mr_rao.converter import ConvertOptions, ConvertResult, convert_bytes, merge_markdowns
from mr_rao.jobs import job_store
from mr_rao.privacy import options_from_form
from mr_rao.profiles import get_profile, list_profiles, options_from_profile
from mr_rao.user_folders import browse_folder, ensure_default_watch_folders
from mr_rao.watch_service import get_watch_state, start_watch, stop_watch

bp = Blueprint("main", __name__)

# One thread per request would let N uploads start N OCR runs at once and
# thrash the machine. Threads stay daemon (clean exit from the tray); the
# semaphore is what bounds the actual work. Queued jobs stay "pending".
_worker_slots = threading.BoundedSemaphore(MAX_WORKERS)


def _spawn(target, *args) -> None:
    def _runner():
        with _worker_slots:
            target(*args)

    threading.Thread(target=_runner, daemon=True).start()


def _truthy(val, default: bool = False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes", "on")


def _parse_options_from_request() -> ConvertOptions:
    form = request.form
    profile_id = form.get("profile") or form.get("preset")
    if profile_id:
        opts = options_from_profile(profile_id)
        if opts:
            # Allow form overrides on top of profile for a few keys
            if form.get("engine"):
                eng = form.get("engine")
                if eng == "paddleocr":
                    eng = "rapidocr"
                opts.engine = eng
            if form.get("language"):
                opts.language = form.get("language", opts.language)
            return opts

    engine = form.get("engine", "auto")
    if engine == "paddleocr":
        engine = "rapidocr"
    privacy = options_from_form(form)
    return ConvertOptions(
        engine=engine,
        language=form.get("language", "it"),
        privacy=privacy,
        include_tables=_truthy(form.get("include_tables"), True),
        include_frontmatter=_truthy(form.get("include_frontmatter"), True),
        clean_output=_truthy(form.get("clean_output"), False),
        force_ocr_pdf=_truthy(form.get("force_ocr_pdf"), False),
        include_raw=_truthy(form.get("include_raw"), True),
        extract_attachments=_truthy(form.get("extract_attachments"), True),
    )


def _result_payload(result: ConvertResult) -> dict:
    payload = {
        "markdown": result.markdown,
        "engine": result.engine_used,
        "filename": result.source_name,
        "empty": result.empty,
        "redaction": result.redaction.to_dict(),
    }
    if result.markdown_raw is not None:
        payload["markdown_raw"] = result.markdown_raw
    if result.attachments:
        # strip huge base64 from list preview? keep full for download
        payload["attachments"] = result.attachments
    return payload


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
        # The client-side size check must follow MR_RAO_MAX_UPLOAD_MB, not a
        # hardcoded 50, or raising the server limit changes nothing.
        max_upload_mb=MAX_UPLOAD_MB,
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
            "max_upload_mb": MAX_UPLOAD_MB,
            "max_workers": MAX_WORKERS,
            "profiles": list_profiles(),
            "watch": get_watch_state(),
            "frozen": bool(getattr(__import__("sys"), "frozen", False)),
        }
    )


@bp.route("/api/profiles")
def profiles():
    return jsonify({"profiles": list_profiles(), "detail": {p: get_profile(p) for p in [x["id"] for x in list_profiles()]}})


def _fail_job(job, exc: Exception) -> None:
    """Never leave a job in 'running': the UI would poll it forever."""
    print(f"job {job.id} crashed: {exc!r}")
    with job.lock:
        if job.status in ("done", "cancelled"):
            return
        job.status = "error"
        job.error = "Errore interno durante la conversione."
        job.message = job.error


def _run_job_single(job_id: str, data: bytes, filename: str, options: ConvertOptions) -> None:
    job = job_store.get(job_id)
    if not job:
        return
    try:
        _run_job_single_inner(job, data, filename, options)
    except Exception as e:  # noqa: BLE001 — last line of defence for the worker thread
        _fail_job(job, e)


def _run_job_single_inner(job, data: bytes, filename: str, options: ConvertOptions) -> None:
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
            job.result = _result_payload(result)


def _run_job_batch(
    job_id: str,
    items: list[tuple[bytes, str]],
    options: ConvertOptions,
    merge: bool,
    merge_title: str,
    compare: bool = False,
) -> None:
    job = job_store.get(job_id)
    if not job:
        return
    try:
        _run_job_batch_inner(job, items, options, merge, merge_title, compare)
    except Exception as e:  # noqa: BLE001 — last line of defence for the worker thread
        _fail_job(job, e)


def _run_job_batch_inner(
    job,
    items: list[tuple[bytes, str]],
    options: ConvertOptions,
    merge: bool,
    merge_title: str,
    compare: bool = False,
) -> None:
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

    if merge or compare:
        title = merge_title if not compare else (merge_title or "Confronto documenti")
        merged = merge_markdowns(results, title=title, compare_mode=compare)
        redaction_total = sum(r.redaction.total for r in results)
        with job.lock:
            job.status = "done"
            job.progress = len(items)
            job.message = "Confronto completato" if compare else "Merge completato"
            job.result = {
                "markdown": merged,
                "engine": "compare" if compare else "merge",
                "filename": (title if title.endswith(".md") else title + ".md"),
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
                    {**_result_payload(r), "error": r.error}
                    for r in results
                ],
            }


@bp.route("/api/convert", methods=["POST"])
def convert_api():
    if "file" not in request.files:
        return jsonify({"error": "Nessun file trovato nella richiesta"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nessun file selezionato"}), 400

    _, err = _validate_filename(file.filename)
    if err:
        return jsonify({"error": err}), 400

    # No .eml special case here: the privacy default is decided once in
    # options_from_form(), which is fail-safe (redacts unless told otherwise).
    options = _parse_options_from_request()

    data = file.read()
    if not data:
        return jsonify({"error": "File vuoto"}), 400
    if len(data) > current_app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"error": "File troppo grande"}), 400

    job = job_store.create()
    with job.lock:
        job.message = "In coda…"
    _spawn(_run_job_single, job.id, data, file.filename, options)
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/batch", methods=["POST"])
def convert_batch():
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files:
        return jsonify({"error": "Nessun file nella richiesta"}), 400

    options = _parse_options_from_request()
    merge = _truthy(request.form.get("merge"), False)
    compare = _truthy(request.form.get("compare"), False)
    merge_title = request.form.get("merge_title", "Documento unificato")
    if compare:
        merge = True
        if merge_title == "Documento unificato":
            merge_title = "Confronto documenti"

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
    if compare and len(items) != 2:
        return jsonify({"error": "Il confronto richiede esattamente 2 file"}), 400

    job = job_store.create()
    with job.lock:
        job.message = "In coda…"
    _spawn(_run_job_batch, job.id, items, options, merge, merge_title, compare)
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/compare", methods=["POST"])
def convert_compare():
    """Compare exactly two documents. Convenience alias of /api/convert/batch
    with compare=1, accepting file_a/file_b instead of a files[] list."""
    files = request.files.getlist("files")
    if len(files) < 2:
        a = request.files.get("file_a") or request.files.get("file1")
        b = request.files.get("file_b") or request.files.get("file2")
        files = [f for f in (a, b) if f]
    if len(files) != 2:
        return jsonify({"error": "Servono esattamente 2 file (file_a e file_b)"}), 400

    options = _parse_options_from_request()
    items: list[tuple[bytes, str]] = []
    for f in files:
        if not f.filename:
            return jsonify({"error": "Nome file mancante"}), 400
        _, err = _validate_filename(f.filename)
        if err:
            return jsonify({"error": err}), 400
        data = f.read()
        if not data:
            return jsonify({"error": f"File vuoto: {f.filename}"}), 400
        items.append((data, f.filename))

    job = job_store.create()
    with job.lock:
        job.message = "In coda…"
    _spawn(
        _run_job_batch,
        job.id,
        items,
        options,
        True,
        request.form.get("merge_title", "Confronto documenti"),
        True,
    )
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/sync", methods=["POST"])
def convert_sync():
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
    return jsonify(_result_payload(result))


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
    return convert_api()


@bp.route("/api/folders/defaults", methods=["GET"])
def folders_defaults():
    """Create (if needed) and return Documenti\\Mr Rao\\Da convertire + Convertiti."""
    paths = ensure_default_watch_folders()
    return jsonify({"ok": True, **paths})


@bp.route("/api/folders/browse", methods=["POST"])
def folders_browse():
    """Native OS folder picker (local app only). Body: { initial?, title? }."""
    data = request.get_json(silent=True) or {}
    initial = data.get("initial") or request.form.get("initial")
    title = data.get("title") or request.form.get("title") or "Scegli cartella"
    path = browse_folder(initial=initial, title=title)
    if not path:
        return jsonify({"ok": False, "cancelled": True, "path": None})
    return jsonify({"ok": True, "cancelled": False, "path": path})


@bp.route("/api/watch", methods=["GET"])
def watch_get():
    defaults = ensure_default_watch_folders()
    state = get_watch_state()
    state["defaults"] = defaults
    return jsonify(state)


@bp.route("/api/watch", methods=["POST"])
def watch_start():
    data = request.get_json(silent=True) or {}
    # also accept form
    defaults = ensure_default_watch_folders()
    inbox = data.get("inbox") or request.form.get("inbox") or defaults["inbox"]
    outbox = data.get("outbox") or request.form.get("outbox") or defaults["outbox"]
    if not inbox or not outbox:
        return jsonify({"error": "Specificare inbox e outbox"}), 400
    interval = float(data.get("interval") or request.form.get("interval") or 2)
    move_done = _truthy(data.get("move_done") or request.form.get("move_done"), False)
    # options from form/json profile
    if request.form:
        options = _parse_options_from_request()
    else:
        profile = data.get("profile")
        options = options_from_profile(profile) if profile else ConvertOptions()
        if options is None:
            options = ConvertOptions()
    state = start_watch(inbox, outbox, options=options, interval=interval, move_done=move_done)
    return jsonify(state)


@bp.route("/api/watch", methods=["DELETE"])
def watch_stop():
    return jsonify(stop_watch())
