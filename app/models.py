"""Database models for citizen reports and YOLO detections."""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Citizen(db.Model):
    __tablename__ = "citizens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reports = db.relationship("Report", backref="citizen")

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}".strip()


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey("citizens.id"), nullable=True)
    image_path = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    captured_at = db.Column(db.DateTime, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reporter_contact = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)

    detections = db.relationship("Detection", backref="report", cascade="all, delete-orphan")

    def to_geojson_feature(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [self.longitude, self.latitude]},
            "properties": {
                "id": self.id,
                "image_path": self.image_path,
                "captured_at": self.captured_at.isoformat() if self.captured_at else None,
                "submitted_at": self.submitted_at.isoformat(),
                "status": self.status,
                "waste_types": [d.waste_type for d in self.detections],
            },
        }


class Detection(db.Model):
    __tablename__ = "detections"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    waste_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    bbox_x1 = db.Column(db.Float, nullable=False)
    bbox_y1 = db.Column(db.Float, nullable=False)
    bbox_x2 = db.Column(db.Float, nullable=False)
    bbox_y2 = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
