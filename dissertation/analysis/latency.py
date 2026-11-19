"""End-to-end latency of POST /api/reports through the real Flask app (scratch DB, alerts off)."""
import io, json, os, random, statistics, sys, tempfile, time
from pathlib import Path
REPO = Path(r"C:\Users\presley.nyama\Desktop\Vision-Based_Illegal_Waste_Detection")
scratch = Path(tempfile.mkdtemp(prefix="pw_latency_"))
os.environ.update({"DATABASE_URL": f"sqlite:///{(scratch / 'r.db').as_posix()}", "ALERT_RECIPIENTS": "", "ALERT_PHONE_NUMBERS": "",
                   "YOLO_WEIGHTS": "model/weights/best.pt", "WASTE_TYPE_WEIGHTS": "model/weights/waste_type.pt"})
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "backend")); os.chdir(REPO)
from planetwatch import create_app
app = create_app(); app.config["UPLOAD_DIR"] = str(scratch / "uploads"); Path(app.config["UPLOAD_DIR"]).mkdir()
c = app.test_client()
tok = c.post("/api/auth/signup", json={"name": "Lat", "surname": "Test", "phone": "0770000000", "password": "secret123"}).get_json()["token"]
test = REPO / "model/datasets/PlanetWatch/test"
imgs = sorted((test / "images").iterdir())
has = lambda p: (test / "labels" / (p.stem + ".txt")).read_text().strip() != ""
rng = random.Random(0)
waste = rng.sample([p for p in imgs if has(p)], 20); clean = rng.sample([p for p in imgs if not has(p)], 10)
rows = []
for i, p in enumerate([waste[0]] + waste + clean):
    data = {"photos": (io.BytesIO(p.read_bytes()), p.name), "latitude": "-17.8292", "longitude": "31.0522"}
    t = time.perf_counter()
    r = c.post("/api/reports", data=data, headers={"Authorization": f"Bearer {tok}"}, content_type="multipart/form-data")
    ms = (time.perf_counter() - t) * 1000
    body = r.get_json()
    types = [d["waste_type"] for rep in body.get("reports", []) for d in rep["detections"]]
    rows.append({"first": i == 0, "waste": has(p), "status": r.status_code, "ms": ms, "types": types})
first = rows[0]; rest = rows[1:]
def s(v): v = sorted(v); return round(statistics.mean(v)), round(statistics.median(v)), round(v[int(0.95 * (len(v) - 1) + 0.5)])
w = [r for r in rest if r["waste"]]; cl = [r for r in rest if not r["waste"]]
out = {"device": os.environ.get("CUDA_VISIBLE_DEVICES", "gpu"), "first_s": round(first["ms"] / 1000, 1),
       "waste_mean_median_p95": s([r["ms"] for r in w]), "clean_mean_median_p95": s([r["ms"] for r in cl]),
       "waste_accepted": sum(r["status"] == 201 for r in w), "clean_rejected": sum(r["status"] == 422 for r in cl),
       "types": [r["types"] for r in w if r["status"] == 201]}
print(json.dumps(out))
