"""Flask routes for Mr. Rao web API."""
from __future__ import annotations

import io
import re
import threading
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
    send_file,
)

from config import (
    ALLOWED_EXTENSIONS,
    APP_NAME,
    APP_VERSION,
    IMAGE_EXTENSIONS,
    MAX_UPLOAD_MB,
    MAX_WORKERS,
)
from mr_rao.converter import ConvertOptions, ConvertResult, convert_bytes, merge_markdowns
from mr_rao.docx_export import docx_disponibile, markdown_to_docx
from mr_rao.i18n import LINGUA_PREDEFINITA, LINGUE, lingua_da, t
from mr_rao.jobs import job_store
from mr_rao.privacy import (
    CATEGORIE,
    FIELD_DEFAULTS,
    PrivacyOptions,
    _pacchetti_da,
    segnala_da_form,
    no_redaction,
    options_from_form,
    prosa_da,
    termini_da,
)
from mr_rao.profiles import (
    PROFILES,
    get_profile,
    list_profiles,
    options_from_profile,
    privacy_flags,
)
from mr_rao.user_folders import (
    browse_folder,
    describe_default_folders,
    ensure_default_watch_folders,
)
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


def _merge_privacy(form, profile: dict) -> PrivacyOptions:
    """Flag privacy del profilo, con sopra quelli presenti nel modulo.

    Un campo assente resta quello del profilo: un client che manda solo
    ``profile`` continua ad avere esattamente il preset. Un campo presente
    vince sempre, perche' e' una scelta esplicita di chi sta convertendo.
    """
    if "privacy_filter" in form:
        master = _truthy(form.get("privacy_filter"), True)
    else:
        master = bool(profile.get("privacy_filter"))
    if not master:
        return no_redaction()

    # Se il profilo aveva la redazione spenta non ci sono flag da cui
    # partire: la base tornano a essere i valori predefiniti del motore.
    base = privacy_flags(profile) if profile.get("privacy_filter") else dict(FIELD_DEFAULTS)
    return PrivacyOptions(
        # **I pacchetti e lo stile si leggono qui, e per mesi non e' stato
        # cosi'.** Non stanno nei profili — un profilo dice *come* convertire,
        # i pacchetti dicono *di quale Paese* sono i dati e lo stile dice se e'
        # una lettera o un modulo — ma questo e' il ramo che l'interfaccia
        # percorre **sempre**, perche' manda sempre un profilo.
        #
        # Dimenticandoli qui, le caselle erano decorative: si spegneva il
        # pacchetto inglese e l'SSN spariva lo stesso, si accendeva «Atti e
        # pratiche» e il numero di protocollo restava in chiaro. Provato da
        # un audit esterno e riprodotto: e' esattamente il difetto per cui
        # esiste `tests/test_gui_parity.py`, che pero' non guardava questi due.
        pacchetti=_pacchetti_da(
            lambda chiave, predefinito: (
                _truthy(form.get(chiave), predefinito)
                if chiave in form else predefinito
            )
        ),
        prosa=prosa_da(form.get("privacy_stile")),
        # Le due liste dello studio non stanno nei profili: sono di chi
        # converte, non del preset. Vanno pero' lette **qui**, perche'
        # l'interfaccia manda sempre un profilo e questo e' il ramo che
        # percorre — dimenticarle qui le renderebbe decorative come lo era
        # l'intero pannello prima del test di parita'.
        sempre=termini_da(form.get("privacy_sempre")),
        mai=termini_da(form.get("privacy_mai")),
        # Come le due liste: e' una scelta di chi converte, non del preset,
        # e questo e' il ramo che l'interfaccia percorre sempre.
        segnala=segnala_da_form(form),
        # Stesso discorso della numerazione: non e' un riconoscitore, quindi
        # non sta in `FIELD_DEFAULTS` ne' nei profili, e va letta a mano da
        # qui — che e' il ramo percorso dall'interfaccia, la quale manda
        # sempre un profilo. Dimenticarla qui avrebbe reso la casella
        # decorativa: e' precisamente il difetto per cui esiste
        # `tests/test_gui_parity.py`.
        numerati=(
            _truthy(form.get("privacy_numerati"), PrivacyOptions.numerati)
            if "privacy_numerati" in form
            else PrivacyOptions.numerati
        ),
        **{
            k: (_truthy(form.get("privacy_" + k), v) if "privacy_" + k in form else v)
            for k, v in base.items()
        },
    )


