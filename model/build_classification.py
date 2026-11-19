"""Build the waste-type classification dataset (model/datasets/WasteTypes) from checked crops.

This is the second dataset. The detection dataset (PlanetWatch) finds waste; this one
teaches a classifier what kind of waste each detected pile is. Its images are crops of
the detection boxes, labelled by type in Roboflow.

    python -m model.build_classification --labelled "model/datasets/WasteTypes-roboflow"
    python -m model.build_classification --labelled <export> --no-supplement
    python -m model.build_classification --labelled <export> "model/datasets/WasteTypes-extra"

WasteTypes-extra/ holds crops whose type is known without checking, e.g. every box in the
rubble photos is construction_rubble.

--labelled is the Roboflow classification export in **Folder Structure** format (one
folder per type, any train/valid/test split inside it is ignored and re-made here).

Split rules
  * all crops from one photo stay in the same split (no near-identical piles leaking
    between train and test);
  * our own Zimbabwe crops (planetwatch-own, app-reports) go half to train, half to test,
    so the test set always measures local performance;
  * downloaded crops split 80 / 10 / 10;
  * supplementary item crops from the litter dataset (`waste.v2i.yolov11 (2).zip`) only
    go to train: they are single items, not piles, so scoring on them would flatter us.

Output:
  WasteTypes/{train,valid,test}/<type>/*.jpg
  WasteTypes/manifest.csv   file, type, source, photo, split
"""
import argparse
import csv
import hashlib
import io
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from model.crop_detections import crop_box
from model.waste_types import TYPE_NAMES

MODEL_DIR = Path(__file__).resolve().parent
DATASETS_DIR = MODEL_DIR / "datasets"
OUTPUT = DATASETS_DIR / "WasteTypes"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

OWN_SOURCES = {"planetwatch-own", "app-reports"}  # extend as more of our own sources are added

# Outdoor litter dataset: classes mapped onto our types. Plastic and paper are left out,
# the crops already have plenty of both.
SUPPLEMENT = {
    "zip": "waste.v2i.yolov11 (2).zip",
    "url": "https://universe.roboflow.com/nci-dexdc/waste-kokii/dataset/2",
    "classes": {"Metal": "metal_glass", "Glass": "metal_glass", "Electronics": "hazardous", "Food Waste": "organic"},
}

_ROBOFLOW_SUFFIX = re.compile(r"_(?:jpe?g|png|webp|bmp)\.rf\.[0-9a-f]+$", re.I)


def parse_crop_name(stem: str) -> tuple[str, str]:
    """(source, photo) from a crop file name, before or after a Roboflow round trip.

    Crops are named `<source>__<photo>__<box index>`; Roboflow appends `_jpg.rf.<hash>`.
    """
    stem = _ROBOFLOW_SUFFIX.sub("", stem)
    photo = stem.rsplit("__", 1)[0]
    return stem.split("__", 1)[0], photo


def split_for(source: str, photo: str) -> str:
    bucket = int(hashlib.sha1(f"{source}/{photo}".encode()).hexdigest(), 16) % 1000 / 1000
    if source in OWN_SOURCES:
        return "test" if bucket < 0.5 else "train"
    return "train" if bucket < 0.8 else ("valid" if bucket < 0.9 else "test")


def labelled_crops(export: Path):
    """Yield (path, type) from a folder-structure export; Roboflow may nest it under train/valid/test."""
    unknown = Counter()
    for path in sorted(export.rglob("*")):
        if path.suffix.lower() not in IMAGE_EXTS:
            continue
        waste_type = path.parent.name
        if waste_type not in TYPE_NAMES:
            unknown[waste_type] += 1
            continue
        yield path, waste_type
    if unknown:
        print(f"  ignored folders that aren't waste types: {dict(unknown)}")


