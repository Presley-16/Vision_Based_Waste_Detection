"""Build the PlanetWatch training dataset: one YOLO detection dataset, one class (`waste`).

Merges our own Roboflow-labelled photos with the downloaded street/dumping datasets:

    python -m model.build_dataset                         # sources from ~/Downloads/Vision Images
    python -m model.build_dataset --downloads "D:/data"   # somewhere else
    python -m model.build_dataset --with-classification   # also unpack the waste-type datasets

Output (all under model/datasets/, gitignored):

    sources/<name>/         untouched copy of each downloaded detection dataset
    PlanetWatch/            merged dataset -> train with model/datasets/PlanetWatch/data.yaml
    classification/<name>/  image-level waste-type datasets for a later classifier

Merge rules
  * every class becomes 0 `waste` (the downloaded sets use incompatible names such as
    `garbage`, `garbage_bag`, `dumping`, `0`, `c` — all of them are dumped waste);
  * polygon labels are converted to boxes;
  * Roboflow exports several augmented copies of one photo — copies are grouped by their
    original filename so a photo never lands in both train and valid/test, and valid/test
    keep only one copy;
  * the same photo appearing in two downloaded datasets is kept once (filename + image hash);
  * our own photos keep the split chosen in Roboflow, so validation always includes
    real Zimbabwe photos;
  * downloaded training photos listed in datasets/label_audit/excluded.txt (written by
    `python -m model.audit_labels`) are dropped as label errors.
"""
import argparse
import hashlib
import io
import json
import os
import random
import re
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

from PIL import Image

MODEL_DIR = Path(__file__).resolve().parent
DATASETS_DIR = MODEL_DIR / "datasets"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Downloaded detection datasets that show dumped / scattered waste outdoors.
DETECTION_SOURCES = [
    {"slug": "ai-dumping-detection", "zip": "AI Dumping Detection.v3i.yolov11.zip",
     "url": "https://universe.roboflow.com/aidumpingdetection/ai-dumping-detection", "license": "MIT"},
    {"slug": "garbage-dumping-detection", "zip": "garbage dumping detection.v1i.yolov11.zip",
     "url": "https://universe.roboflow.com/myspace-vwrde/garbage-dumping-detection", "license": "CC BY 4.0"},
    {"slug": "garbage-best", "zip": "garbage_best.v1i.yolov11.zip",
     "url": "https://universe.roboflow.com/smart-india-hackathon-2023/garbage_best", "license": "CC BY 4.0"},
    # Street piles + clean-road negatives (`clean*`, no boxes). Its drone shots of grass
    # (`batch*`, `GOPR*`) and high-up video frames (`frame*`) don't match phone photos.
    {"slug": "garbage-streets", "zip": "garbage.v1i.yolov11 (1).zip",
     "url": "https://universe.roboflow.com/daminiprashantvichare/garbage-djz5n", "license": "not stated",
     "exclude": r"^(batch|gopr|frame)"},
    {"slug": "garbage-roadside", "zip": "Garbage.v2i.yolov11.zip",
     "url": "https://universe.roboflow.com/agx-iyj2m/garbage-0q3db", "license": "CC BY 4.0"},
]

# Our own labelled photos (Roboflow export, already inside the project).
OWN_SOURCE = {"slug": "planetwatch-own", "dir": "PlanetWatch Waste.v1i.yolov11",
              "url": "https://universe.roboflow.com/presleys-workspace/planetwatch-waste", "license": "CC BY 4.0"}

# Image-level (no boxes) datasets for the future waste-type classifier.
CLASSIFICATION_SOURCES = [
    {"slug": "garbage-classification", "zip": "Garbage classification.v1i.folder.zip"},
    {"slug": "waste-classification-multiclass", "zip": "waste classification.v1i.multiclass.zip"},
    {"slug": "organic-recyclable", "zip": "archive.zip"},
    {"slug": "biodegradable", "zip": "archive (2).zip"},
]

# Split for downloaded data (by original photo): train / valid / test.
SPLIT = (0.80, 0.15, 0.05)


_RF_SPLIT = re.compile(r"(_(?:jpe?g|png|heic|webp|bmp)\.rf\.)", re.I)