def _privacy_dalla_richiesta(form) -> PrivacyOptions:
    """Le opzioni privacy di *questa* richiesta, profilo compreso.

    Esiste perche' la regola stava scritta due volte e la seconda copia era
    incompleta: le rotte del PDF chiamavano `options_from_form`, che il
    profilo non lo guarda. Risultato: la stessa pagina, con le stesse
    caselle, rediggeva il Markdown in un modo e il PDF in un altro — e la
    differenza si vedeva solo aprendo i due file uno accanto all'altro.

    Ora la regola sta in un posto solo. Una rotta nuova che chiama questa
    non puo' sbagliarla; una che chiama `options_from_form` a mano ripete
    lo stesso difetto, ed e' il motivo per cui questa funzione ha un nome
    invece di essere due righe copiate.
    """
    profile_id = form.get("profile") or form.get("preset")
    if profile_id and profile_id in PROFILES:
        return _merge_privacy(form, PROFILES[profile_id])
    return options_from_form(form)


def lingua_richiesta(esplicita: str | None = None) -> str:
    """La lingua di *questa* richiesta.

    Non guarda `request.form`: la usa anche `app_factory`, dentro un
    `before_request` e nel gestore del 413, dove leggere il modulo
    vorrebbe dire far analizzare a Flask un invio che stiamo rifiutando
    proprio perche' e' troppo grande.

    Chi il modulo ce l'ha gia' in mano passa il campo `lang` in
    ``esplicita``: lo manda il JavaScript leggendo `<html lang>`, ed e'
    l'unica fonte che sa davvero cosa l'utente sta guardando adesso.
    Sotto restano cookie e Accept-Language, gli stessi che decidono la
    pagina, cosi' schermo e documento non possono divergere.
    """
    return lingua_da(
        request.headers.get("Accept-Language"),
        cookie=request.cookies.get("mr_rao_lang"),
        query=esplicita or request.args.get("lang"),
    )


