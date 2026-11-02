"""Municipal monitoring API: view every pinned report, change its status, delete it.

"Solved" on the dashboard maps to the existing `resolved` status; "Pending"
covers everything not yet solved (`pending` and the legacy `reviewed`).
"""
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request

from .auth import check_municipal_login, issue_municipal_token, municipal_required
from .models import Report, db

municipal = Blueprint("municipal", __name__, url_prefix="/api/municipal")

SOLVED = "resolved"
ALLOWED_STATUSES = {"pending", "reviewed", SOLVED}


@municipal.post("/login")
def login():
    data = request.get_json(silent=True) or request.form.to_dict()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not check_municipal_login(username, password):
        return jsonify({"error": "Incorrect username or password."}), 401
    return jsonify({"token": issue_municipal_token(username), "user": username})


@municipal.get("/me")
@municipal_required
def me():
    return jsonify({"user": g.municipal_user})


@municipal.get("/reports")
@municipal_required
def list_reports():
    status_filter = request.args.get("status", "all")
    query = Report.query.filter(Report.latitude.isnot(None))
    if status_filter == "solved":
        query = query.filter(Report.status == SOLVED)
    elif status_filter == "pending":
        query = query.filter(Report.status != SOLVED)

    reports = query.order_by(Report.submitted_at.desc()).all()

    all_statuses = [status for (status,) in db.session.query(Report.status).filter(Report.latitude.isnot(None))]
    solved_count = sum(1 for status in all_statuses if status == SOLVED)
    return jsonify({
        "reports": [r.to_dict(include_reporter=True) for r in reports],
        "counts": {
            "all": len(all_statuses),
            "pending": len(all_statuses) - solved_count,
            "solved": solved_count,
        },
    })


@municipal.patch("/reports/<int:report_id>")
@municipal_required
def update_report(report_id: int):
    report = db.get_or_404(Report, report_id)
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status == "solved":
        status = SOLVED
    if status not in ALLOWED_STATUSES:
        return jsonify({"error": f"Unknown status: {status}"}), 400
    report.status = status
    db.session.commit()
    return jsonify({"report": report.to_dict(include_reporter=True)})


@municipal.delete("/reports/<int:report_id>")
@municipal_required
def delete_report(report_id: int):
    report = db.get_or_404(Report, report_id)
    image_file = Path(current_app.config["UPLOAD_DIR"]) / Path(report.image_path).name
    db.session.delete(report)
    db.session.commit()
    image_file.unlink(missing_ok=True)
    return jsonify({"deleted": report_id})