def short_name(filename: str) -> str:
    """Shorten very long filenames (Windows' 260-char path limit) deterministically.

    An image and its label share a stem, so both get the same short stem; the
    `<original>_jpg.rf.<hash>` shape is kept so augmented copies still group.
    """
    stem, dot, ext = filename.rpartition(".")
    if len(stem) <= 60:
        return filename
    match = _RF_SPLIT.search(stem)
    if match:
        original, sep, rest = stem[:match.start()], match.group(1), stem[match.end():]
    else:
        original, sep, rest = stem, "", ""
    short = hashlib.sha1(original.lower().encode()).hexdigest()[:16]
    return f"{short}{sep}{rest[:32]}{dot}{ext}"


def extract(zip_path: Path, destination: Path) -> None:
    marker = destination / ".extracted"
    if marker.exists():
        print(f"  already extracted: {destination.relative_to(MODEL_DIR)}")
        return
    if destination.exists():
        shutil.rmtree(destination)  # a previous extraction was interrupted
    print(f"  extracting {zip_path.name} -> {destination.relative_to(MODEL_DIR)}")
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            parts = PurePosixPath(member.filename).parts
            target = destination.joinpath(*parts[:-1], short_name(parts[-1]))
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    marker.write_text(zip_path.name)


def original_name(image_path: Path) -> str:
    """Roboflow names augmented copies `<original>_jpg.rf.<hash>.jpg` — recover `<original>`."""
    return re.split(r"_(?:jpe?g|png|heic|webp|bmp)\.rf\.", image_path.name, flags=re.I)[0].lower()


def image_hash(image_path: Path) -> str:
    """Difference hash: identical for the same photo even after re-encoding/resizing."""
    with Image.open(image_path) as img:
        small = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = small.tobytes()  # one byte per pixel in "L" mode
    bits = "".join("1" if pixels[r * 9 + c] > pixels[r * 9 + c + 1] else "0" for r in range(8) for c in range(8))
    return f"{int(bits, 2):016x}"


def to_waste_boxes(label_path: Path) -> list[str]:
    """Read a YOLO label file (boxes or polygons) and return `0 cx cy w h` lines."""
    if not label_path.exists():
        return []
    lines = []
    for raw in label_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = raw.split()
        if len(parts) == 5:
            cx, cy, w, h = map(float, parts[1:])
            x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        elif len(parts) > 5 and len(parts) % 2 == 1:
            xs, ys = list(map(float, parts[1::2])), list(map(float, parts[2::2]))
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        else:
            continue
        x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(1.0, x2), min(1.0, y2)
        if x2 - x1 < 0.002 or y2 - y1 < 0.002:
            continue
        lines.append(f"0 {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}")
    return lines


def collect(dataset_root: Path) -> dict[str, list[tuple[Path, Path, str]]]:
    """Group a YOLO export's images by original photo: {original: [(image, label, roboflow_split)]}."""
    groups = defaultdict(list)
    for image in sorted(dataset_root.rglob("*")):
        if image.suffix.lower() not in IMAGE_EXTENSIONS or "images" not in image.parts:
            continue
        label = Path(str(image.parent).replace(f"{os.sep}images", f"{os.sep}labels")) / (image.stem + ".txt")
        split = next((p for p in image.parts if p in ("train", "valid", "val", "test")), "train")
        groups[original_name(image)].append((image, label, "valid" if split == "val" else split))
    return groups


EXCLUDED_FILE = DATASETS_DIR / "label_audit" / "excluded.txt"
NEGATIVES_DIR = DATASETS_DIR / "negatives"  # our own no-waste photos (no labels needed)
COCO_URL = "http://images.cocodataset.org/zips/val2017.zip"


def load_excluded() -> set[str]:
    """`source/original` keys of training photos whose labels the audit flagged as wrong."""
    if not EXCLUDED_FILE.exists():
        return set()
    lines = EXCLUDED_FILE.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def assign_split(key: str) -> str:
    bucket = int(hashlib.sha1(key.encode()).hexdigest(), 16) % 1000 / 1000
    if bucket < SPLIT[0]:
        return "train"
    return "valid" if bucket < SPLIT[0] + SPLIT[1] else "test"


