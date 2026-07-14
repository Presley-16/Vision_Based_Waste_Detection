# Vision-Based Illegal Waste Detection and Reporting

YOLOv11-based system for detecting illegal waste dumping from geotagged smartphone
images, with a Flask backend serving a GIS dashboard and a citizen reporting website.

## Structure

- `raw_images/` — unannotated iPhone photos (dataset collection)
- `dataset/` — Roboflow-exported annotated dataset
- `models/` — trained YOLOv11 weight files (`best.pt`)
- `notebooks/` — experimentation notebooks
- `scripts/` — standalone scripts (`exif_extract.py`, `detect.py`, `train.py`)
- `app/` — Flask backend (GIS dashboard + citizen reporting site)

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env` and fill in secret values (email password, Twilio credentials, API keys) before running.

## GPU

PyTorch auto-detected a CUDA-capable GPU on this machine (`torch.cuda.is_available() == True`),
8GB VRAM. `scripts/train.py` and `app/inference.py` will use it automatically via Ultralytics —
no `device=0` flag needed unless you want to force it explicitly.

## Alerts

Email alerts use Gmail SMTP; SMS alerts use Twilio. Both are optional — `app/alerts.py` skips
silently with a warning if their `.env` credentials aren't set, so the rest of the app keeps
working before those accounts are provisioned.

## Citizen reporting site

The `/report` form captures location via the browser's Geolocation API (not EXIF) — the
iPhone-native EXIF pipeline (`scripts/exif_extract.py`) is for your own training-data
collection, not for photos submitted through the website.
