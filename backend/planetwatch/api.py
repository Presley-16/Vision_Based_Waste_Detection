"""Citizen-facing JSON API used by both the website (frontend/) and the mobile app (mobile/)."""
import os
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request
from PIL import Image, ImageOps, UnidentifiedImageError

from model.exif_extract import IMAGE_EXTENSIONS, extract_gps_and_timestamp

from .alerts import notify_new_report, send_sms_alert, sms_number
from .auth import citizen_required, issue_citizen_token
from .models import Citizen, Detection, PasswordReset, Report, db

api = Blueprint("api", __name__, url_prefix="/api")


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _payload() -> dict:
    return request.get_json(silent=True) or request.form.to_dict()


def _find_citizen(name: str, surname: str) -> Citizen | None:
    return Citizen.query.filter(
        db.func.lower(Citizen.name) == name.lower(),
        db.func.lower(Citizen.surname) == surname.lower(),
    ).first()


def _auth_response(citizen: Citizen):
    return jsonify({"token": issue_citizen_token(citizen), "citizen": citizen.to_dict()})


MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128


def _password(data: dict, key: str = "password") -> str:
    # Never stripped: spaces and any other characters are part of the password.
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Your password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Your password can be at most {MAX_PASSWORD_LENGTH} characters long."
    return None


@api.post("/auth/signin")
def signin():
    data = _payload()
    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    password = _password(data)
    if not name or not surname or not password:
        return jsonify({"error": "Please enter your first name, surname and password."}), 400

    citizen = _find_citizen(name, surname)
    if citizen and not citizen.has_password:
        return jsonify({"error": "This account doesn't have a password yet. Sign Up again with the same "
                                 "name and surname to set one."}), 401
    if not citizen or not citizen.check_password(password):
        return jsonify({"error": "The name, surname or password is incorrect."}), 401
    return _auth_response(citizen)


@api.post("/auth/signup")
def signup():
    data = _payload()
    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    address = (data.get("address") or "").strip()
    phone = (data.get("phone") or "").strip()
    password = _password(data)

    if not name or not surname or not phone or not password:
        return jsonify({"error": "Please fill in your name, surname, phone number and password."}), 400
    problem = _password_problem(password)
    if problem:
        return jsonify({"error": problem}), 400

    citizen = _find_citizen(name, surname)
    if citizen and citizen.has_password:
        return jsonify({"error": "An account with this name and surname already exists. Sign In instead."}), 409
    if citizen:
        # An account from before passwords existed: signing up again claims it.
        citizen.phone = phone
        citizen.address = address or citizen.address
    else:
        citizen = Citizen(name=name, surname=surname, address=address, phone=phone)
        db.session.add(citizen)
    citizen.set_password(password)
    db.session.commit()
    return _auth_response(citizen)


@api.get("/me")
@citizen_required
def me():
    return jsonify({"citizen": g.citizen.to_dict()})


# ---------- Forgot password: a 6-digit code texted to the account's phone ----------

RESET_CODE_MINUTES = 10
RESET_MAX_ATTEMPTS = 5
RESET_RESEND_SECONDS = 60
RESET_MAX_PER_HOUR = 5


def _masked_phone(phone: str) -> str:
    digits = [c for c in phone if c.isdigit()]
    return "\u2022\u2022\u2022\u2022 \u2022\u2022\u2022 " + "".join(digits[-3:]) if len(digits) >= 3 else "your phone"


