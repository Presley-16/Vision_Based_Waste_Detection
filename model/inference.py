"""Shared YOLOv11 inference logic used by dataset scripts and the live website.

Kept provider-agnostic about the weights file: pass the trained
`model/weights/best.pt` once it exists, or a stock `yolo11n.pt` in the meantime
so the rest of the pipeline (backend API, detect.py) can be built and tested
before the Zimbabwe-specific dataset is ready.
"""
import threading
from pathlib import Path

from ultralytics import YOLO

WEIGHTS_DIR = Path(__file__).resolve().parent / "weights"

_model_cache: dict[str, YOLO] = {}
# The server answers requests on several threads that share one model, and
# YOLO models aren't thread-safe, so loading and predicting go one at a time.
_lock = threading.Lock()


def resolve_weights(weights_path: str) -> Path:
    """Resolve a weights path that may be relative to the cwd, the repo root, or model/weights/.

    YOLO_WEIGHTS values written before the repo was split (e.g. `models/best.pt`)
    keep working because the bare filename is also looked up in model/weights/.
    """
    path = Path(weights_path)
    candidates = [path, Path(__file__).resolve().parent.parent / path, WEIGHTS_DIR / path.name]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def load_model(weights_path: str) -> YOLO:
    """Load (and cache) a YOLO model from `weights_path`."""
    weights_path = str(resolve_weights(weights_path))
    with _lock:
        if weights_path not in _model_cache:
            if not Path(weights_path).exists():
                raise FileNotFoundError(
                    f"Weights file not found: {weights_path}. "
                    "Train a model with model/train.py, or point YOLO_WEIGHTS "
                    "at a stock checkpoint such as yolo11n.pt in the meantime."
                )
            _model_cache[weights_path] = YOLO(weights_path)
        return _model_cache[weights_path]


def run_inference(model: YOLO, image_path: str, conf: float = 0.25,
                  type_model: YOLO | None = None, type_conf: float = 0.40) -> list[dict]:
    """Run detection on a single image, return a list of detection dicts.

    Each dict has: class_name, confidence, bbox ([x1, y1, x2, y2] in pixels).

    With `type_model` (the waste-type classifier), each box is cropped the same way the
    training crops were and classified: class_name becomes the waste type, or
    "unclassified" below `type_conf`, and type_confidence is added. Without it the
    detector's own class (`waste`) is kept.
    """
    with _lock:
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
    if type_model is not None and detections:
        classify_types(type_model, image_path, detections, type_conf)
    return detections


def classify_types(type_model: YOLO, image_path: str, detections: list[dict], type_conf: float) -> None:
    """Fill in class_name / type_confidence for each detection from the waste-type classifier."""
    from PIL import Image, ImageOps

    from model.crop_detections import crop_box
    from model.waste_types import UNCLASSIFIED

    with Image.open(image_path) as im:
        image = ImageOps.exif_transpose(im).convert("RGB")
    crops = [crop_box(image, tuple(d["bbox"]), 0.10) for d in detections]
    with _lock:
        results = type_model.predict(source=crops, verbose=False)
    for detection, result in zip(detections, results):
        confidence = float(result.probs.top1conf)
        detection["type_confidence"] = round(confidence, 4)
        detection["class_name"] = result.names[result.probs.top1] if confidence >= type_conf else UNCLASSIFIED


def save_annotated_image(model: YOLO, image_path: str, output_path: str, conf: float = 0.25) -> str:
    """Run detection and save an annotated copy of the image with boxes drawn."""
    with _lock:
        results = model.predict(source=image_path, conf=conf, verbose=False)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results[0].save(filename=str(output_path))
    return str(output_path)