def _parse_options_from_request() -> ConvertOptions:
    form = request.form
    lingua = lingua_richiesta(form.get("lang"))
    profile_id = form.get("profile") or form.get("preset")
    if profile_id:
        opts = options_from_profile(profile_id)
        if opts:
            # La lingua non e' un'opzione del profilo: il profilo dice *come*
            # convertire, la lingua dice in che lingua sono scritte le nostre
            # righe dentro il documento.
            opts.lingua = lingua
            # Il profilo e' il punto di partenza, non l'ultima parola: quello
            # che l'utente ha toccato vince. Prima il profilo vinceva su
            # tutto, e siccome l'interfaccia manda sempre il profilo, l'intero
            # pannello «Quali dati nascondere» — interruttore generale
            # compreso — non comandava nulla.
            if form.get("engine"):
                eng = form.get("engine")
                if eng == "paddleocr":
                    eng = "rapidocr"
                opts.engine = eng
            if form.get("language"):
                opts.language = form.get("language", opts.language)
            opts.privacy = _privacy_dalla_richiesta(form)
            for attr, key in (
                ("include_tables", "include_tables"),
                ("include_frontmatter", "include_frontmatter"),
                ("clean_output", "clean_output"),
                ("force_ocr_pdf", "force_ocr_pdf"),
                ("include_raw", "include_raw"),
                ("extract_attachments", "extract_attachments"),
            ):
                if key in form:
                    setattr(opts, attr, _truthy(form.get(key), getattr(opts, attr)))
            return opts

    engine = form.get("engine", "auto")
    if engine == "paddleocr":
        engine = "rapidocr"
    privacy = _privacy_dalla_richiesta(form)
    return ConvertOptions(
        engine=engine,
        language=form.get("language", "it"),
        lingua=lingua,
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


def _validate_filename(
    filename: str, lingua: str = LINGUA_PREDEFINITA
) -> tuple[str | None, str | None]:
    if not filename:
        return None, t("err_nessun_file", lingua)
    original_ext = Path(filename).suffix.lower() if "." in filename else ""
    if original_ext not in ALLOWED_EXTENSIONS:
        return None, t("err_tipo_non_supportato", lingua, ext=original_ext)
    return original_ext, None


@bp.route("/")
def index():
    from mr_rao.i18n import CATEGORIE_NON_SEGNALABILI, TESTI, etichetta_categoria

    # La stessa funzione che decide la lingua delle risposte JSON e del
    # testo dentro i documenti: se qui si scegliesse diversamente, si
    # potrebbe leggere una pagina in una lingua e ricevere un errore
    # nell'altra.
    lingua = lingua_richiesta()
    risposta = make_response(
        render_template(
            "index.html",
            app_name=APP_NAME,
            app_version=APP_VERSION,
            # The client-side size check must follow MR_RAO_MAX_UPLOAD_MB, not a
            # hardcoded 50, or raising the server limit changes nothing.
            max_upload_mb=MAX_UPLOAD_MB,
            lang=lingua,
            # `t` come funzione, non un dizionario gia' risolto: cosi' il
            # template chiede `t('chiave')` e una chiave sbagliata si vede
            # come testo brutto invece di far saltare la pagina.
            t=lambda chiave, **kw: t(chiave, lingua, **kw),
            # Le stesse stringhe al JavaScript, in un blob inline: nessun
            # file in piu' da impacchettare, nessuna chiamata di rete.
            testi_js={k: v[lingua] for k, v in TESTI.items()},
            # Le categorie del terzo stato («rileva ma non sostituire»)
            # arrivano dal motore, non da un elenco copiato nel template:
            # una categoria nuova compare nel pannello il giorno che nasce,
            # invece di restare irraggiungibile dall'interfaccia in silenzio.
            #
            # Coppie `(identificatore, nome leggibile)`: il primo e' quello
            # che il motore riceve, il secondo quello che l'utente legge.
            # Prima il pannello mostrava `bban`, `mrz`, `routing_number` --
            # i nomi con cui il codice parla a se stesso.
            #
            # `termini` resta fuori: non e' un dato riconosciuto dal motore,
            # e' la lista di parole che l'utente **stesso** ha chiesto di
            # proteggere, e chiedere di segnalarle invece di sostituirle
            # vuol dire chiedere al programma di disobbedire a una richiesta
            # esplicita.
            categorie=[
                (c, etichetta_categoria(c, lingua))
                for c in CATEGORIE
                if c not in CATEGORIE_NON_SEGNALABILI
            ],
        )
    )
    if request.args.get("lang"):
        # La scelta esplicita si ricorda. Solo `SameSite=Lax` e nessun
        # `Secure`: e' un server locale in http, e un cookie che il browser
        # rifiuta e' peggio di nessun cookie.
        # Il valore scritto e' ricontrollato qui e non solo dentro
        # `lingua_da`: cio' che finisce in un'intestazione HTTP si valida nel
        # punto in cui ci finisce, cosi' resta vero anche se un domani
        # `lingua_da` cambia. `?lang=` arriva dall'utente.
        risposta.set_cookie(
            "mr_rao_lang",
            lingua if lingua in LINGUE else LINGUA_PREDEFINITA,
            max_age=60 * 60 * 24 * 365,
            samesite="Lax", httponly=False,
        )
    return risposta


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


def _fail_job(job, exc: Exception, lingua: str = LINGUA_PREDEFINITA) -> None:
    """Never leave a job in 'running': the UI would poll it forever."""
    print(f"job {job.id} crashed: {exc!r}")
    with job.lock:
        if job.status in ("done", "cancelled"):
            return
        job.status = "error"
        job.error = t("err_interno_conversione", lingua)
        job.message = job.error


def _run_job_single(job_id: str, data: bytes, filename: str, options: ConvertOptions) -> None:
    job = job_store.get(job_id)
    if not job:
        return
    try:
        _run_job_single_inner(job, data, filename, options)
    except Exception as e:  # noqa: BLE001 — last line of defence for the worker thread
        _fail_job(job, e, options.lingua)


def _run_job_single_inner(job, data: bytes, filename: str, options: ConvertOptions) -> None:
    with job.lock:
        # Annullato mentre era **in coda**. Dietro `MAX_WORKERS` i lavori
        # aspettano il loro turno, e un annullamento arrivato in quella
        # finestra veniva sovrascritto proprio qui: `cancel()` aveva gia'
        # scritto «cancelled», il worker prendeva il lavoro in mano e lo
        # riportava a «running». Il lavoro vero non partiva comunque -- il
        # convertitore esce al primo controllo -- ma chi guardava la pagina
        # vedeva la barra ripartire su qualcosa che aveva appena annullato,
        # ed e' l'unica cosa che conta per chi ha premuto quel tasto.
        if job.cancel_flag:
            return
        job.status = "running"
        job.message = t("job_avvio", options.lingua)

    # , non :  e' la funzione delle traduzioni, e un parametro
    # con lo stesso nome la nasconderebbe dentro questa funzione annidata.
    def progress(c, totale, msg):
        job.set_progress(c, totale, msg)

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
            job.message = t("job_annullato", options.lingua)
            return
        if result.error:
            job.status = "error"
            job.error = result.error
            job.message = result.error
        else:
            job.status = "done"
            job.message = t("job_completato", options.lingua)
            job.progress = job.total
            job.result = _result_payload(result)


def _run_job_batch(
    job_id: str,
    items: list[tuple[bytes, str]],
    options: ConvertOptions,
    merge: bool,
    merge_title: str | None,
    compare: bool = False,
) -> None:
    job = job_store.get(job_id)
    if not job:
        return
    try:
        _run_job_batch_inner(job, items, options, merge, merge_title, compare)
    except Exception as e:  # noqa: BLE001 — last line of defence for the worker thread
        _fail_job(job, e, options.lingua)


def _run_job_batch_inner(
    job,
    items: list[tuple[bytes, str]],
    options: ConvertOptions,
    merge: bool,
    merge_title: str | None,
    compare: bool = False,
) -> None:
    with job.lock:
        # Stessa finestra del lavoro singolo: annullato mentre era in coda.
        if job.cancel_flag:
            return
        job.status = "running"
        job.total = len(items)
        job.message = t("job_batch", options.lingua)

    results = []
    for i, (data, filename) in enumerate(items):
        if job.should_cancel():
            with job.lock:
                job.status = "cancelled"
                job.message = t("job_annullato", options.lingua)
            return
        job.set_progress(
            i,
            len(items),
            t("job_file_n", options.lingua, i=i + 1, n=len(items), nome=filename),
        )

        def progress(c, totale, msg, _i=i, _n=len(items), _f=filename):
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
            job.message = t("job_annullato", options.lingua)
        return

    if merge or compare:
        # Il titolo predefinito lo decide qui il server, nella lingua del
        # lavoro. Prima si confrontava `merge_title` **per valore** con
        # «Documento unificato» — una stringa che scriveva il client: bastava
        # tradurla perche' il ramo non scattasse piu' e un confronto uscisse
        # intitolato come un'unione. Ora il client o manda un titolo suo, o
        # non manda niente.
        title = merge_title or t(
            "doc_titolo_confronto" if compare else "doc_titolo_unificato",
            options.lingua,
        )
        merged = merge_markdowns(
            results, title=title, compare_mode=compare, lingua=options.lingua
        )
        redaction_total = sum(r.redaction.total for r in results)
        with job.lock:
            job.status = "done"
            job.progress = len(items)
            job.message = t(
                "js_confronto_completato" if compare else "job_merge_completato",
                options.lingua,
            )
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
            job.message = t("job_batch_completato", options.lingua)
            job.result = {
                "batch": True,
                "items": [
                    {**_result_payload(r), "error": r.error}
                    for r in results
                ],
            }


@bp.route("/api/convert", methods=["POST"])
def convert_api():
    # No .eml special case here: the privacy default is decided once in
    # options_from_form(), which is fail-safe (redacts unless told otherwise).
    options = _parse_options_from_request()
    lingua = options.lingua

    if "file" not in request.files:
        return jsonify({"error": t("err_nessun_file_richiesta", lingua)}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": t("err_nessun_file", lingua)}), 400

    _, err = _validate_filename(file.filename, lingua)
    if err:
        return jsonify({"error": err}), 400

    data = file.read()
    if not data:
        return jsonify({"error": t("err_file_vuoto", lingua)}), 400
    if len(data) > current_app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"error": t("err_troppo_grande", lingua)}), 400

    job = job_store.create()
    with job.lock:
        job.message = t("job_in_coda", lingua)
    _spawn(_run_job_single, job.id, data, file.filename, options)
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/batch", methods=["POST"])
def convert_batch():
    options = _parse_options_from_request()
    lingua = options.lingua

    files = request.files.getlist("files") or request.files.getlist("file")
    if not files:
        return jsonify({"error": t("err_nessun_file_richiesta", lingua)}), 400

    merge = _truthy(request.form.get("merge"), False)
    compare = _truthy(request.form.get("compare"), False)
    # Vuoto = «decidilo tu»: il titolo predefinito lo sceglie il worker nella
    # lingua del lavoro, invece di riconoscerlo dal valore che manda il client.
    merge_title = (request.form.get("merge_title") or "").strip() or None
    if compare:
        merge = True

    items: list[tuple[bytes, str]] = []
    for f in files:
        if not f or not f.filename:
            continue
        _, err = _validate_filename(f.filename, lingua)
        if err:
            return jsonify({"error": f"{f.filename}: {err}"}), 400
        data = f.read()
        if data:
            items.append((data, f.filename))

    if not items:
        return jsonify({"error": t("err_nessun_file_valido", lingua)}), 400
    if compare and len(items) != 2:
        return jsonify({"error": t("err_confronto_due_file", lingua)}), 400

    job = job_store.create()
    with job.lock:
        job.message = t("job_in_coda", lingua)
    _spawn(_run_job_batch, job.id, items, options, merge, merge_title, compare)
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/compare", methods=["POST"])
def convert_compare():
    """Compare exactly two documents. Convenience alias of /api/convert/batch
    with compare=1, accepting file_a/file_b instead of a files[] list."""
    options = _parse_options_from_request()
    lingua = options.lingua

    files = request.files.getlist("files")
    if len(files) < 2:
        a = request.files.get("file_a") or request.files.get("file1")
        b = request.files.get("file_b") or request.files.get("file2")
        files = [f for f in (a, b) if f]
    if len(files) != 2:
        return jsonify({"error": t("err_due_file_ab", lingua)}), 400

    items: list[tuple[bytes, str]] = []
    for f in files:
        if not f.filename:
            return jsonify({"error": t("err_nome_mancante", lingua)}), 400
        _, err = _validate_filename(f.filename, lingua)
        if err:
            return jsonify({"error": err}), 400
        data = f.read()
        if not data:
            return jsonify({"error": t("err_file_vuoto_nome", lingua, nome=f.filename)}), 400
        items.append((data, f.filename))

    job = job_store.create()
    with job.lock:
        job.message = t("job_in_coda", lingua)
    _spawn(
        _run_job_batch,
        job.id,
        items,
        options,
        True,
        (request.form.get("merge_title") or "").strip() or None,
        True,
    )
    return jsonify({"job_id": job.id}), 202


