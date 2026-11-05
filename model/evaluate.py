"""Score a trained model: box-level mAP and photo-level accuracy, overall and per source.

    python -m model.evaluate                          # model/weights/best.pt on the test split
    python -m model.evaluate --weights model/weights/best_v1_map40.pt --split valid

Photo-level accuracy answers the question the app actually asks: "does this photo
contain dumped waste?" A photo counts as detected when any box reaches --conf (the
backend's YOLO_CONF_THRESHOLD, default 0.25).
"""
import argparse
import collections
from pathlib import Path

from ultralytics import YOLO

MODEL_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = MODEL_DIR / "datasets" / "PlanetWatch"


def photo_level(model: YOLO, images: list[Path], conf: float) -> dict:
    tp = fp = tn = fn = 0
    for start in range(0, len(images), 16):
        batch = images[start:start + 16]
        for image, result in zip(batch, model.predict([str(p) for p in batch], conf=conf, verbose=False)):
            label = image.parent.parent / "labels" / (image.stem + ".txt")
            has_waste = label.exists() and label.read_text().strip() != ""
            detected = len(result.boxes) > 0
            tp += has_waste and detected
            fn += has_waste and not detected
            fp += detected and not has_waste
            tn += not detected and not has_waste
    total = tp + fp + tn + fn
    return {"photos": total, "with_waste": tp + fn, "without_waste": tn + fp, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "accuracy": (tp + tn) / total if total else 0.0}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights", default=str(MODEL_DIR / "weights" / "best.pt"))
    parser.add_argument("--data", default=str(DEFAULT_DATA / "data.yaml"))
    parser.add_argument("--split", default="test", choices=["train", "valid", "test"])
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold for photo-level accuracy")
    parser.add_argument("--sweep", action="store_true", help="Also show the accept/reject trade-off at several thresholds")
    args = parser.parse_args()

    data_root = Path(args.data).parent
    model = YOLO(args.weights)
    metrics = model.val(data=args.data, split="val" if args.split == "valid" else args.split,
                        plots=False, verbose=False, workers=0, project=str(MODEL_DIR / "runs" / "evaluate"), exist_ok=True)

    images = sorted(p for p in (data_root / args.split / "images").iterdir())
    by_source = collections.defaultdict(list)
    for image in images:
        by_source[image.name.split("__")[0]].append(image)

    overall = photo_level(model, images, args.conf)
    print(f"\n=== {Path(args.weights).name} on the {args.split} split ({len(images)} photos) ===")
    print(f"Box level   : mAP50={metrics.box.map50:.3f}  mAP50-95={metrics.box.map:.3f}  "
          f"precision={metrics.box.mp:.3f}  recall={metrics.box.mr:.3f}")
    print(f"Photo level : accuracy={overall['accuracy']:.3f}  "
          f"(waste photos found {overall['tp']}/{overall['with_waste']}, "
          f"clean photos correctly ignored {overall['tn']}/{overall['without_waste']})  conf>={args.conf}")
    print("\nPhoto-level accuracy per source:")
    for source, source_images in sorted(by_source.items()):
        result = photo_level(model, source_images, args.conf)
        print(f"  {source:<28} {result['accuracy']:.3f}  ({result['tp'] + result['tn']}/{result['photos']} photos)")

    if args.sweep:
        # Best score per photo, then the trade-off at each threshold: raising YOLO_CONF_THRESHOLD
        # rejects more non-waste photos but also more real ones.
        scores = []
        for start in range(0, len(images), 16):
            batch = images[start:start + 16]
            for image, result in zip(batch, model.predict([str(p) for p in batch], conf=0.05, verbose=False)):
                label = image.parent.parent / "labels" / (image.stem + ".txt")
                scores.append((label.read_text().strip() != "", max((float(c) for c in result.boxes.conf), default=0.0)))
        waste = sum(has for has, _ in scores)
        clean = len(scores) - waste
        print("\nThreshold sweep (set the chosen value as YOLO_CONF_THRESHOLD in .env):")
        for threshold in (0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6):
            accepted = sum(1 for has, s in scores if has and s >= threshold)
            wrong = sum(1 for has, s in scores if not has and s >= threshold)
            print(f"  conf>={threshold:.2f}  waste photos accepted {accepted}/{waste} ({accepted / max(waste, 1):.0%})"
                  f"   no-waste photos wrongly accepted {wrong}/{clean} ({wrong / max(clean, 1):.0%})")


if __name__ == "__main__":
    main()