@api.post("/auth/forgot")
def forgot_password():
    data = _payload()
    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    if not name or not surname:
        return jsonify({"error": "Please enter your first name and surname."}), 400
    citizen = _find_citizen(name, surname)
    if not citizen:
        return jsonify({"error": "We couldn't find an account with that name and surname."}), 404

    now = datetime.utcnow()
    recent = (PasswordReset.query.filter(PasswordReset.citizen_id == citizen.id,
                                         PasswordReset.created_at > now - timedelta(hours=1))
              .order_by(PasswordReset.created_at.desc()).all())
    if len(recent) >= RESET_MAX_PER_HOUR:
        return jsonify({"error": "Too many codes have been requested. Please try again in an hour."}), 429
    if recent and (now - recent[0].created_at).total_seconds() < RESET_RESEND_SECONDS:
        wait = RESET_RESEND_SECONDS - int((now - recent[0].created_at).total_seconds())
        return jsonify({"error": f"Please wait {wait} seconds before asking for another code.", "retry_after": wait}), 429

    code = f"{secrets.randbelow(10 ** 6):06d}"
    message = (f"Your PlanetWatch password reset code is {code}. "
               f"It expires in {RESET_CODE_MINUTES} minutes. Don't share it with anyone.")
    try:
        sent = send_sms_alert(message, sms_number(citizen.phone))
    except Exception as exc:  # phone gateway unreachable, or the SMS service rejected the request
        current_app.logger.error("Reset code SMS to citizen %s failed: %s", citizen.id, exc)
        return jsonify({"error": "We couldn't send the code right now. Please try again in a few minutes."}), 502

    dev_console = False
    if not sent:
        if not current_app.debug:
            return jsonify({"error": "Text messages aren't set up on this server yet, so a reset code can't be sent."}), 503
        # Local development without Twilio: the code goes to the server window only.
        print(f"\n  [forgot password] code for {citizen.full_name}: {code}\n", flush=True)
        dev_console = True

    db.session.add(PasswordReset(citizen_id=citizen.id, code_hash=PasswordReset.hash_code(code),
                                 created_at=now, expires_at=now + timedelta(minutes=RESET_CODE_MINUTES)))
    db.session.commit()
    return jsonify({"phone": _masked_phone(citizen.phone), "expires_in": RESET_CODE_MINUTES * 60,
                    "resend_after": RESET_RESEND_SECONDS, "dev_console": dev_console})


@api.post("/auth/reset")
def reset_password():
    data = _payload()
    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    code = "".join(c for c in str(data.get("code") or "") if c.isdigit())
    password = _password(data)
    problem = _password_problem(password)
    if problem:
        return jsonify({"error": problem}), 400

    citizen = _find_citizen(name, surname) if name and surname else None
    # Only the newest code counts; asking for a new one cancels the old.
    reset = (PasswordReset.query.filter_by(citizen_id=citizen.id).order_by(PasswordReset.created_at.desc()).first()
             if citizen else None)
    if not reset or reset.expires_at < datetime.utcnow():
        return jsonify({"error": "This code has expired. Please ask for a new one."}), 400
    if reset.attempts >= RESET_MAX_ATTEMPTS:
        return jsonify({"error": "Too many wrong codes. Please ask for a new one."}), 429
    if not reset.check_code(code):
        reset.attempts += 1
        db.session.commit()
        left = RESET_MAX_ATTEMPTS - reset.attempts
        return jsonify({"error": "That code is incorrect." + (f" {left} tries left." if left else " Please ask for a new one.")}), 400

    citizen.set_password(password)
    PasswordReset.query.filter_by(citizen_id=citizen.id).delete()
    db.session.commit()
    return _auth_response(citizen)


AVATAR_SIZE = 320


