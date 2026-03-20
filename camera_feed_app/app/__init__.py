import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, send_from_directory

from camera_feed_app.config import Config


def _configure_logging(app: Flask) -> None:
    app.logger.setLevel(app.config["LOG_LEVEL"])

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    if not app.debug:
        file_handler = RotatingFileHandler("camera_feed_app.log", maxBytes=1_000_000, backupCount=3)
        file_handler.setLevel(app.config["LOG_LEVEL"])
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable Gzip compression for JSON/HTML responses
    app.config["COMPRESS_MIMETYPES"] = [
        "text/html", "text/css", "text/xml",
        "text/javascript", "application/json"
    ]
    app.config["COMPRESS_MIN_SIZE"] = 500
    from flask_compress import Compress
    Compress(app)

    app.config["CAPTURES_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["RECORDINGS_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["UPLOADS_DIR"].mkdir(parents=True, exist_ok=True)

    _configure_logging(app)

    from camera_feed_app.app.routes.camera_routes import camera_bp

    app.register_blueprint(camera_bp)

    @app.get("/favicon.ico")
    def favicon():
        resp = send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")
        resp.headers["Cache-Control"] = "public, max-age=86400"  # 1 day
        return resp

    return app
