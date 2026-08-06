"""Flask application factory for Mr. Rao."""
from __future__ import annotations

from flask import Flask, jsonify, request

import config
from mr_rao.routes import bp


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


def _register_guards(app: Flask) -> None:
    """A server on localhost is reachable by every page the browser has open.

    Two distinct attacks, two distinct checks:
    - DNS rebinding: an attacker domain resolving to 127.0.0.1 would read
      responses. Defeated by pinning the Host header.
    - CSRF: a cross-site POST (multipart is CORS-safelisted, so no preflight)
      could start a hotfolder or convert files. Defeated by refusing a
      cross-site Origin on state-changing methods.
    """

    @app.before_request
    def _check_origin():
        allowed = app.config["ALLOWED_HOSTS"]
        host = _hostname(request.host or "")
        if "*" not in allowed and host not in allowed:
            return (
                jsonify(
                    {
                        "error": (
                            f"Host '{host}' non consentito. Usa http://127.0.0.1 "
                            "oppure imposta MR_RAO_ALLOWED_HOSTS."
                        )
                    }
                ),
                403,
            )

        origin = request.headers.get("Origin")
        if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
            if _hostname(origin) != host:
                return (
                    jsonify({"error": "Richiesta cross-site rifiutata"}),
                    403,
                )
        return None


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
                    "error": (
                        f"Richiesta troppo grande. Limite {max_mb} MB "
                        "per l'intero invio (non per singolo file)."
                    ),
                    "max_mb": max_mb,
                }
            ),
            413,
        )

    @app.errorhandler(404)
    def _not_found(e):
        if _wants_json():
            return jsonify({"error": "Endpoint non trovato"}), 404
        return e

    @app.errorhandler(405)
    def _not_allowed(e):
        if _wants_json():
            return jsonify({"error": "Metodo non consentito"}), 405
        return e

    @app.errorhandler(Exception)
    def _unhandled(e):
        from werkzeug.exceptions import HTTPException

        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Errore non gestito")
        if _wants_json():
            return jsonify({"error": "Errore interno del server"}), 500
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
    # Le crea la UI (POST /api/folders/defaults) o l'avvio della sorveglianza.

    app.register_blueprint(bp)
    _register_guards(app)
    _register_error_handlers(app)
    return app