def _save_avatar(upload) -> str:
    """Square-crop and re-encode a profile photo; returns its path under uploads/.

    Re-encoding also drops the original's EXIF, so a phone photo's GPS isn't published.
    """
    image = ImageOps.exif_transpose(Image.open(upload.stream)).convert("RGB")
    image = ImageOps.fit(image, (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    filename = f"avatar-{uuid.uuid4().hex}.jpg"
    image.save(Path(current_app.config["UPLOAD_DIR"]) / filename, "JPEG", quality=88)
    return f"uploads/{filename}"


def _delete_upload(path: str | None) -> None:
    if path:
        (Path(current_app.config["UPLOAD_DIR"]) / Path(path).name).unlink(missing_ok=True)


@api.put("/me")
@citizen_required
def update_me():
    """Update profile details and/or photo (JSON or multipart). Needs the current password."""
    data = _payload()
    citizen = g.citizen
    if citizen.has_password:
        if not citizen.check_password(_password(data, "current_password")):
            return jsonify({"error": "Your current password is incorrect."}), 403
    else:
        # Account from before passwords existed: saving the profile sets one.
        new_password = _password(data, "new_password")
        problem = _password_problem(new_password)
        if problem:
            return jsonify({"error": problem}), 400
        citizen.set_password(new_password)

    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not surname or not phone:
        return jsonify({"error": "Please fill in your name, surname, and phone number."}), 400
    other = _find_citizen(name, surname)
    if other and other.id != citizen.id:
        return jsonify({"error": "Another account already uses this name and surname."}), 409

    photo = request.files.get("photo")
    old_photo = citizen.photo_path
    if photo and photo.filename:
        try:
            citizen.photo_path = _save_avatar(photo)
        except (UnidentifiedImageError, OSError):
            return jsonify({"error": "That profile photo couldn't be read. Please choose a JPG or PNG image."}), 400
    elif data.get("remove_photo") in ("1", "true", True):
        citizen.photo_path = None

    citizen.name = name
    citizen.surname = surname
    citizen.phone = phone
    citizen.address = (data.get("address") or "").strip()
    db.session.commit()
    if old_photo != citizen.photo_path:
        _delete_upload(old_photo)
    return jsonify({"citizen": citizen.to_dict()})


@api.get("/me/reports")
@citizen_required
def my_reports():
    reports = (
        Report.query.filter_by(citizen_id=g.citizen.id)
        .order_by(Report.submitted_at.desc())
        .all()
    )
    return jsonify({"reports": [r.to_dict() for r in reports]})


@api.get("/reports")
def all_reports():
    reports = Report.query.filter(Report.latitude.isnot(None)).all()
    return jsonify({
        "type": "FeatureCollection",
        "features": [r.to_geojson_feature() for r in reports],
    })


def _detect(image_path: Path) -> list[dict] | None:
    """YOLO detections for one photo, or None if the model can't be loaded."""
    # Imported lazily so the API boots (and serves maps, auth, etc.) in a few
    # hundred ms instead of waiting on torch/ultralytics to import.
    try:
        from model.inference import load_model, run_inference
    except ImportError as exc:
        current_app.logger.error("Waste check unavailable, model package missing: %s", exc)
        return None

    weights_path = os.environ.get("YOLO_WEIGHTS", "model/weights/best.pt")
    try:
        model = load_model(weights_path)
    except FileNotFoundError as exc:
        current_app.logger.error("Waste check unavailable: %s", exc)
        return None
    conf = float(os.environ.get("YOLO_CONF_THRESHOLD", "0.25"))

    # Optional second model: names the type of each detected pile. Until it has been
    # trained (model/weights/waste_type.pt) reports keep the detector's plain "waste".
    type_model = None
    type_weights = os.environ.get("WASTE_TYPE_WEIGHTS", "model/weights/waste_type.pt")
    try:
        type_model = load_model(type_weights)
    except FileNotFoundError:
        pass
    type_conf = float(os.environ.get("WASTE_TYPE_CONF_THRESHOLD", "0.40"))
    return run_inference(model, str(image_path), conf=conf, type_model=type_model, type_conf=type_conf)


@api.post("/reports")
@citizen_required
def create_reports():
    """Accept one or more photos taken at the citizen's current (pinned) location.

    Every photo becomes its own report pinned where it was taken, so each gets
    its own YOLO detections and its own status on the municipal dashboard.
    """
    photos = [p for p in request.files.getlist("photos") + request.files.getlist("photo") if p and p.filename]
    if not photos:
        return jsonify({"error": "Please take or choose at least one photo to upload."}), 400

    for photo in photos:
        if Path(photo.filename).suffix.lower() not in IMAGE_EXTENSIONS:
            return jsonify({"error": f"Unsupported file type: {photo.filename}"}), 400

    # One latitude/longitude pair per photo (the spot pinned when it was taken);
    # a single pair applies to every photo.
    latitudes = [_parse_float(v) for v in request.form.getlist("latitude")]
    longitudes = [_parse_float(v) for v in request.form.getlist("longitude")]
    # Capture time per photo for camera shots ("YYYY:MM:DD HH:MM:SS", EXIF format);
    # EXIF DateTimeOriginal in the photo itself takes precedence.
    captured_ats = [v.strip() for v in request.form.getlist("captured_at")]

    def pinned_location(index: int):
        if not latitudes or not longitudes:
            return None, None
        i = index if index < min(len(latitudes), len(longitudes)) else 0
        return latitudes[i], longitudes[i]

    contact = (request.form.get("contact") or "").strip() or None
    upload_dir = Path(current_app.config["UPLOAD_DIR"])

    created = []
    rejected = []  # filenames of photos with no waste detected
    saved_paths = []
    for index, photo in enumerate(photos):
        suffix = Path(photo.filename).suffix.lower()
        filename = f"{uuid.uuid4().hex}{suffix}"
        saved_path = upload_dir / filename
        photo.save(saved_path)
        saved_paths.append(saved_path)

        try:
            metadata = extract_gps_and_timestamp(str(saved_path))
        except (UnidentifiedImageError, OSError):
            db.session.rollback()
            for path in saved_paths:
                path.unlink(missing_ok=True)
            return jsonify({"error": f"Couldn't read {photo.filename} as an image."}), 400
        captured_at = None
        if metadata["timestamp"]:
            try:
                captured_at = datetime.fromisoformat(metadata["timestamp"])
            except ValueError:
                captured_at = None
        if captured_at is None and index < len(captured_ats) and captured_ats[index]:
            # Native-camera shots whose EXIF was stripped: the time the app recorded the shot.
            try:
                captured_at = datetime.strptime(captured_ats[index], "%Y:%m:%d %H:%M:%S")
            except ValueError:
                captured_at = None

        # The location pinned on the report page is authoritative; EXIF GPS is
        # only a fallback for a gallery photo submitted without a live fix.
        pinned_lat, pinned_lng = pinned_location(index)
        latitude = pinned_lat if pinned_lat is not None else metadata["latitude"]
        longitude = pinned_lng if pinned_lng is not None else metadata["longitude"]
        if latitude is None or longitude is None:
            db.session.rollback()
            for path in saved_paths:
                path.unlink(missing_ok=True)
            return jsonify({"error": "Your location is required. Switch on location and try again."}), 400

        # Only photos the model recognises as waste become reports; the rest are
        # deleted and never reach the map.
        detections = _detect(saved_path)
        if detections is None:
            db.session.rollback()
            for path in saved_paths:
                path.unlink(missing_ok=True)
            return jsonify({"error": "The waste check is unavailable right now. Please try again later."}), 503
        if not detections:
            saved_path.unlink(missing_ok=True)
            saved_paths.remove(saved_path)
            rejected.append(photo.filename)
            continue

        report = Report(
            citizen_id=g.citizen.id,
            image_path=f"uploads/{filename}",
            latitude=latitude,
            longitude=longitude,
            captured_at=captured_at,
            reporter_contact=contact,
        )
        db.session.add(report)
        db.session.flush()  # assigns report.id before we attach detections

        for detection in detections:
            db.session.add(Detection(
                report_id=report.id,
                waste_type=detection["class_name"],
                confidence=detection["confidence"],
                type_confidence=detection.get("type_confidence"),
                bbox_x1=detection["bbox"][0],
                bbox_y1=detection["bbox"][1],
                bbox_x2=detection["bbox"][2],
                bbox_y2=detection["bbox"][3],
            ))
        created.append((report, detections))

    if not created:
        db.session.rollback()
        message = ("No waste was detected in this photo, so it wasn't submitted." if len(rejected) == 1
                   else "No waste was detected in any of these photos, so they weren't submitted.")
        return jsonify({"error": message, "rejected": rejected}), 422

    db.session.commit()

    for report, detections in created:
        notify_new_report(report, detections)

    return jsonify({"reports": [report.to_dict() for report, _ in created], "rejected": rejected}), 201
