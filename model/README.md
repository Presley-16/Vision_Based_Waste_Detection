# PlanetWatch model

YOLOv11 waste detection. The backend imports `model.inference` and `model.exif_extract` from here.

## Dataset

```
python -m model.build_dataset                        # merge everything into model/datasets/PlanetWatch
python -m model.build_dataset --with-classification  # also unpack the waste-type datasets
```

It reads the downloaded zips from `~/Downloads/Vision Images` (change with `--downloads`) plus our
own Roboflow export in `model/datasets/PlanetWatch Waste.v1i.yolov11`. Everything is merged into a
single class, `waste`; duplicates are removed and augmented copies never cross train/valid.
Sources, counts and licences are in `model/datasets/PlanetWatch/SOURCES.md`.

To add newly labelled photos: export a new version from Roboflow (YOLOv11), replace the
`PlanetWatch Waste.v…` folder in `model/datasets/`, update `OWN_SOURCE` in `build_dataset.py`
if the folder name changed, and rebuild.

| Folder in `model/datasets/` | Contents |
| --- | --- |
| `PlanetWatch Waste.v1i.yolov11/` | Our own labelled Zimbabwe photos (Roboflow export) |
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

PyTorch must be the CUDA build to use the GPU (`torch.cuda.is_available()` → True):
`pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu130`

`weights/`, `datasets/`, `dataset/`, `raw_images/` and `runs/` are gitignored.
