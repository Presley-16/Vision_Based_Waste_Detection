"""Shared YOLOv11 inference logic used by dataset scripts and the live website.

Kept provider-agnostic about the weights file: pass the trained `models/best.pt`
once it exists, or a stock `yolo11n.pt` in the meantime so the rest of the
pipeline (Flask routes, detect.py) can be built and tested before the
Zimbabwe-specific dataset is ready.
"""
from pathlib import Path

from ultralytics import YOLO

_model_cache: dict[str, YOLO] = {}


def load_model(weights_path: str) -> YOLO:
    """Load (and cache) a YOLO model from `weights_path`."""
    weights_path = str(weights_path)
    if weights_path not in _model_cache:
        if not Path(weights_path).exists():
            raise FileNotFoundError(
                f"Weights file not found: {weights_path}. "
                "Train a model with scripts/train.py, or point YOLO_WEIGHTS "
                "at a stock checkpoint such as yolo11n.pt in the meantime."
            )
        _model_cache[weights_path] = YOLO(weights_path)
    return _model_cache[weights_path]


def run_inference(model: YOLO, image_path: str, conf: float = 0.25) -> list[dict]:
    """Run detection on a single image, return a list of detection dicts.

    Each dict has: class_name, confidence, bbox ([x1, y1, x2, y2] in pixels).
    """
    results = model.predict(source=image_path, conf=conf, verbose=False)
    detections = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls.item())
            detections.append({
                "class_name": result.names[class_id],
                "confidence": round(float(box.conf.item()), 4),
                "bbox": [round(v, 1) for v in box.xyxy[0].tolist()],
            })
    return detections


def save_annotated_image(model: YOLO, image_path: str, output_path: str, conf: float = 0.25) -> str:
    """Run detection and save an annotated copy of the image with boxes drawn."""
    results = model.predict(source=image_path, conf=conf, verbose=False)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results[0].save(filename=str(output_path))
    return str(output_path)
