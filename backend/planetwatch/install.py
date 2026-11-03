"""Mobile-app distribution: QR code install, APK download, and USB (ADB) install.

QR flow: the install page asks for a QR code tied to a random session id. The
QR opens `get-app.html?s=<id>` on the phone, which pings `/scanned`; the install
page polls `/status` and shows a green check once its own session was scanned.

USB flow: Android phones are installed with ADB on the machine running this
backend (the phone is plugged into *this* computer), so those endpoints only
answer requests coming from this machine itself.
"""
import io
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import qrcode
import qrcode.image.svg
from flask import Blueprint, abort, current_app, jsonify, request, send_file

install = Blueprint("install", __name__)

# session id -> {"scanned_at", "platform", "downloaded_at"}; in-memory is fine,
# a session only needs to live as long as someone is looking at the install page.
_qr_sessions: dict[str, dict] = {}
_SESSION_TTL_SECONDS = 60 * 60

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _lan_ip() -> str | None:
    """Best-effort LAN IP of this machine (no packets are actually sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return None


def public_base_url() -> str:
    """Base URL a *phone* can reach: PUBLIC_BASE_URL if set, else this host with localhost swapped for the LAN IP."""
    configured = os.environ.get("PUBLIC_BASE_URL")
    if configured:
        return configured.rstrip("/")

    parts = urlsplit(request.host_url)
    host = parts.hostname or "localhost"
    if host in _LOOPBACK_HOSTS:
        host = _lan_ip() or host
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}"


def _apk_path() -> Path:
    return Path(current_app.config["APK_PATH"])


def _ipa_path() -> Path:
    return Path(current_app.config["APK_PATH"]).with_name("PlanetWatch.ipa")


def _platform_from_user_agent(user_agent: str) -> str:
    ua = user_agent.lower()
    if "android" in ua:
        return "android"
    if "iphone" in ua or "ipad" in ua or "ipod" in ua:
        return "ios"
    return "other"


def _prune_sessions() -> None:
    cutoff = time.time() - _SESSION_TTL_SECONDS
    for session_id in [sid for sid, info in _qr_sessions.items() if info["created_at"] < cutoff]:
        del _qr_sessions[session_id]


def _session(session_id: str | None) -> dict | None:
    if not session_id or len(session_id) > 64:
        return None
    _prune_sessions()
    return _qr_sessions.setdefault(
        session_id, {"created_at": time.time(), "scanned_at": None, "platform": None, "downloaded_at": None}
    )


def _qr_svg(data: str) -> str:
    image = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode("utf-8")


@install.get("/api/install/info")
def info():
    session_id = request.args.get("session")
    _session(session_id)
    base_url = public_base_url()
    page_url = f"{base_url}/get-app.html" + (f"?s={session_id}" if session_id else "")
    apk = _apk_path()
    return jsonify({
        "base_url": base_url,
        "page_url": page_url,
        "share_url": f"{base_url}/get-app.html",
        "apk_url": f"{base_url}/download/PlanetWatch.apk",
        "apk_available": apk.exists(),
        "apk_size_mb": round(apk.stat().st_size / 1_048_576, 1) if apk.exists() else None,
        "qr_svg": _qr_svg(page_url),
        "ipa_url": f"{base_url}/download/PlanetWatch.ipa",
        "ipa_available": _ipa_path().exists(),
        "https": base_url.startswith("https://"),
        "usb_supported": _is_local_request(),
    })


@install.post("/api/install/scanned")
def scanned():
    data = request.get_json(silent=True) or {}
    info = _session(data.get("session"))
    if info is None:
        return jsonify({"ok": False}), 400
    info["scanned_at"] = time.time()
    info["platform"] = _platform_from_user_agent(request.headers.get("User-Agent", ""))
    return jsonify({"ok": True, "platform": info["platform"]})


@install.get("/api/install/status")
def status():
    info = _session(request.args.get("session"))
    if info is None:
        return jsonify({"error": "Missing session"}), 400
    return jsonify({
        "qr": {
            "scanned": info["scanned_at"] is not None,
            "platform": info["platform"],
            "downloaded": info["downloaded_at"] is not None,
        },
    })


@install.get("/download/PlanetWatch.apk")
def download_apk():
    apk = _apk_path()
    if not apk.exists():
        abort(404, description="The Android app has not been built yet — see mobile/README.md.")
    info = _session(request.args.get("s"))
    if info is not None:
        info["downloaded_at"] = time.time()
    return send_file(
        apk,
        mimetype="application/vnd.android.package-archive",
        as_attachment=True,
        download_name="PlanetWatch.apk",
    )


@install.get("/download/PlanetWatch.ipa")
def download_ipa():
    ipa = _ipa_path()
    if not ipa.exists():
        abort(404, description="The iOS app has not been built yet — see mobile/README.md.")
    return send_file(ipa, mimetype="application/octet-stream", as_attachment=True, download_name="PlanetWatch.ipa")


# ---------- USB / ADB ----------

def _local_addresses() -> set[str]:
    addresses = {"127.0.0.1", "::1"}
    try:
        addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    lan = _lan_ip()
    if lan:
        addresses.add(lan)
    return addresses


def _is_local_request() -> bool:
    return request.remote_addr in _local_addresses()


def _find_adb() -> str | None:
    configured = os.environ.get("ADB_PATH")
    if configured and Path(configured).exists():
        return configured
    on_path = shutil.which("adb")
    if on_path:
        return on_path
    exe = "adb.exe" if sys.platform == "win32" else "adb"
    sdk_roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT")]
    if os.environ.get("LOCALAPPDATA"):
        sdk_roots.append(str(Path(os.environ["LOCALAPPDATA"]) / "Android" / "Sdk"))
    sdk_roots.append(str(Path.home() / "Library" / "Android" / "sdk"))
    sdk_roots.append(str(Path.home() / "Android" / "Sdk"))
    for root in filter(None, sdk_roots):
        candidate = Path(root) / "platform-tools" / exe
        if candidate.exists():
            return str(candidate)
    return None


def _run_adb(adb: str, *args: str, timeout: int = 10) -> subprocess.CompletedProcess:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        [adb, *args], capture_output=True, text=True, timeout=timeout, creationflags=creationflags
    )


def _list_devices(adb: str) -> list[dict]:
    result = _run_adb(adb, "devices", "-l")
    devices = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("*") or line.startswith("List of devices"):
            continue
        serial, _, rest = line.partition("\t") if "\t" in line else line.partition(" ")
        fields = rest.split()
        state = fields[0] if fields else "unknown"
        props = dict(field.split(":", 1) for field in fields[1:] if ":" in field)
        # Only real phones count — a running Android Studio emulator would
        # otherwise get the green check and receive the install instead.
        if serial.startswith("emulator-") or props.get("model", "").startswith("sdk_"):
            continue
        devices.append({
            "serial": serial,
            "state": state,  # "device" (ready), "unauthorized" (tap Allow on the phone), "offline"
            "model": props.get("model", "").replace("_", " ") or None,
        })
    return devices


# USB vendor IDs of common Android phone makers (Samsung, Google, Motorola,
# Xiaomi, Huawei, OnePlus, Oppo/Realme, Vivo, HTC, LG, Sony, Transsion).
_ANDROID_VENDOR_IDS = {"04E8", "18D1", "22B8", "2717", "12D1", "2A70", "22D9", "2D95", "0BB4", "1004", "0FCE", "2A45"}
_APPLE_VENDOR_ID = "05AC"
_attached_cache: dict = {"at": 0.0, "value": None}


def _scan_usb() -> dict:
    """Phones plugged in by cable, as Windows sees them: {"android": ..., "iphone": ...}.

    adb only sees Android phones with USB debugging on, but Windows enumerates a
    phone in any mode — so we can tell the user *why* it isn't installing (e.g.
    left on MIDI) and spot iPhones, which install through Sideloadly instead.
    """
    if sys.platform != "win32":
        return {"android": None, "iphone": None}
    if time.time() - _attached_cache["at"] < 4:
        return _attached_cache["value"]

    script = (
        "Get-CimInstance Win32_PnPEntity -Filter \"PNPDeviceID LIKE 'USB%VID_%'\" | "
        "ForEach-Object { $_.PNPDeviceID + '|' + $_.Name }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.TimeoutExpired, OSError):
        return {"android": None, "iphone": None}

    phone = None
    iphone = None
    for line in result.stdout.splitlines():
        device_id, _, name = line.strip().partition("|")
        upper = device_id.upper()
        lower_name = name.strip().lower()
        vendor = upper.split("VID_", 1)[1][:4] if "VID_" in upper else ""

        if vendor == _APPLE_VENDOR_ID:
            # Apple's iPhone/iPad USB product IDs are 0x12xx.
            if "iphone" in lower_name or "ipad" in lower_name or "apple mobile device" in lower_name or "PID_12" in upper:
                iphone = iphone or {"name": None, "driver_ok": False}
                if "iphone" in lower_name or "ipad" in lower_name:
                    iphone["name"] = name.strip()
                if "apple mobile device" in lower_name:
                    iphone["driver_ok"] = True
            continue

        if vendor not in _ANDROID_VENDOR_IDS:
            continue
        phone = phone or {"name": None, "mode": "charging", "adb_interface": False}
        if "MIDI" in upper or lower_name == "midi function":
            phone["mode"] = "midi"
        elif ("MTP" in upper or "WPD" in name.upper()) and phone["mode"] != "midi":
            phone["mode"] = "file-transfer"
        if "adb" in lower_name:
            phone["adb_interface"] = True
        if "\\" in device_id and "&MI_" not in upper and "composite" not in lower_name and "midi" not in lower_name:
            phone["name"] = phone["name"] or name.strip() or None

    value = {"android": phone, "iphone": iphone}
    _attached_cache.update(at=time.time(), value=value)
    return value


@install.get("/api/install/usb")
def usb_status():
    if not _is_local_request():
        return jsonify({"supported": False, "reason": "remote"}), 403
    adb = _find_adb()
    if not adb:
        return jsonify({"supported": False, "reason": "no-adb"})
    try:
        devices = _list_devices(adb)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return jsonify({"supported": False, "reason": "adb-error", "detail": str(exc)})
    scan = _scan_usb()
    return jsonify({
        "supported": True,
        "devices": devices,
        # Only worth the slower Windows lookup when adb sees nothing usable.
        "attached": None if devices else scan["android"],
        "iphone": scan["iphone"],
        "apk_available": _apk_path().exists(),
        "ipa_available": _ipa_path().exists(),
    })


@install.post("/api/install/usb/install")
def usb_install():
    if not _is_local_request():
        return jsonify({"error": "USB install is only available on the computer running PlanetWatch."}), 403
    adb = _find_adb()
    if not adb:
        return jsonify({"error": "Android platform-tools (adb) is not installed on this computer."}), 400
    apk = _apk_path()
    if not apk.exists():
        return jsonify({"error": "The Android app has not been built yet — see mobile/README.md."}), 400

    serial = (request.get_json(silent=True) or {}).get("serial")
    ready = [d for d in _list_devices(adb) if d["state"] == "device"]
    if serial:
        ready = [d for d in ready if d["serial"] == serial]
    if not ready:
        return jsonify({"error": "No authorised phone connected. Unlock it and tap Allow USB debugging."}), 400

    target = ready[0]
    try:
        result = _run_adb(adb, "-s", target["serial"], "install", "-r", str(apk), timeout=180)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Install timed out — check the phone for a confirmation prompt."}), 504

    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or "Success" not in output:
        return jsonify({"error": "Install failed.", "detail": output[-500:]}), 500
    return jsonify({"ok": True, "device": target})
