"""Bearer-token auth shared by the citizen website, the mobile app, and the municipal dashboard.

Tokens are signed with the app SECRET_KEY, so — exactly like the old session
cookies — a server restart with no FLASK_SECRET_KEY set invalidates every token
and forces a fresh sign-in. Bearer tokens (rather than cookies) are used because
the mobile app calls the API cross-origin from its own bundled pages.
"""
import hmac
import os
from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, URLSafeSerializer

from .models import Citizen, db

_CITIZEN_SALT = "planetwatch-citizen"
_MUNICIPAL_SALT = "planetwatch-municipal"


def _serializer(salt: str) -> URLSafeSerializer:
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt=salt)


def issue_citizen_token(citizen: Citizen) -> str:
    return _serializer(_CITIZEN_SALT).dumps({"cid": citizen.id})


def issue_municipal_token(username: str) -> str:
    return _serializer(_MUNICIPAL_SALT).dumps({"user": username})


def _bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip() or None
    return None


def _load(salt: str) -> dict | None:
    token = _bearer_token()
    if not token:
        return None
    try:
        return _serializer(salt).loads(token)
    except BadSignature:
        return None


def current_citizen() -> Citizen | None:
    payload = _load(_CITIZEN_SALT)
    if not payload:
        return None
    return db.session.get(Citizen, payload.get("cid"))


def municipal_credentials() -> tuple[str, str]:
    username = os.environ.get("MUNICIPAL_USERNAME") or "admin"
    password = os.environ.get("MUNICIPAL_PASSWORD") or "planetwatch"
    return username, password


def check_municipal_login(username: str, password: str) -> bool:
    expected_user, expected_password = municipal_credentials()
    return hmac.compare_digest(username, expected_user) and hmac.compare_digest(password, expected_password)


def citizen_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.citizen = current_citizen()
        if not g.citizen:
            return jsonify({"error": "Please sign in to continue."}), 401
        return view(*args, **kwargs)
    return wrapper


def municipal_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        payload = _load(_MUNICIPAL_SALT)
        if not payload:
            return jsonify({"error": "Municipal sign-in required."}), 401
        g.municipal_user = payload.get("user")
        return view(*args, **kwargs)
    return wrapper
