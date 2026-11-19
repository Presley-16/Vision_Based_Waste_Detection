# PlanetWatch backend

Flask JSON API shared by the citizen website, the mobile app and the municipal dashboard.
Run it with `python backend/run.py`. It binds `0.0.0.0:5000` so phones on the same Wi-Fi can reach it.

For convenience it also serves `frontend/` at `/` and `municipal/` at `/municipal/`.

## Endpoints

| Method | Path | Who |
| --- | --- | --- |
| POST | `/api/auth/signup` (name, surname, phone, password, address), `/api/auth/signin` (name, surname, password) | citizen → `{token, citizen}` |
| POST | `/api/auth/forgot` (name, surname) → texts a 6-digit code; `/api/auth/reset` (name, surname, code, password) → `{token, citizen}` | forgot password |
| GET/PUT | `/api/me` | citizen profile. PUT needs `current_password`; it is JSON or multipart with an optional `photo` / `remove_photo` |
| GET | `/api/me/reports` | citizen's own reports |
| GET | `/api/reports` | public GeoJSON of all pinned reports |
| POST | `/api/reports` | multipart: `photos` (one or more) with a `latitude`/`longitude` pair per photo; location is required |
| POST | `/api/municipal/login` | staff → `{token}` |
| GET | `/api/municipal/reports?status=all\|pending\|solved` | reports with uploader contact details, plus counts |
| PATCH / DELETE | `/api/municipal/reports/<id>` | set `{status}` / delete report and its photo |
| GET | `/api/install/info`, `/api/install/status` | QR code and scan detection for the install page |
| GET | `/download/PlanetWatch.apk` | serves `mobile/dist/PlanetWatch.apk` |
| GET/POST | `/api/install/usb`, `/api/install/usb/install` | ADB install. Only answers requests from this computer. |

Passwords are stored only as salted scrypt hashes. They can contain spaces and any symbols, and need at least 6 characters.
Accounts created before passwords existed set one by signing up again with the same name.

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
| `SMS_GATEWAY_URL` / `SMS_GATEWAY_USERNAME` / `SMS_GATEWAY_PASSWORD` | unset. Sends SMS from your own Android phone's SIM (see **Text messages** below) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` | unset. Used for SMS only if `SMS_GATEWAY_URL` isn't set |
| `ALERT_PHONE_NUMBERS` / `ALERT_RECIPIENTS` | unset. Municipal staff phone numbers / email addresses (comma-separated) that get an alert for every new report |
| `SMS_COUNTRY_CODE` | `263`. Added to local numbers that start with 0 |
| `TRUSTED_PROXY` | unset. Set it to `1` behind nginx so the app trusts `X-Forwarded-*` (see `deploy/README.md`) |

## Text messages (SMS from your own phone)

Password-reset codes and the municipal new-report alerts are sent as normal SMS from an
Android phone's own SIM, using its SMS bundle, through the free
[SMS Gateway for Android](https://sms-gate.app) app. An iPhone can't do this, because iOS
doesn't let apps send texts on their own.

1. Put a SIM with an SMS bundle in an Android phone (a cheap or old one is fine), and install
   **SMS Gateway for Android** from the Play Store or [sms-gate.app](https://sms-gate.app).
   Allow it to send SMS.
2. Choose a mode in the app and copy its details into `.env`:

   | Mode | When | `SMS_GATEWAY_URL` |
   | --- | --- | --- |
   | **Local Server** | Backend on your PC, phone on the same Wi-Fi | `http://<phone IP shown in the app>:8080/message` |
   | **Cloud Server** (free) | Backend on the internet (Azure) | `https://api.sms-gate.app/3rdparty/v1/messages` |

   ```
   SMS_GATEWAY_URL=http://192.168.1.23:8080/message
   SMS_GATEWAY_USERNAME=<username shown in the app>
   SMS_GATEWAY_PASSWORD=<password shown in the app>
   ALERT_PHONE_NUMBERS=0771234567, 0712345678   # municipal staff
   ```
3. Tap **Start** in the app, then restart the backend.

Keep the phone charged, online, and out of battery-saving mode for the app. If the phone
can't be reached, citizens are asked to try the code again later. A failed municipal alert is
logged and never blocks a report. Without any SMS setup, `run.py` (debug mode) prints reset
codes in the server window instead.

