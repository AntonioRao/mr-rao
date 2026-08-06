"""Flask application factory for Mr. Rao."""
from __future__ import annotations

from flask import Flask

import config
from mr_rao.routes import bp


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

    config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    app.register_blueprint(bp)
    return app
