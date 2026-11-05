"""PlanetWatch backend — JSON API for the citizen website, mobile app, and municipal dashboard."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix

from .models import db

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")


def create_app() -> Flask:
    app = Flask(__name__, instance_path=str(BACKEND_DIR / "instance"), static_folder=None)
    if os.environ.get("TRUSTED_PROXY") == "1":
        # Behind nginx (deploy/): take the client IP and https scheme from its
        # X-Forwarded-* headers. Without this every request looks local, which
        # would open the this-computer-only USB install endpoints to everyone.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    # A fresh random key each process start invalidates every previously-issued
    # token, so restarting the server always forces a new sign-in — set
    # FLASK_SECRET_KEY explicitly to opt back into surviving restarts.
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///reports.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024  # several phone photos per report
    app.config["UPLOAD_DIR"] = str(BACKEND_DIR / "uploads")
    app.config["FRONTEND_DIR"] = os.environ.get("FRONTEND_DIR", str(REPO_ROOT / "frontend"))
    app.config["MUNICIPAL_DIR"] = os.environ.get("MUNICIPAL_DIR", str(REPO_ROOT / "municipal"))
    app.config["APK_PATH"] = os.environ.get("APK_PATH", str(REPO_ROOT / "mobile" / "dist" / "PlanetWatch.apk"))

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        # citizens table is newer than reports, so create_all() won't
        # retrofit the FK onto an existing sqlite file — add it if missing.
        inspector = inspect(db.engine)
        report_columns = {col["name"] for col in inspector.get_columns("reports")}
        if "citizen_id" not in report_columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE reports ADD COLUMN citizen_id INTEGER REFERENCES citizens(id)"))
        citizen_columns = {col["name"] for col in inspector.get_columns("citizens")}
        for column, ddl in (("password_hash", "VARCHAR(255)"), ("photo_path", "VARCHAR(255)")):
            if column not in citizen_columns:
                with db.engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE citizens ADD COLUMN {column} {ddl}"))

    _enable_cors(app)

    from .api import api
    from .install import install
    from .municipal import municipal
    from .web import web

    app.register_blueprint(api)
    app.register_blueprint(municipal)
    app.register_blueprint(install)
    app.register_blueprint(web)

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "Those photos are too large — try fewer or smaller images."}), 413

    return app


def _enable_cors(app: Flask) -> None:
    """Allow the mobile app (served from its own local origin) to call the API.

    Auth is a bearer token, never a cookie, so a wildcard origin is safe here.
    """
    @app.after_request
    def add_cors_headers(response):
        if request.path.startswith(("/api/", "/uploads/")):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, ngrok-skip-browser-warning"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response