def fetch_coco_negatives(downloads: Path, count: int) -> Path:
    """Extract `count` random COCO val2017 photos (everyday scenes: people, rooms, streets)."""
    destination = DATASETS_DIR / "sources" / "coco-negatives"
    marker = destination / ".extracted"
    if marker.exists() and marker.read_text() == str(count):
        print(f"  already extracted: {destination.relative_to(MODEL_DIR)} ({count} photos)")
        return destination
    zip_path = downloads / "coco-val2017.zip"
    if not zip_path.exists():
        print(f"  downloading COCO val2017 (~780 MB) -> {zip_path}")
        partial = zip_path.with_suffix(".part")
        urllib.request.urlretrieve(COCO_URL, partial)
        partial.rename(zip_path)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        names = sorted(n for n in archive.namelist() if n.lower().endswith(".jpg"))
        for name in random.Random(0).sample(names, min(count, len(names))):
            (destination / PurePosixPath(name).name).write_bytes(archive.read(name))
    marker.write_text(str(count))
    print(f"  extracted {count} COCO photos -> {destination.relative_to(MODEL_DIR)}")
    return destination


def build(downloads: Path, with_classification: bool, coco_negatives: int = 0) -> None:
    sources_dir = DATASETS_DIR / "sources"
    output = DATASETS_DIR / "PlanetWatch"

    print("1) Extracting downloaded detection datasets")
    for source in DETECTION_SOURCES:
        zip_path = downloads / source["zip"]
        if not zip_path.exists():
            raise SystemExit(f"Missing {zip_path} — download it from {source['url']} (format: YOLOv11).")
        extract(zip_path, sources_dir / source["slug"])

    own_dir = DATASETS_DIR / OWN_SOURCE["dir"]
    if not own_dir.exists():
        raise SystemExit(f"Missing our own labelled dataset at {own_dir}")

    print("2) Merging into model/datasets/PlanetWatch (single class: waste)")
    if output.exists():
        shutil.rmtree(output)
    for split in ("train", "valid", "test"):
        (output / split / "images").mkdir(parents=True)
        (output / split / "labels").mkdir(parents=True)

    seen_names, seen_hashes = set(), set()
    stats = []
    excluded = load_excluded()
    manifest = ["image,source,original,split"]
    plan = [(OWN_SOURCE, own_dir, True)] + [(s, sources_dir / s["slug"], False) for s in DETECTION_SOURCES]

    for source, root, keep_own_split in plan:
        counts = {"train": 0, "valid": 0, "test": 0, "photos": 0, "boxes": 0, "duplicates": 0, "label_errors": 0}
        exclude = re.compile(source["exclude"], re.I) if source.get("exclude") else None
        for original, items in collect(root).items():
            if exclude and exclude.search(original):
                continue
            hashes = {image_hash(image) for image, _, _ in items}
            if not keep_own_split and (original in seen_names or hashes & seen_hashes):
                counts["duplicates"] += 1
                continue
            seen_names.add(original)
            seen_hashes |= hashes
            # Training photos flagged by `python -m model.audit_labels`; valid/test stay
            # untouched so scores remain comparable between runs.
            if (not keep_own_split and f"{source['slug']}/{original}" in excluded
                    and assign_split(f"{source['slug']}/{original}") == "train"):
                counts["label_errors"] += 1
                continue
            counts["photos"] += 1

            for index, (image, label, roboflow_split) in enumerate(items):
                split = roboflow_split if keep_own_split else assign_split(f"{source['slug']}/{original}")
                if split != "train" and not keep_own_split and index > 0:
                    continue  # one copy per photo outside train
                name = f"{source['slug']}__{hashlib.sha1(str(image).encode()).hexdigest()[:10]}"
                boxes = to_waste_boxes(label)
                shutil.copy2(image, output / split / "images" / f"{name}{image.suffix.lower()}")
                (output / split / "labels" / f"{name}.txt").write_text("\n".join(boxes) + ("\n" if boxes else ""))
                counts[split] += 1
                counts["boxes"] += len(boxes)
                manifest.append(f"{name},{source['slug']},\"{original}\",{split}")
        stats.append((source, counts))
        print(f"  {source['slug']:<28} photos={counts['photos']:<5} images train/valid/test="
              f"{counts['train']}/{counts['valid']}/{counts['test']}  boxes={counts['boxes']}  "
              f"duplicates skipped={counts['duplicates']}  label errors dropped={counts['label_errors']}")

    # No-waste photos (people, rooms, offices, clean streets) with empty labels, so the
    # model learns what is *not* waste instead of calling anything cluttered "waste".
    negative_sources = []
    if NEGATIVES_DIR.exists():
        negative_sources.append(({"slug": "negatives-own", "license": "own photos", "url": "model/datasets/negatives/"},
                                 NEGATIVES_DIR))
    if coco_negatives:
        negative_sources.append(({"slug": "coco-negatives", "license": "COCO (CC BY 4.0 annotations; Flickr images)",
                                  "url": "https://cocodataset.org"}, fetch_coco_negatives(downloads, coco_negatives)))
    for source, root in negative_sources:
        counts = {"train": 0, "valid": 0, "test": 0, "photos": 0, "boxes": 0, "duplicates": 0, "label_errors": 0}
        for image in sorted(p for p in root.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS):
            try:
                digest = image_hash(image)
            except OSError:
                print(f"  skipped damaged image: {image.name}")
                continue
            if digest in seen_hashes:
                counts["duplicates"] += 1
                continue
            split = assign_split(f"{source['slug']}/{image.name}")
            name = f"{source['slug']}__{hashlib.sha1(str(image).encode()).hexdigest()[:10]}"
            shutil.copy2(image, output / split / "images" / f"{name}{image.suffix.lower()}")
            (output / split / "labels" / f"{name}.txt").write_text("")
            counts[split] += 1
            counts["photos"] += 1
            manifest.append(f"{name},{source['slug']},\"{image.stem}\",{split}")
        stats.append((source, counts))
        print(f"  {source['slug']:<28} photos={counts['photos']:<5} images train/valid/test="
              f"{counts['train']}/{counts['valid']}/{counts['test']}  (no-waste examples)")

    (output / "manifest.csv").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    (output / "data.yaml").write_text(
        "# Generated by `python -m model.build_dataset` — rebuild instead of editing by hand.\n"
        "train: train/images\nval: valid/images\ntest: test/images\n\nnc: 1\nnames: ['waste']\n",
        encoding="utf-8",
    )
    write_sources_note(output, stats)

    if with_classification:
        print("3) Extracting waste-type (classification) datasets")
        for source in CLASSIFICATION_SOURCES:
            zip_path = downloads / source["zip"]
            if zip_path.exists():
                extract(zip_path, DATASETS_DIR / "classification" / source["slug"])
            else:
                print(f"  skipped (not found): {zip_path.name}")

    print(f"\nDone. Train with: python -m model.train --data \"{output / 'data.yaml'}\"")


