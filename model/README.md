# PlanetWatch model

YOLOv11 waste detection. The backend imports `model.inference` and `model.exif_extract` from here.

```
python -m model.train               # trains on model/dataset/data.yaml, copies best.pt to model/weights/
python -m model.detect --source model/raw_images
python -m model.exif_extract        # writes a GPS/time manifest for raw_images/
```

`weights/`, `dataset/`, `datasets/`, `raw_images/` and `runs/` are gitignored.
