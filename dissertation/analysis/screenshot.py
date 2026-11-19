import io, os, sys, tempfile, threading, time
from pathlib import Path
REPO = Path(r"C:\Users\presley.nyama\Desktop\Vision-Based_Illegal_Waste_Detection")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "figures" / "fig4_8a_dashboard.png"
scratch = Path(tempfile.mkdtemp(prefix="pw_shot_"))
os.environ.update({"DATABASE_URL": f"sqlite:///{(scratch / 'r.db').as_posix()}", "ALERT_RECIPIENTS": "", "ALERT_PHONE_NUMBERS": "",
                   "MUNICIPAL_USERNAME": "examiner", "MUNICIPAL_PASSWORD": "examiner-pass", "FLASK_SECRET_KEY": "shot"})
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "backend")); os.chdir(REPO)
from planetwatch import create_app
from werkzeug.serving import make_server
app = create_app(); app.config["UPLOAD_DIR"] = str(scratch / "uploads"); Path(app.config["UPLOAD_DIR"]).mkdir()
c = app.test_client()
tok = c.post("/api/auth/signup", json={"name": "Test", "surname": "Citizen", "phone": "0770000000", "password": "secret123"}).get_json()["token"]
own = sorted((REPO / "model/datasets/PlanetWatch/test/images").glob("planetwatch-own__*"))
photos = [own[0], own[2], Path(r"C:\Users\presley.nyama\Downloads\Vision Images\Rubble\WhatsApp Image 2026-11-15 at 13.10.51.jpeg")]
coords = [("-17.8452", "31.0335"), ("-17.8105", "31.0420"), ("-17.7893", "31.0906")]
for p, (lat, lng) in zip(photos, coords):
    r = c.post("/api/reports", data={"photos": (io.BytesIO(p.read_bytes()), p.name), "latitude": lat, "longitude": lng},
               headers={"Authorization": f"Bearer {tok}"}, content_type="multipart/form-data")
    print(p.name, r.status_code, [rep["waste_types"] for rep in r.get_json().get("reports", [])])
server = make_server("127.0.0.1", 5077, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1366, "height": 800})
    pg.goto("http://127.0.0.1:5077/municipal/")
    pg.fill("#username", "examiner"); pg.fill("#password", "examiner-pass"); pg.click("button[type=submit]")
    pg.wait_for_url("**/dashboard*", timeout=20000); time.sleep(6)
    pg.screenshot(path=str(OUT))
    b.close()
server.shutdown()
