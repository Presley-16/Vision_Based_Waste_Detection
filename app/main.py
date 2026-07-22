"""Flask app entry point — serves the GIS dashboard and citizen reporting site."""
import os
import uuid
from datetime import datetime
from pathlib import Path

import folium
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from app.alerts import notify_new_report  # noqa: E402
from app.inference import load_model, run_inference  # noqa: E402
from app.models import Detection, Report, db  # noqa: E402
from scripts.exif_extract import IMAGE_EXTENSIONS, extract_gps_and_timestamp  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
HARARE = [-17.8252, 31.0335]


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///reports.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def build_dumping_map(reports: list[Report]) -> folium.Map:
    """Render a Folium map with one marker per report, colored by review status."""
    if reports:
        center = [
            sum(r.latitude for r in reports) / len(reports),
            sum(r.longitude for r in reports) / len(reports),
        ]
    else:
        center = HARARE

    fmap = folium.Map(location=center, zoom_start=12)
    status_colors = {"pending": "orange", "reviewed": "blue", "resolved": "green"}

    for report in reports:
        waste_types = ", ".join(sorted({d.waste_type for d in report.detections})) or "unclassified"
        popup_html = (
            f"<b>Report #{report.id}</b><br>"
            f"Waste: {waste_types}<br>"
            f"Status: {report.status}<br>"
            f"Submitted: {report.submitted_at.isoformat()}"
        )
        folium.Marker(
            location=[report.latitude, report.longitude],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color=status_colors.get(report.status, "gray"), icon="trash", prefix="fa"),
        ).add_to(fmap)

    return fmap


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        return render_template("index.html", active_page="home")

    @app.route("/report", methods=["GET", "POST"])
    def report():
        if request.method == "GET":
            return render_template("upload.html", active_page="report")

        photo = request.files.get("photo")
        if not photo or not photo.filename:
            return render_template("upload.html", active_page="report", error="Please choose a photo to upload."), 400

        suffix = Path(photo.filename).suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            return render_template("upload.html", active_page="report", error="Unsupported file type."), 400

        filename = f"{uuid.uuid4().hex}{suffix}"
        saved_path = UPLOAD_DIR / filename
        photo.save(saved_path)

        metadata = extract_gps_and_timestamp(str(saved_path))
        captured_at = None
        if metadata["timestamp"]:
            try:
                captured_at = datetime.fromisoformat(metadata["timestamp"])
            except ValueError:
                captured_at = None

        # Browser-submitted coordinates (Geolocation API) take priority over EXIF:
        # citizen uploads often lack EXIF GPS since browsers strip metadata or the
        # photo never touched a file with EXIF at all. EXIF is the fallback for
        # reports submitted from a gallery photo that happens to carry it.
        latitude = _parse_float(request.form.get("latitude")) or metadata["latitude"]
        longitude = _parse_float(request.form.get("longitude")) or metadata["longitude"]

        new_report = Report(
            image_path=f"uploads/{filename}",
            latitude=latitude,
            longitude=longitude,
            captured_at=captured_at,
            reporter_contact=request.form.get("contact") or None,
        )
        db.session.add(new_report)
        db.session.flush()  # assigns new_report.id before we attach detections

        detections = []
        weights_path = os.environ.get("YOLO_WEIGHTS", "models/best.pt")
        try:
            model = load_model(weights_path)
            conf = float(os.environ.get("YOLO_CONF_THRESHOLD", "0.25"))
            detections = run_inference(model, str(saved_path), conf=conf)
        except FileNotFoundError as exc:
            app.logger.warning("Inference skipped: %s", exc)

        for detection in detections:
            db.session.add(Detection(
                report_id=new_report.id,
                waste_type=detection["class_name"],
                confidence=detection["confidence"],
                bbox_x1=detection["bbox"][0],
                bbox_y1=detection["bbox"][1],
                bbox_x2=detection["bbox"][2],
                bbox_y2=detection["bbox"][3],
            ))

        db.session.commit()

        if new_report.latitude is not None and detections:
            notify_new_report(new_report, detections)

        return render_template("upload.html", active_page="report", success=True, detections=detections)

    @app.route("/map")
    def map_view():
        reports = Report.query.filter(Report.latitude.isnot(None)).all()
        fmap = build_dumping_map(reports)
        return render_template(
            "map.html",
            active_page="map",
            map_html=fmap.get_root().render(),
            report_count=len(reports),
        )

    @app.route("/api/reports")
    def api_reports():
        reports = Report.query.filter(Report.latitude.isnot(None)).all()
        return jsonify({
            "type": "FeatureCollection",
            "features": [r.to_geojson_feature() for r in reports],
        })


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
