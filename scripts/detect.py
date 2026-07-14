"""Run YOLOv11 inference on an image or directory of images.

Combines detection with EXIF-derived GPS/timestamp so a single command turns
a folder of raw smartphone photos into ready-to-map JSON records, ahead of
that logic being wired into the live Flask reporting site.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.inference import load_model, run_inference, save_annotated_image  # noqa: E402
from scripts.exif_extract import IMAGE_EXTENSIONS, extract_gps_and_timestamp  # noqa: E402


def iter_image_paths(source: Path):
    if source.is_file():
        yield source
    else:
        for path in sorted(source.rglob("*")):
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Image file or directory to run detection on")
    parser.add_argument("--weights", default="models/best.pt", help="Path to trained weights")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--out-dir", default="runs/predict", help="Where to save annotated images + results.json")
    args = parser.parse_args()

    model = load_model(args.weights)
    source = Path(args.source)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for image_path in iter_image_paths(source):
        detections = run_inference(model, str(image_path), conf=args.conf)
        metadata = extract_gps_and_timestamp(str(image_path))
        annotated_path = save_annotated_image(model, str(image_path), out_dir / image_path.name, conf=args.conf)

        records.append({
            "filename": str(image_path),
            "annotated_path": annotated_path,
            **metadata,
            "detections": detections,
        })
        print(f"{image_path}: {len(detections)} detection(s)")

    results_path = out_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Wrote {len(records)} record(s) to {results_path}")


if __name__ == "__main__":
    main()
