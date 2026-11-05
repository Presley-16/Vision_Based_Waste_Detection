"""Train YOLOv11 on the annotated Roboflow dataset.

Trains on the merged single-class dataset at `model/datasets/PlanetWatch/data.yaml`,
built by `python -m model.build_dataset` from our own Roboflow-labelled photos plus
the downloaded dumping datasets. Fails fast with a clear message if it's missing.
"""
import argparse
import shutil
from pathlib import Path

import torch
from ultralytics import YOLO

MODEL_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(MODEL_DIR / "datasets" / "PlanetWatch" / "data.yaml"), help="YOLO data.yaml (default: the merged PlanetWatch dataset)")
    parser.add_argument("--base-weights", default=str(MODEL_DIR / "weights" / "yolo11s.pt"),
                        help="Pretrained checkpoint to fine-tune from (yolo11s: good accuracy, fits 8GB VRAM)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--patience", type=int, default=30, help="Stop early after this many epochs without improvement")
    parser.add_argument("--workers", type=int, default=4, help="Data-loading processes")
    parser.add_argument("--device", default=None, help="'0' for the first GPU, 'cpu' to force CPU (default: GPU if available)")
    parser.add_argument("--project", default=str(MODEL_DIR / "runs" / "detect"), help="Where ultralytics writes run artifacts")
    parser.add_argument("--name", default="waste_yolov11", help="Run name")
    parser.add_argument("--models-dir", default=str(MODEL_DIR / "weights"), help="Where to copy the resulting best.pt")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(
            f"{data_path} not found. Build it with `python -m model.build_dataset` "
            "(or pass --data to another YOLO data.yaml)."
        )

    device = args.device or ("0" if torch.cuda.is_available() else "cpu")
    if device == "cpu":
        print("WARNING: training on the CPU — this will be very slow. Install the CUDA build of PyTorch:\n"
              "  pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu130")
    else:
        print(f"Training on GPU: {torch.cuda.get_device_name(int(device))}")

    model = YOLO(args.base_weights)
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        workers=args.workers,
        device=device,
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

        # Score the final model on the held-out test photos (includes our own Zimbabwe photos).
        metrics = YOLO(str(best_weights)).val(data=str(data_path), split="test", device=device, plots=False)
        print(f"\nTest set: mAP50={metrics.box.map50:.3f}  mAP50-95={metrics.box.map:.3f}  "
              f"precision={metrics.box.mp:.3f}  recall={metrics.box.mr:.3f}")
        print("Restart the backend (python backend/run.py) so uploads use the new model.")


if __name__ == "__main__":
    main()