def supplement_crops(zip_path: Path, min_side: int):
    """Yield (photo key, type, crop image) — one copy per original photo, boxes >= min_side px."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        yaml = archive.read(next(n for n in names if n.endswith("data.yaml"))).decode()
        class_names = re.findall(r"'([^']*)'", re.search(r"names:\s*\[(.*?)\]", yaml, re.S).group(1))
        seen = set()
        for name in sorted(n for n in names if "/images/" in n):
            original = re.split(r"_(?:jpe?g|png|webp|bmp)\.rf\.", name.rsplit("/", 1)[-1], flags=re.I)[0].lower()
            if original in seen:
                continue  # augmented copy of a photo we already used
            label_name = name.rsplit(".", 1)[0].replace("/images/", "/labels/") + ".txt"
            if label_name not in names:
                continue
            boxes = []
            for line in archive.read(label_name).decode().splitlines():
                parts = line.split()
                if len(parts) == 5 and class_names[int(parts[0])] in SUPPLEMENT["classes"]:
                    boxes.append((SUPPLEMENT["classes"][class_names[int(parts[0])]], *map(float, parts[1:])))
            if not boxes:
                continue
            seen.add(original)
            image = Image.open(io.BytesIO(archive.read(name))).convert("RGB")
            for index, (waste_type, cx, cy, w, h) in enumerate(boxes):
                box = ((cx - w / 2) * image.width, (cy - h / 2) * image.height,
                       (cx + w / 2) * image.width, (cy + h / 2) * image.height)
                if min(box[2] - box[0], box[3] - box[1]) >= min_side:
                    yield f"{original}__{index}", waste_type, crop_box(image, box, 0.10)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--labelled", required=True, nargs="+",
                        help="Roboflow classification export (Folder Structure); more folders laid out the same "
                             "way (<type>/<source>__<photo>__<n>.jpg) can follow, e.g. WasteTypes-extra")
    parser.add_argument("--downloads", default=str(Path.home() / "Downloads" / "Vision Images"))
    parser.add_argument("--no-supplement", action="store_true", help="Leave out the litter-dataset item crops")
    parser.add_argument("--min-side", type=int, default=64)
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    exports, output = [Path(p) for p in args.labelled], Path(args.output)
    for export in exports:
        if not export.exists():
            raise SystemExit(f"{export} not found. Export the checked crops from Roboflow as Folder Structure.")
    if output.exists():
        shutil.rmtree(output)
    for split in ("train", "valid", "test"):
        for waste_type in TYPE_NAMES:
            (output / split / waste_type).mkdir(parents=True)

    manifest, counts, seen = [], defaultdict(Counter), set()

    def add(image_source, file_name: str, waste_type: str, source: str, photo: str, split: str) -> None:
        destination = output / split / waste_type / file_name
        if isinstance(image_source, Path):
            shutil.copy(image_source, destination)
        else:
            image_source.save(destination, "JPEG", quality=92)
        manifest.append({"file": f"{split}/{waste_type}/{file_name}", "type": waste_type,
                         "source": source, "photo": photo, "split": split})
        counts[split][waste_type] += 1

    print("1) Checked crops")
    for path, waste_type in (item for export in exports for item in labelled_crops(export)):
        source, photo = parse_crop_name(path.stem)
        key = _ROBOFLOW_SUFFIX.sub("", path.stem)
        if key in seen:
            continue  # Roboflow augmentation copies: keep one
        seen.add(key)
        add(path, f"{key}.jpg", waste_type, source, photo, split_for(source, photo))

    if not args.no_supplement:
        zip_path = Path(args.downloads) / SUPPLEMENT["zip"]
        if zip_path.exists():
            print(f"2) Supplementary item crops from {zip_path.name} (train only)")
            for key, waste_type, crop in supplement_crops(zip_path, args.min_side):
                add(crop, f"litter-outdoor__{key}.jpg", waste_type, "litter-outdoor", key.rsplit("__", 1)[0], "train")
        else:
            print(f"2) skipped supplement, not found: {zip_path}")

    with open(output / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "type", "source", "photo", "split"])
        writer.writeheader()
        writer.writerows(manifest)

    own_test = Counter(m["type"] for m in manifest if m["split"] == "test" and m["source"] in OWN_SOURCES)
    print(f"\n{'type':22}{'train':>7}{'valid':>7}{'test':>7}{'  (own in test)':>16}")
    problems = []
    for waste_type in TYPE_NAMES:
        row = [counts[s][waste_type] for s in ("train", "valid", "test")]
        print(f"{waste_type:22}{row[0]:>7}{row[1]:>7}{row[2]:>7}{own_test[waste_type]:>16}")
        if 0 in row:
            problems.append(f"{waste_type} has no images in {['train', 'valid', 'test'][row.index(0)]}")
        elif row[0] < 100 or row[2] < 30:
            print(f"{'':22}  ^ thin: aim for 100+ train and 30+ test")
    if problems:
        # The trainer reads class folders per split; an empty one would shift class numbers.
        raise SystemExit("Can't train yet:\n  " + "\n  ".join(problems) +
                         "\nLabel more crops of these types, or merge the type into another in waste_types.py.")
    print(f"\nDataset ready: {output}\nTrain with: python -m model.train_classifier")


if __name__ == "__main__":
    main()
