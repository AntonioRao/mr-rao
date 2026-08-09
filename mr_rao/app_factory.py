"""Flask application factory for Mr. Rao."""
from __future__ import annotations

from flask import Flask, jsonify, request

import config
from mr_rao.i18n import t
from mr_rao.routes import bp, lingua_richiesta


def _wants_json() -> bool:
    """API callers get JSON errors; a mistyped page URL still gets Flask's HTML."""
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def _hostname(value: str) -> str:
    """Host/Origin header -> bare hostname, lowercase, without the port."""
    host = value.strip().lower()
    if "//" in host:
        host = host.split("//", 1)[1]
    host = host.split("/", 1)[0]
    if host.startswith("["):  # IPv6 literal: [::1]:5000
        end = host.find("]")
        if end != -1:
            return host[: end + 1]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


METODI_SICURI = ("GET", "HEAD", "OPTIONS")

# Valori di Sec-Fetch-Site che non devono poter modificare stato.
# "same-site" c'è di proposito: per localhost i browser considerano *stessa
# site* anche una porta diversa, quindi una pagina servita da un altro
# programma su 127.0.0.1:8080 supererebbe il controllo di Origin (stesso
# hostname) pur non essendo questa applicazione.
SITE_RIFIUTATI = ("cross-site", "same-site")


def _register_guards(app: Flask) -> None:
    """A server on localhost is reachable by every page the browser has open.

    Tre attacchi distinti, tre controlli distinti:
    - DNS rebinding: un dominio dell'attaccante che risolve a 127.0.0.1
      leggerebbe le risposte. Si blocca fissando l'header Host.
    - CSRF: una POST cross-site (multipart è CORS-safelisted, quindi niente
      preflight) potrebbe avviare un hotfolder o convertire file. Si blocca
      rifiutando Sec-Fetch-Site esterni e Origin esterne.
    - Vicini di porta: un'altra pagina su 127.0.0.1, porta diversa. Origin non
      la distingue (stesso hostname); Sec-Fetch-Site sì.
    """

    @app.before_request
    def _check_origin():
        allowed = app.config["ALLOWED_HOSTS"]
        host = _hostname(request.host or "")
        if "*" not in allowed and host not in allowed:
            # `lingua_richiesta()` non guarda `request.form`: qui siamo in un
            # before_request, e far analizzare a Flask il corpo di una
            # richiesta che stiamo per rifiutare sarebbe lavoro regalato a
            # chi la manda.
            return (
                jsonify({"error": t("err_host", lingua_richiesta(), host=host)}),
                403,
            )

        if request.method in METODI_SICURI:
            return None

        # Sec-Fetch-Site va guardato PRIMA di Origin perché copre il caso che
        # Origin non copre: una navigazione da <form> cross-site può arrivare
        # senza Origin, e allora il controllo sotto non scatta affatto. Questo
        # header i browser attuali lo mandano su ogni richiesta.
        site = (request.headers.get("Sec-Fetch-Site") or "").strip().lower()
        if site in SITE_RIFIUTATI:
            return jsonify({"error": t("err_cross_site", lingua_richiesta())}), 403

        # Chi non manda Sec-Fetch-Site (curl, la CLI, un browser vecchio)
        # ricade qui: è il controllo che c'era prima, non sostituito.
        origin = request.headers.get("Origin")
        if origin and _hostname(origin) != host:
            return jsonify({"error": t("err_cross_site", lingua_richiesta())}), 403
        return None

    @app.after_request
    def _intestazioni_di_sicurezza(response):
        """Due righe che costano zero, con aspettative oneste su cosa fanno.

        frame-ancestors è quella che si guadagna il posto: impedisce di
        incorniciare l'applicazione in un'altra pagina. Il contenuto non
        sarebbe comunque leggibile (same-origin policy), ma il *clic* sì — e
        qui un clic accende il monitoraggio di una cartella.

        nosniff qui ha poco da mordere, perché nessun endpoint restituisce
        contenuto dell'utente con un tipo indovinabile: è tutto JSON e static.
        Vale come rete per gli endpoint che verranno.
        """
        # img-src e' arrivata con l'anteprima fedele (P1.4). Il renderer non
        # emette mai un <img> verso l'esterno, e ci sono i test che lo
        # provano — ma la promessa «non esce niente» e' il cuore del
        # programma, e farla dipendere da una sola espressione regolare
        # scritta da noi e' troppo poco. Le uniche immagini che servono
        # stanno in /static; `data:` resta per l'anteprima di un'immagine
        # incollata, che e' roba dell'utente e non fa traffico.
        response.headers.setdefault(
            "Content-Security-Policy",
            "frame-ancestors 'none'; img-src 'self' data: blob:",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(413)
    def _too_large(_e):
        # Flask aborts before the view runs, so this is the ONLY place the
        # size limit can be reported — and the frontend parses JSON, not HTML.
        # Read at request time, so the message follows MR_RAO_MAX_UPLOAD_MB.
        max_mb = (app.config.get("MAX_CONTENT_LENGTH") or 0) // (1024 * 1024)
        return (
            jsonify(
                {
                    "error": t(
                        "err_richiesta_troppo_grande", lingua_richiesta(), max=max_mb
                    ),
                    "max_mb": max_mb,
                }
            ),
            413,
        )

    @app.errorhandler(404)
    def _not_found(e):
        if _wants_json():
            return jsonify({"error": t("err_endpoint", lingua_richiesta())}), 404
        return e

    @app.errorhandler(405)
    def _not_allowed(e):
        if _wants_json():
            return jsonify({"error": t("err_metodo", lingua_richiesta())}), 405
        return e

    @app.errorhandler(Exception)
    def _unhandled(e):
        from werkzeug.exceptions import HTTPException

        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Errore non gestito")
        if _wants_json():
            return jsonify({"error": t("err_server_interno", lingua_richiesta())}), 500
        raise e


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(config.TEMPLATES_FOLDER),
        static_folder=str(config.STATIC_FOLDER),
        static_url_path="/static",
    )
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = str(config.UPLOAD_FOLDER)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["APP_NAME"] = config.APP_NAME
    app.config["APP_VERSION"] = config.APP_VERSION
    app.config["ALLOWED_HOSTS"] = set(config.ALLOWED_HOSTS)
    app.config["MAX_UPLOAD_MB"] = config.MAX_UPLOAD_MB

    config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    # Le cartelle di lavoro NON si creano all'avvio: chi apre l'app per una
    # conversione al volo non deve trovarsi cartelle nuove nei Documenti.
    # Le crea la UI (POST /api/folders/defaults) o l'attivazione del monitoraggio.

    app.register_blueprint(bp)
    _register_guards(app)
    _register_error_handlers(app)
    return app
