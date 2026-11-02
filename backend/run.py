"""Start the PlanetWatch backend: `python backend/run.py` (from the repo root or backend/).

Binds to 0.0.0.0 by default so phones on the same Wi-Fi can reach it — that's
what the install QR code and the mobile app point at.
"""
import os
import sys
from pathlib import Path

# The backend uses the sibling `model/` package for YOLO inference and EXIF parsing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planetwatch import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )
