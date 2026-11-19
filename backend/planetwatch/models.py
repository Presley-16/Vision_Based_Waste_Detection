"""Database models for citizen reports and YOLO detections."""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from model.waste_types import type_label  # plain dict + function, no torch import

db = SQLAlchemy()


class Citizen(db.Model):
    __tablename__ = "citizens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(30), nullable=False)
    # Salted scrypt hash, never the password itself. Empty for accounts made
    # before passwords existed; signing up again with the same name sets one.
    password_hash = db.Column(db.String(255), nullable=True)
    photo_path = db.Column(db.String(255), nullable=True)  # optional profile photo in uploads/
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reports = db.relationship("Report", backref="citizen")

    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return self.has_password and check_password_hash(self.password_hash, password)

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}".strip()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "address": self.address or "",
            "phone": self.phone,
            "photo_url": f"/{self.photo_path}" if self.photo_path else None,
            "has_password": self.has_password,
            "member_since": self.created_at.isoformat() if self.created_at else None,
        }


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

    @property
    def waste_types(self) -> list[str]:
        """Readable labels of the types in this report, e.g. ["Construction rubble", "Plastic"]."""
        return sorted({type_label(d.waste_type) for d in self.detections})

    def to_dict(self, include_reporter: bool = False) -> dict:
        """Public report shape; `include_reporter` adds uploader contact details for municipal staff."""
        data = {
            "id": self.id,
            "image_url": f"/{self.image_path}",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "submitted_at": self.submitted_at.isoformat(),
            "status": self.status,
            "waste_types": self.waste_types,
            "detections": [
                {"waste_type": type_label(d.waste_type), "type": d.waste_type,
                 "confidence": d.confidence, "type_confidence": d.type_confidence}
                for d in self.detections
            ],
        }
        if include_reporter:
            data["reporter"] = {
                "name": self.citizen.full_name if self.citizen else None,
                "phone": self.citizen.phone if self.citizen else None,
                "address": self.citizen.address if self.citizen else None,
                "contact": self.reporter_contact,
            }
        return data

    def to_geojson_feature(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [self.longitude, self.latitude]},
            "properties": {
                "id": self.id,
                "image_path": self.image_path,
                "image_url": f"/{self.image_path}",
                "captured_at": self.captured_at.isoformat() if self.captured_at else None,
                "submitted_at": self.submitted_at.isoformat(),
                "status": self.status,
                "waste_types": self.waste_types,
            },
        }


class Detection(db.Model):
    __tablename__ = "detections"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    waste_type = db.Column(db.String(50), nullable=False)  # a model.waste_types name, or "waste" before the classifier
    confidence = db.Column(db.Float, nullable=False)  # detector: how sure this is waste
    type_confidence = db.Column(db.Float, nullable=True)  # classifier: how sure of waste_type (None before it existed)
    bbox_x1 = db.Column(db.Float, nullable=False)
    bbox_y1 = db.Column(db.Float, nullable=False)
    bbox_x2 = db.Column(db.Float, nullable=False)
    bbox_y2 = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PasswordReset(db.Model):
    """A one-time code texted to a citizen's phone to reset a forgotten password."""
    __tablename__ = "password_resets"

    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey("citizens.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)  # hashed like a password
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)

    def check_code(self, code: str) -> bool:
        return check_password_hash(self.code_hash, code)

    @staticmethod
    def hash_code(code: str) -> str:
        return generate_password_hash(code)
