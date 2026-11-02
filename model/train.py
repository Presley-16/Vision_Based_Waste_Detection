"""Train YOLOv11 on the annotated Roboflow dataset.

Expects a Roboflow-exported YOLO dataset at `model/dataset/data.yaml` (see
https://roboflow.com export options: choose "YOLO11"). Until that export is
in place this will fail fast with a clear message rather than a confusing
ultralytics stack trace.
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

MODEL_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(MODEL_DIR / "dataset" / "data.yaml"), help="Path to Roboflow data.yaml")
    parser.add_argument("--base-weights", default=str(MODEL_DIR / "weights" / "yolo11n.pt"), help="Pretrained checkpoint to fine-tune from")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--project", default=str(MODEL_DIR / "runs" / "detect"), help="Where ultralytics writes run artifacts")
    parser.add_argument("--name", default="waste_yolov11", help="Run name")
    parser.add_argument("--models-dir", default=str(MODEL_DIR / "weights"), help="Where to copy the resulting best.pt")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(
            f"{data_path} not found. Export your annotated dataset from Roboflow "
            "in YOLO11 format and place it at this path before training."
        )

    model = YOLO(args.base_weights)
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
    )

    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    if best_weights.exists():
        models_dir = Path(args.models_dir)
        models_dir.mkdir(parents=True, exist_ok=True)
        destination = models_dir / "best.pt"
        shutil.copy(best_weights, destination)
        print(f"Copied best weights to {destination}")


if __name__ == "__main__":
    main()
