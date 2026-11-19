"""Crop every labelled waste box into its own image, ready for waste-type labelling.

Sources:
  * the merged detection dataset (model/datasets/PlanetWatch). Only one copy of each
    original photo is used, so Roboflow's augmented duplicates don't make you label
    the same pile three times. Valid/test copies are preferred because they are never
    augmented.
  * reports citizens submitted through the app (backend/instance/reports.db), using
    the boxes the detector stored. These are real Zimbabwe photos.

Output (model/datasets/type_labelling/):
  crops/<source>/<crop>.jpg
  crops.csv   crop, source, original, split, width, height

    python -m model.crop_detections
    python -m model.crop_detections --min-side 96 --padding 0.15
"""
import argparse
import csv
import sqlite3
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageOps

MODEL_DIR = Path(__file__).resolve().parent
REPO_DIR = MODEL_DIR.parent
DATASET = MODEL_DIR / "datasets" / "PlanetWatch"
OUT_DIR = MODEL_DIR / "datasets" / "type_labelling"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def find_image(split: str, stem: str) -> Path | None:
    for ext in IMAGE_EXTS:
        path = DATASET / split / "images" / f"{stem}{ext}"
        if path.exists():
            return path
    return None


def crop_box(image: Image.Image, box: tuple[float, float, float, float], padding: float) -> Image.Image:
    """Crop pixel box (x1, y1, x2, y2) with `padding` × its size added on every side.

    A little surrounding ground helps tell rubble from a sandy verge, and organic
    waste from a hedge.
    """
    x1, y1, x2, y2 = box
    pad_x, pad_y = (x2 - x1) * padding, (y2 - y1) * padding
    return image.crop((
        max(0, int(x1 - pad_x)), max(0, int(y1 - pad_y)),
        min(image.width, int(x2 + pad_x)), min(image.height, int(y2 + pad_y)),
    ))


def dataset_boxes():
    """Yield (source, original, split, image_path, [pixel boxes]) for one copy per original photo."""
    groups = defaultdict(list)
    with open(DATASET / "manifest.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            groups[(row["source"], row["original"])].append(row)

    for (source, original), rows in groups.items():
        row = sorted(rows, key=lambda r: r["split"] == "train")[0]  # valid/test first: un-augmented
        label_path = DATASET / row["split"] / "labels" / f"{row['image']}.txt"
        image_path = find_image(row["split"], row["image"])
        if not image_path or not label_path.exists():
            continue
        lines = [line.split() for line in label_path.read_text().splitlines() if line.strip()]
        if not lines:
            continue  # no-waste negatives
        with Image.open(image_path) as im:
            width, height = im.size
        boxes = []
        for parts in lines:
            cx, cy, w, h = (float(v) for v in parts[1:5])
            boxes.append(((cx - w / 2) * width, (cy - h / 2) * height, (cx + w / 2) * width, (cy + h / 2) * height))
        yield source, original, row["split"], image_path, boxes


def app_boxes(db_path: Path):
    """Yield the same tuples for photos citizens reported through the app."""
    if not db_path.exists():
        return
    connection = sqlite3.connect(db_path)
    rows = connection.execute(
        "SELECT r.id, r.image_path, d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2 "
        "FROM reports r JOIN detections d ON d.report_id = r.id ORDER BY r.id"
    ).fetchall()
    connection.close()
    grouped = defaultdict(list)
    for report_id, image_path, *box in rows:
        grouped[(report_id, image_path)].append(tuple(box))
    for (report_id, image_path), boxes in grouped.items():
        path = REPO_DIR / "backend" / image_path
        if path.exists():
            yield "app-reports", f"report-{report_id}", "test", path, boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min-side", type=int, default=64,
                        help="Skip boxes whose shorter side is under this many pixels (too small to tell the type)")
    parser.add_argument("--padding", type=float, default=0.10, help="Context added around each box, as a fraction of its size")
    parser.add_argument("--db", default=str(REPO_DIR / "backend" / "instance" / "reports.db"))
    args = parser.parse_args()

    crops_dir = OUT_DIR / "crops"
    records, skipped = [], 0
    for source, original, split, image_path, boxes in [*dataset_boxes(), *app_boxes(Path(args.db))]:
        with Image.open(image_path) as im:
            image = ImageOps.exif_transpose(im).convert("RGB")
            for index, box in enumerate(boxes):
                if min(box[2] - box[0], box[3] - box[1]) < args.min_side:
                    skipped += 1
                    continue
                crop = crop_box(image, box, args.padding)
                name = f"{image_path.stem}__{index}"
                destination = crops_dir / source / f"{name}.jpg"
                destination.parent.mkdir(parents=True, exist_ok=True)
                crop.save(destination, "JPEG", quality=92)
                records.append({"crop": f"{source}/{name}.jpg", "source": source, "original": original,
                                "split": split, "width": crop.width, "height": crop.height})

    with open(OUT_DIR / "crops.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["crop", "source", "original", "split", "width", "height"])
        writer.writeheader()
        writer.writerows(records)

    per_source = defaultdict(int)
    for record in records:
        per_source[record["source"]] += 1
    print(f"Wrote {len(records)} crops to {crops_dir} (skipped {skipped} boxes under {args.min_side}px)")
    for source, count in sorted(per_source.items()):
        print(f"  {source:28} {count}")


if __name__ == "__main__":
    main()
