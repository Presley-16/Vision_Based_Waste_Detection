"""Train the YOLO11 waste-type classifier on model/datasets/WasteTypes.

    python -m model.build_classification --labelled <roboflow export>   # first
    python -m model.train_classifier                                    # -> model/weights/waste_type.pt
    python -m model.train_classifier --no-install                       # keep the current waste_type.pt

Then score it with `python -m model.evaluate_classifier`. The backend picks up
model/weights/waste_type.pt after a restart; without that file reports keep the
detector's plain `waste` label.
"""
import argparse
import shutil
from pathlib import Path

import torch
from ultralytics import YOLO

MODEL_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default=str(MODEL_DIR / "datasets" / "WasteTypes"))
    parser.add_argument("--base-weights", default="yolo11s-cls.pt", help="ImageNet-pretrained classifier to fine-tune")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--device", default=None)
    parser.add_argument("--name", default="waste_type")
    parser.add_argument("--no-install", action="store_true", help="Don't copy the result to model/weights/waste_type.pt")
    args = parser.parse_args()

    data = Path(args.data)
    if not (data / "train").exists():
        raise SystemExit(f"{data} not found. Build it with `python -m model.build_classification --labelled <export>`.")

    base = MODEL_DIR / "weights" / args.base_weights
    model = YOLO(str(base) if base.exists() else args.base_weights)  # downloads the stock checkpoint once
    results = model.train(
        data=str(data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, patience=args.patience,
        device=args.device or ("0" if torch.cuda.is_available() else "cpu"),
        project=str(MODEL_DIR / "runs" / "classify"), name=args.name,
    )
    best = Path(results.save_dir) / "weights" / "best.pt"
    print(f"\nBest weights: {best}")
    if not args.no_install and best.exists():
        destination = MODEL_DIR / "weights" / "waste_type.pt"
        shutil.copy(best, destination)
        print(f"Installed as {destination}. Score it: python -m model.evaluate_classifier")


if __name__ == "__main__":
    main()
