"""Draft waste boxes on new photos so labelling in Roboflow means adjusting, not drawing.

Runs the current detector with a deliberately low threshold, because new photos are
usually of waste the detector is weak on (that's why we're labelling them). Expect
some wrong or loose boxes: fix, add or delete them in Roboflow, never upload as final.

    python -m model.draft_boxes "C:/Users/me/Downloads/Vision Images/Rubble"
    python -m model.draft_boxes <folder> --conf 0.05

Output: model/datasets/to_label/<folder name>/
  images/*.jpg, labels/*.txt (YOLO), data.yaml   drag the whole folder into the
                                                  PlanetWatch Waste project in Roboflow
  draft_report.csv                                boxes and best confidence per photo
  preview/*.jpg                                   the drafts drawn on each photo
"""
import argparse
import csv
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from model.inference import load_model, run_inference

MODEL_DIR = Path(__file__).resolve().parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", help="Folder of new photos")
    parser.add_argument("--weights", default=str(MODEL_DIR / "weights" / "best.pt"))
    parser.add_argument("--conf", type=float, default=0.10, help="Draft threshold (lower than the app's 0.25 on purpose)")
    parser.add_argument("--app-conf", type=float, default=0.25, help="The app's threshold, to report which photos it would reject")
    args = parser.parse_args()

    folder = Path(args.folder)
    out = MODEL_DIR / "datasets" / "to_label" / folder.name
    for sub in ("images", "labels", "preview"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    model = load_model(args.weights)
    rows = []
    for photo in sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS):
        # Roboflow and YOLO read pixels as stored, so bake the EXIF rotation in first.
        with Image.open(photo) as im:
            image = ImageOps.exif_transpose(im).convert("RGB")
        stem = photo.stem.replace(" ", "_").replace("(", "").replace(")", "")
        image_path = out / "images" / f"{stem}.jpg"
        image.save(image_path, "JPEG", quality=95)

        detections = run_inference(model, str(image_path), conf=args.conf)
        width, height = image.size
        lines = []
        preview = image.copy()
        draw = ImageDraw.Draw(preview)
        for d in detections:
            x1, y1, x2, y2 = d["bbox"]
            lines.append(f"0 {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} "
                         f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}")
            draw.rectangle((x1, y1, x2, y2), outline="red", width=max(3, width // 250))
            draw.text((x1 + 6, y1 + 6), f"{d['confidence']:.2f}", fill="red")
        (out / "labels" / f"{stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
        preview.save(out / "preview" / f"{stem}.jpg", "JPEG", quality=80)

        best = max((d["confidence"] for d in detections), default=0.0)
        rows.append({"photo": photo.name, "draft_boxes": len(lines), "best_confidence": round(best, 3),
                     "app_would_accept": int(best >= args.app_conf)})

    (out / "data.yaml").write_text("names: ['waste']\nnc: 1\n", encoding="utf-8")
    with open(out / "draft_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    rejected = [r for r in rows if not r["app_would_accept"]]
    empty = [r for r in rows if not r["draft_boxes"]]
    print(f"{len(rows)} photos -> {out}")
    print(f"  the app would reject {len(rejected)} of them today (best confidence < {args.app_conf})")
    print(f"  {len(empty)} have no draft box at all: draw those from scratch")
    for r in empty:
        print(f"    {r['photo']}")


if __name__ == "__main__":
    main()
