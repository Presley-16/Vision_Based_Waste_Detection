# PlanetWatch model

YOLOv11 waste detection. The backend imports `model.inference` and `model.exif_extract` from here.

## Dataset

```
python -m model.build_dataset                        # merge everything into model/datasets/PlanetWatch
python -m model.build_dataset --with-classification  # also unpack the waste-type datasets
```

It reads the downloaded zips from `~/Downloads/Vision Images` (change with `--downloads`) plus our
own Roboflow export in `model/datasets/PlanetWatch Waste.v3i.yolov11`. Everything is merged into a
single class, `waste`; duplicates are removed and augmented copies never cross train/valid.
Sources, counts and licences are in `model/datasets/PlanetWatch/SOURCES.md`.

To add newly labelled photos: export a new version from Roboflow (YOLOv11), replace the
`PlanetWatch Waste.v…` folder in `model/datasets/`, update `OWN_SOURCE` in `build_dataset.py`
if the folder name changed, and rebuild.

| Folder in `model/datasets/` | Contents |
| --- | --- |
| `PlanetWatch Waste.v3i.yolov11/` | Our own labelled Zimbabwe photos incl. 9 rubble photos (Roboflow export, no augmentation) |
| `WasteTypes-roboflow/` | Checked waste-type crops (Roboflow Folder Structure export) |
| `WasteTypes-extra/` | Crops whose type is known without checking (the rubble photos) |
| `WasteTypes/` | **The waste-type classification dataset** (built from the two above) |
| `sources/` | Untouched copies of the downloaded detection datasets |
| `PlanetWatch/` | **The merged training dataset** |
| `classification/` | Image-level waste-type datasets, for a later classifier |
| `label_audit/` | `excluded.txt` (training photos dropped as label errors) and `review.csv` |

## Train / evaluate / detect

```
python -m model.train --epochs 100 --batch 16   # writes model/weights/best.pt
python -m model.evaluate                        # mAP + photo-level accuracy on the test split, per source
python -m model.detect --source model/raw_images
python -m model.exif_extract                    # GPS/time manifest for raw_images/
```

## No-waste examples

The model only rejects non-waste photos reliably if it has trained on them. Two sources of
photos with empty labels are merged in, and split across train/valid/test like everything else:

- `model/datasets/negatives/`: our own photos with no waste (selfies, offices, rooms, clean
  streets). Just drop the photos in, no labelling needed.
- `--coco-negatives N`: N random everyday COCO photos (people, rooms, streets), downloaded once.

```
python -m model.build_dataset --coco-negatives 800
python -m model.evaluate --sweep   # accept/reject trade-off per YOLO_CONF_THRESHOLD
```

## Cleaning labels

```
python -m model.audit_labels    # flags downloaded training photos the trained model disagrees with
python -m model.build_dataset   # rebuilds without them; valid/test are never changed
```

The audit drops at most 12% of downloaded training photos and never touches clean-scene
negatives, our own photos, or large piles the model simply missed. Delete a line from
`datasets/label_audit/excluded.txt` to keep a photo. Own photos that disagree with the model
are listed in `review.csv` as "check by hand"; fix them in Roboflow.

## Waste-type labels

Every detected pile also gets a type (plastic, rubble, hazardous, …), listed with the reason
for each in `waste_types.py`. The labels come from crops of the detection boxes, so the
classifier learns from real dump scenes, not single items on a white background.

```
python -m model.crop_detections   # one crop per box -> datasets/type_labelling/crops/ (+ crops.csv)
python -m model.prelabel_types    # CLIP suggests a type -> datasets/type_labelling/roboflow_upload/<type>/
```

`crop_detections` uses one copy of each original photo (no augmented duplicates), skips boxes
under 64px, and also crops photos citizens reported through the app.

Then correct the suggestions in Roboflow:

1. Create a new **Classification** project (single-label), e.g. `planetwatch-waste-types`.
2. Drag the whole `roboflow_upload/` folder in. The folder names become the labels.
3. Go through each class and move wrong crops to the right type. Delete crops that are
   not waste or are too blurry to judge. Start with the low-confidence ones at the top of
   `suggestions.csv`; plastic, paper and mixed suggestions are mostly right, while rubble,
   metal/glass and hazardous suggestions are mostly wrong.
4. Export the dataset as **Folder Structure** into `datasets/` for training.

File names keep their source as a prefix (`planetwatch-own__…`), so our own Zimbabwe crops can
be held out for testing after export.

The public crops have very little rubble, hazardous waste or metal/glass. Those types need our
own photos of rubble heaps, scrap and e-waste, cropped the same way.

### New photos (e.g. rubble)

```
python -m model.draft_boxes "C:/Users/me/Downloads/Vision Images/Rubble"
```

Draws draft boxes with the current detector (low threshold) into `datasets/to_label/<folder>/`.
Drag that folder into the **PlanetWatch Waste** detection project, fix the boxes, export a new
version, then rebuild (`build_dataset`) and re-run `crop_detections` and `prelabel_types`.
`draft_report.csv` shows which photos the app would reject today.

### Train the waste-type classifier (second dataset: `datasets/WasteTypes/`)

```
python -m model.build_classification --labelled "model/datasets/WasteTypes-roboflow" "model/datasets/WasteTypes-extra"
python -m model.train_classifier       # -> weights/waste_type.pt
python -m model.evaluate_classifier    # accuracy, per-type F1, confusion matrix; own vs downloaded
```

Our own crops are split half train / half test so the test always measures Zimbabwe photos;
the outdoor-litter item crops (`waste.v2i.yolov11 (2).zip`) only go to train. The backend uses
`weights/waste_type.pt` automatically after a restart (`WASTE_TYPE_WEIGHTS`,
`WASTE_TYPE_CONF_THRESHOLD`, default 0.40, below which a pile is stored as "unclassified").

PyTorch must be the CUDA build to use the GPU (`torch.cuda.is_available()` → True):
`pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu130`

`weights/`, `datasets/`, `dataset/`, `raw_images/` and `runs/` are gitignored.
