# Vision-Based Illegal Waste Detection and Reporting

YOLOv11-based system for detecting illegal waste dumping from geotagged smartphone
images: citizens report from the website or mobile app, municipal teams monitor and
act on reports from their own dashboard.

## Structure

Each part is its own codebase in its own folder:

| Folder | What it is | Tech |
| --- | --- | --- |
| [`backend/`](backend/) | JSON API: auth, reports, municipal actions, app distribution (QR / USB) | Flask, SQLite |
| [`frontend/`](frontend/) | Citizen reporting website | Static HTML/CSS/JS + Leaflet |
| [`municipal/`](municipal/) | Municipal monitoring dashboard | Static HTML/CSS/JS + Leaflet |
| [`mobile/`](mobile/) | Android + iOS app, bundling `frontend/` so it behaves exactly like the website | Capacitor 8 |
| [`model/`](model/) | YOLOv11 training, inference, EXIF tooling, weights, datasets | Ultralytics |

## Quick start

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python backend/run.py
```

That serves everything on port 5000:

- Citizen website: http://localhost:5000/
- Municipal dashboard: http://localhost:5000/municipal/ (login from `MUNICIPAL_USERNAME` / `MUNICIPAL_PASSWORD`, default `admin` / `planetwatch`; change these before real use)
- Install page (QR code + USB): http://localhost:5000/install.html

Copy `.env` and fill in secret values (email password, Twilio credentials, API keys) before running.

## Location is mandatory

Signed-in citizens must keep device location on. If it's off or blocked, a blocking popup
asks them to switch it on. The Report page pins the current location on a map and tags
every photo with it.

Browsers only share location on **https** or `localhost`. Phones visiting the website over
plain `http://192.168.x.x` won't get a location. Serve the backend over HTTPS (for
example a tunnel such as `cloudflared tunnel --url http://localhost:5000`) and set
`PUBLIC_BASE_URL` to that address. The Android app is not affected, because its pages
load from the app itself.

## GPU

PyTorch detects the CUDA GPU on this machine (8GB VRAM). `model/train.py` and
`model/inference.py` use it automatically through Ultralytics.

## Alerts

Email alerts use Gmail SMTP and SMS alerts use Twilio. Both are optional:
`backend/planetwatch/alerts.py` logs a warning and skips them if their `.env`
credentials aren't set.
