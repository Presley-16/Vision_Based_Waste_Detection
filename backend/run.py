"""Start the PlanetWatch backend: `python backend/run.py` (from the repo root or backend/).

Binds to 0.0.0.0 by default so phones on the same Wi-Fi can reach it — that's
what the install QR code and the mobile app point at.

`python backend/run.py --tunnel` also opens an https address through ngrok.
iPhones (and phone browsers in general) only share location over https, so
use this when citizens use PlanetWatch from Safari / the iPhone Home Screen.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# The backend uses the sibling `model/` package for YOLO inference and EXIF parsing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planetwatch import create_app  # noqa: E402

app = create_app()


def start_ngrok_tunnel(port: int) -> str:
    """Start `ngrok http <port>` and return its public https URL."""
    ngrok = shutil.which("ngrok")
    if not ngrok:
        sys.exit("ngrok isn't installed — get it from https://ngrok.com/download, then run `ngrok config add-authtoken <token>`.")
    subprocess.Popen([ngrok, "http", str(port), "--log", "stdout"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ngrok's local inspection API reports the tunnel once it's up.
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as response:
                tunnels = json.load(response)["tunnels"]
            https = [t["public_url"] for t in tunnels if t["public_url"].startswith("https://")]
            if https:
                return https[0]
        except OSError:
            pass
        time.sleep(0.5)
    sys.exit("ngrok didn't start a tunnel within 20s — run `ngrok http %d` yourself to see the error." % port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PlanetWatch backend.")
    parser.add_argument("--tunnel", action="store_true", help="also serve over https via ngrok (needed for location on iPhones)")
    args = parser.parse_args()

    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    # The debug reloader re-runs this file in a child process; only the parent
    # starts ngrok, and the child inherits PUBLIC_BASE_URL through the environment.
    if args.tunnel and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        os.environ["PUBLIC_BASE_URL"] = start_ngrok_tunnel(port)
        print(f"\n  PlanetWatch is live over https at {os.environ['PUBLIC_BASE_URL']}\n"
              f"  The install QR code and share links now use that address.\n")

    app.run(host=os.environ.get("FLASK_HOST", "0.0.0.0"), port=port, debug=debug)