@bp.route("/api/convert/sync", methods=["POST"])
def convert_sync():
    options = _parse_options_from_request()
    lingua = options.lingua

    if "file" not in request.files:
        return jsonify({"error": t("err_nessun_file_richiesta", lingua)}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": t("err_nessun_file", lingua)}), 400
    _, err = _validate_filename(file.filename, lingua)
    if err:
        return jsonify({"error": err}), 400

    data = file.read()
    result = convert_bytes(data, file.filename, options=options)
    if result.error:
        return jsonify({"error": result.error}), 500
    return jsonify(_result_payload(result))


@bp.route("/api/export/docx", methods=["POST"])
def export_docx():
    """Markdown gia' redatto -> .docx da scaricare.

    Il `.md` e il `.txt` li costruisce il browser da se'. Questo no: un .docx
    e' un archivio zip con dentro dell'XML, e generarlo lato client vorrebbe
    dire portarsi una libreria in piu' nella pagina.

    **Non converte il documento originale.** Riceve il Markdown *gia'
    redatto* -- cioe' un testo in cui i dati personali sono gia' segnaposto --
    e lo rimette in forma di documento. Il dato non e' coperto: e' assente.
    """
    lingua = lingua_richiesta()
    if not docx_disponibile():
        return jsonify({"error": t("err_docx_assente", lingua)}), 501

    dati = request.get_json(silent=True) or {}
    markdown = dati.get("markdown") or ""
    if not markdown.strip():
        return jsonify({"error": t("err_niente_da_esportare", lingua)}), 400

    # Il nome arriva dal client: qui diventa solo il nome del file scaricato,
    # e `send_file` lo mette in un'intestazione HTTP. Si tiene il gambo e si
    # scarta tutto il resto, percorsi compresi.
    nome = Path(str(dati.get("filename") or "documento")).stem or "documento"
    nome = re.sub(r"[^\w \-.]", "", nome)[:80].strip() or "documento"

    try:
        contenuto = markdown_to_docx(markdown, lingua=lingua)
    except Exception:
        current_app.logger.exception("export docx")
        return jsonify({"error": t("err_docx_fallito", lingua)}), 500

    return send_file(
        io.BytesIO(contenuto),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=f"{nome}.docx",
    )


#: Quanto grande esce un'anteprima. Due immagini per pagina viaggiano dentro un
#: JSON: a scala 1.4 una pagina A4 sta sotto i 200 KB e si legge; a scala 2 ne
#: pesa il doppio e non si legge meglio dentro un riquadro largo mezzo schermo.
_SCALA_ANTEPRIMA = 1.4


def _redigi_pdf_caricato(lingua: str):
    """Legge il PDF dalla richiesta e lo redige. Ritorna (bytes, esito, errore)."""
    if "file" not in request.files:
        return None, None, (t("err_nessun_file_richiesta", lingua), 400)
    file = request.files["file"]
    if not file.filename:
        return None, None, (t("err_nessun_file", lingua), 400)
    if Path(file.filename).suffix.lower() != ".pdf":
        return None, None, (t("err_pdf_solo_pdf", lingua), 400)

    dati = file.read()
    if not dati:
        return None, None, (t("err_file_vuoto", lingua), 400)
    if len(dati) > current_app.config["MAX_CONTENT_LENGTH"]:
        return None, None, (t("err_troppo_grande", lingua), 400)

    import tempfile

    from mr_rao.redazione_pdf import redigi_pdf

    opzioni = _privacy_dalla_richiesta(request.form)
    with tempfile.TemporaryDirectory() as cartella:
        dentro = Path(cartella) / "dentro.pdf"
        fuori = Path(cartella) / "fuori.pdf"
        dentro.write_bytes(dati)
        try:
            esito = redigi_pdf(dentro, fuori, opzioni)
        except Exception:
            current_app.logger.exception("redazione pdf")
            return None, None, (t("err_pdf_fallita", lingua), 500)
        if esito.scansione:
            return None, esito, (t("err_pdf_scansione", lingua), 422)
        if not fuori.exists():
            return None, esito, (t("err_pdf_fallita", lingua), 500)
        return fuori.read_bytes(), esito, None


def _pagina_in_png(dati: bytes, numero: int) -> str:
    """Una pagina come PNG in base64, pronta per un `src`."""
    import base64

    import pypdfium2 as pdfium

    documento = pdfium.PdfDocument(io.BytesIO(dati))
    try:
        numero = max(0, min(numero, len(documento) - 1))
        immagine = documento[numero].render(scale=_SCALA_ANTEPRIMA).to_pil()
    finally:
        documento.close()
    buffer = io.BytesIO()
    immagine.convert("RGB").save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


@bp.route("/api/pdf/anteprima", methods=["POST"])
def anteprima_pdf():
    """Prima e dopo, la stessa pagina, come immagini.

    **L'anteprima non e' un vezzo.** Chi redige un atto da depositare deve
    poter vedere cosa e' sparito prima di consegnarlo, e deve poterlo vedere
    *sulla pagina*: un numero che dice «14 sostituzioni» non fa distinguere il
    nome tolto dal nome che era gia' li'.

    Si rendono immagini invece di mostrare il PDF in un riquadro perche' e'
    l'unica cosa che funziona uguale ovunque — dentro la finestra
    dell'applicazione, in Edge, in Firefox — senza dipendere da un lettore PDF
    incorporato che c'e' o non c'e'.
    """
    lingua = lingua_richiesta(request.form.get("lang"))
    dati_originali = b""
    if "file" in request.files:
        dati_originali = request.files["file"].read()
        request.files["file"].stream.seek(0)

    redatto, esito, errore = _redigi_pdf_caricato(lingua)
    if errore:
        messaggio, codice = errore
        return jsonify({"error": messaggio}), codice

    try:
        numero = int(request.form.get("pagina") or 0)
    except ValueError:
        numero = 0

    return jsonify({
        "pagine": esito.pagine,
        "pagina": numero,
        "sostituzioni": esito.segnaposto_inseriti,
        # **Le pagine non trattate si dicono sempre**, anche quando sono zero:
        # una pagina finita nel ripiego NON e' stata redatta, e presentarla
        # come tale sarebbe il modo peggiore di sbagliare.
        "pagine_non_trattate": sorted(esito.pagine_in_ripiego),
        "prima": _pagina_in_png(dati_originali, numero),
        "dopo": _pagina_in_png(redatto, numero),
    })


@bp.route("/api/export/pdf", methods=["POST"])
def export_pdf():
    """Il PDF redatto da scaricare.

    Non copre i dati con dei rettangoli: **toglie i glifi dal flusso di
    contenuto**. Il documento che esce e' ancora un PDF di testo, selezionabile
    e ricercabile, pesa quanto quello di partenza, e il dato non c'e' piu' nel
    file — non e' nascosto sotto qualcosa.
    """
    lingua = lingua_richiesta(request.form.get("lang"))
    nome_originale = ""
    if "file" in request.files:
        nome_originale = request.files["file"].filename or ""

    redatto, esito, errore = _redigi_pdf_caricato(lingua)
    if errore:
        messaggio, codice = errore
        return jsonify({"error": messaggio}), codice

    nome = Path(str(nome_originale or "documento")).stem
    nome = re.sub(r"[^\w \-.]", "", nome)[:80].strip() or "documento"
    risposta = send_file(
        io.BytesIO(redatto),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{nome}-redatto.pdf",
    )
    # I conti viaggiano nelle intestazioni: il corpo e' il file, e chi scarica
    # deve poter sapere quante pagine non sono state trattate senza aprirlo.
    risposta.headers["X-MrRao-Sostituzioni"] = str(esito.segnaposto_inseriti)
    risposta.headers["X-MrRao-Pagine-Non-Trattate"] = ",".join(
        str(p) for p in sorted(esito.pagine_in_ripiego))
    return risposta


@bp.route("/api/jobs/<job_id>", methods=["GET"])
def job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        return jsonify({"error": t("err_job_assente", lingua_richiesta())}), 404
    return jsonify(job.to_public())


@bp.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def job_cancel(job_id: str):
    if not job_store.cancel(job_id):
        return jsonify({"error": t("err_job_assente", lingua_richiesta())}), 404
    return jsonify({"ok": True, "id": job_id})


@bp.route("/api/paste-image", methods=["POST"])
def paste_image():
    return convert_api()


@bp.route("/api/folders/defaults", methods=["GET"])
def folders_defaults():
    """Percorsi predefiniti, in sola lettura.

    Una GET deve essere sicura (RFC 9110): prima questa creava directory, e
    bastava un <img src> su una pagina qualsiasi per far comparire cartelle
    nei Documenti dell'utente.
    """
    return jsonify({"ok": True, **describe_default_folders()})


@bp.route("/api/folders/defaults", methods=["POST"])
def folders_defaults_create():
    """Crea le cartelle predefinite. Modifica lo stato, quindi è POST e passa
    dal controllo anti-CSRF sull'header Origin."""
    return jsonify({"ok": True, **ensure_default_watch_folders()})


@bp.route("/api/folders/browse", methods=["POST"])
def folders_browse():
    """Native OS folder picker (local app only). Body: { initial?, title? }."""
    data = request.get_json(silent=True) or {}
    initial = data.get("initial") or request.form.get("initial")
    lingua = lingua_richiesta(data.get("lang"))
    title = (
        data.get("title")
        or request.form.get("title")
        or t("js_scegli_cartella", lingua)
    )
    path = browse_folder(initial=initial, title=title)
    if not path:
        return jsonify({"ok": False, "cancelled": True, "path": None})
    return jsonify({"ok": True, "cancelled": False, "path": path})


def _stato_watch_tradotto(state: dict) -> dict:
    """Il messaggio «non attivo» nella lingua di chi sta guardando.

    Mentre il monitoraggio lavora, il messaggio racconta un file e resta
    nella lingua scelta all'avvio: e' la stessa dei documenti che sta
    scrivendo, e cambiarla a meta' sarebbe una bugia. Ma **da fermo** non
    c'e' nessun lavoro in corso, e quel testo lo ha scritto il valore
    predefinito della classe -- deciso all'importazione del modulo, quando
    di richieste non ce n'era ancora nessuna. Qui la richiesta c'e'.
    """
    if not state.get("running"):
        state["message"] = t("watch_msg_non_attivo", lingua_richiesta())
    return state


@bp.route("/api/watch", methods=["GET"])
def watch_get():
    # Nessuna creazione qui: la UI interroga questo endpoint ogni 4 secondi,
    # e creare cartelle a ogni poll significa toccare il disco (e la sincro-
    # nizzazione cloud) per sempre.
    state = _stato_watch_tradotto(get_watch_state())
    state["defaults"] = describe_default_folders()
    return jsonify(state)


@bp.route("/api/watch", methods=["POST"])
def watch_start():
    data = request.get_json(silent=True) or {}
    # also accept form
    defaults = ensure_default_watch_folders()
    inbox = data.get("inbox") or request.form.get("inbox") or defaults["inbox"]
    outbox = data.get("outbox") or request.form.get("outbox") or defaults["outbox"]
    if not inbox or not outbox:
        return jsonify({"error": t("err_inbox_outbox", lingua_richiesta())}), 400
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
        # Anche la cartella sorvegliata scrive documenti: la lingua gliela fissa
        # chi accende il monitoraggio, perche' poi lavora senza nessuna richiesta.
        options.lingua = lingua_richiesta(data.get("lang"))
    state = start_watch(inbox, outbox, options=options, interval=interval, move_done=move_done)
    return jsonify(state)


@bp.route("/api/watch", methods=["DELETE"])
def watch_stop():
    return jsonify(_stato_watch_tradotto(stop_watch()))