def write_sources_note(output: Path, stats) -> None:
    totals = {k: sum(c[k] for _, c in stats) for k in ("train", "valid", "test", "photos", "boxes")}
    rows = "\n".join(
        f"| {s['slug']} | {c['photos']} | {c['train']} / {c['valid']} / {c['test']} | {c['boxes']} | {s['license']} | {s['url']} |"
        for s, c in stats
    )
    (output / "SOURCES.md").write_text(
        "# PlanetWatch detection dataset\n\n"
        "Single class: `waste`. Built by `python -m model.build_dataset`.\n\n"
        "| Source | Unique photos | Images train / valid / test | Boxes | Licence | Link |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"{rows}\n"
        f"| **Total** | **{totals['photos']}** | **{totals['train']} / {totals['valid']} / {totals['test']}** | **{totals['boxes']}** | | |\n\n"
        "CC BY 4.0 datasets require attribution — cite the links above in any publication.\n",
        encoding="utf-8",
    )
    (output / "stats.json").write_text(json.dumps({s["slug"]: c for s, c in stats}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--downloads", default=str(Path.home() / "Downloads" / "Vision Images"),
                        help="Folder containing the downloaded dataset zips")
    parser.add_argument("--with-classification", action="store_true",
                        help="Also unpack the image-level waste-type datasets into model/datasets/classification/")
    parser.add_argument("--coco-negatives", type=int, default=0, metavar="N",
                        help="Add N random everyday COCO photos as no-waste examples (downloads ~780 MB once)")
    args = parser.parse_args()
    build(Path(args.downloads), args.with_classification, args.coco_negatives)


if __name__ == "__main__":
    main()
