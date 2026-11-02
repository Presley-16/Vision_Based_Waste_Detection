"""Citizen-facing JSON API used by both the website (frontend/) and the mobile app (mobile/)."""
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request
from PIL import UnidentifiedImageError

from model.exif_extract import IMAGE_EXTENSIONS, extract_gps_and_timestamp

from .alerts import notify_new_report
from .auth import citizen_required, issue_citizen_token
from .models import Citizen, Detection, Report, db

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


@api.post("/auth/signin")
def signin():
    # Sign In is intentionally lenient: whatever is typed gets you in,
    # matching an existing citizen if one exists or creating a minimal
    # one on the fly so every visit is still tracked in the database.
    data = _payload()
    name = (data.get("name") or "").strip() or "Guest"
    surname = (data.get("surname") or "").strip() or "Citizen"

    citizen = _find_citizen(name, surname)
    if not citizen:
        citizen = Citizen(name=name, surname=surname, address="", phone="")
        db.session.add(citizen)
        db.session.commit()
    return _auth_response(citizen)


@api.post("/auth/signup")
def signup():
    data = _payload()
    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    address = (data.get("address") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not name or not surname or not phone:
        return jsonify({"error": "Please fill in your name, surname, and phone number."}), 400

    citizen = _find_citizen(name, surname)
    if citizen:
        citizen.phone = phone
        citizen.address = address or citizen.address
    else:
        citizen = Citizen(name=name, surname=surname, address=address, phone=phone)
        db.session.add(citizen)
    db.session.commit()
    return _auth_response(citizen)


@api.get("/me")
@citizen_required
def me():
    return jsonify({"citizen": g.citizen.to_dict()})


@api.put("/me")
@citizen_required
def update_me():
    data = _payload()
    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not surname or not phone:
        return jsonify({"error": "Please fill in your name, surname, and phone number."}), 400

    g.citizen.name = name
    g.citizen.surname = surname
    g.citizen.phone = phone
    g.citizen.address = (data.get("address") or "").strip()
    db.session.commit()
    return jsonify({"citizen": g.citizen.to_dict()})


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


def _detect(image_path: Path) -> list[dict]:
    # Imported lazily so the API boots (and serves maps, auth, etc.) in a few
    # hundred ms instead of waiting on torch/ultralytics to import.
    try:
        from model.inference import load_model, run_inference
    except ImportError as exc:
        current_app.logger.warning("Inference skipped, model package unavailable: %s", exc)
        return []

    weights_path = os.environ.get("YOLO_WEIGHTS", "model/weights/best.pt")
    try:
        model = load_model(weights_path)
    except FileNotFoundError as exc:
        current_app.logger.warning("Inference skipped: %s", exc)
        return []
    conf = float(os.environ.get("YOLO_CONF_THRESHOLD", "0.25"))
    return run_inference(model, str(image_path), conf=conf)


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

    def pinned_location(index: int):
        if not latitudes or not longitudes:
            return None, None
        i = index if index < min(len(latitudes), len(longitudes)) else 0
        return latitudes[i], longitudes[i]

    contact = (request.form.get("contact") or "").strip() or None
    upload_dir = Path(current_app.config["UPLOAD_DIR"])

    created = []
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

        detections = _detect(saved_path)
        for detection in detections:
            db.session.add(Detection(
                report_id=report.id,
                waste_type=detection["class_name"],
                confidence=detection["confidence"],
                bbox_x1=detection["bbox"][0],
                bbox_y1=detection["bbox"][1],
                bbox_x2=detection["bbox"][2],
                bbox_y2=detection["bbox"][3],
            ))
        created.append((report, detections))

    db.session.commit()

    for report, detections in created:
        if detections:
            notify_new_report(report, detections)

    return jsonify({"reports": [report.to_dict() for report, _ in created]}), 201
