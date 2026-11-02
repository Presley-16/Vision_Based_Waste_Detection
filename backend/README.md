# PlanetWatch backend

Flask JSON API shared by the citizen website, the mobile app and the municipal dashboard.
Run it with `python backend/run.py`. It binds `0.0.0.0:5000` so phones on the same Wi-Fi can reach it.

For convenience it also serves `frontend/` at `/` and `municipal/` at `/municipal/`.

## Endpoints

| Method | Path | Who |
| --- | --- | --- |
| POST | `/api/auth/signup`, `/api/auth/signin` | citizen → `{token, citizen}` |
| GET/PUT | `/api/me` | citizen profile |
| GET | `/api/me/reports` | citizen's own reports |
| GET | `/api/reports` | public GeoJSON of all pinned reports |
| POST | `/api/reports` | multipart: `photos` (one or more) with a `latitude`/`longitude` pair per photo; location is required |
| POST | `/api/municipal/login` | staff → `{token}` |
| GET | `/api/municipal/reports?status=all\|pending\|solved` | reports with uploader contact details, plus counts |
| PATCH / DELETE | `/api/municipal/reports/<id>` | set `{status}` / delete report and its photo |
| GET | `/api/install/info`, `/api/install/status` | QR code and scan detection for the install page |
| GET | `/download/PlanetWatch.apk` | serves `mobile/dist/PlanetWatch.apk` |
| GET/POST | `/api/install/usb`, `/api/install/usb/install` | ADB install. Only answers requests from this computer. |

Auth uses `Authorization: Bearer <token>`. Tokens are signed with `FLASK_SECRET_KEY`. If that
isn't set, a random key is used, so restarting the server signs everyone out.

## Environment

| Variable | Default |
| --- | --- |
| `DATABASE_URL` | `sqlite:///reports.db` (in `backend/instance/`) |
| `MUNICIPAL_USERNAME` / `MUNICIPAL_PASSWORD` | `admin` / `planetwatch` |
| `PUBLIC_BASE_URL` | auto: this machine's LAN IP. This address goes into the QR code and the share link. |
| `APK_PATH` | `mobile/dist/PlanetWatch.apk` |
| `ADB_PATH` | auto: PATH, `ANDROID_HOME`, or the Android Studio SDK |
| `YOLO_WEIGHTS`, `YOLO_CONF_THRESHOLD` | `model/weights/best.pt`, `0.25` |
| `FLASK_HOST` / `FLASK_PORT` / `FLASK_DEBUG` | `0.0.0.0` / `5000` / `1` |
