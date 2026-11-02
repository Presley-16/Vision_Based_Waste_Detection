"""Serves uploaded photos, plus the two static frontends as a single-port convenience.

The citizen website (frontend/) and municipal dashboard (municipal/) are plain
static sites that only talk to /api — they can be hosted anywhere. Serving them
from here just means `python backend/run.py` brings the whole system up on one
port, which is also the address phones scan via the install QR code.
"""
from flask import Blueprint, current_app, redirect, send_from_directory

web = Blueprint("web", __name__)


@web.get("/uploads/<path:filename>")
def uploads(filename: str):
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)


@web.get("/municipal")
def municipal_root():
    return redirect("/municipal/")


@web.get("/municipal/", defaults={"path": "index.html"})
@web.get("/municipal/<path:path>")
def municipal_site(path: str):
    return send_from_directory(current_app.config["MUNICIPAL_DIR"], path)


@web.get("/get-app")
def get_app():
    return redirect("/get-app.html")


@web.get("/", defaults={"path": "index.html"})
@web.get("/<path:path>")
def citizen_site(path: str):
    return send_from_directory(current_app.config["FRONTEND_DIR"], path)
