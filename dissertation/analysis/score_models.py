"""Score M1-M4 on the v4 dataset: box metrics (test), per-photo max confidence (valid+test), speed."""
import json, time, sys
from pathlib import Path
import torch
from ultralytics import YOLO

REPO = Path(r"C:\Users\presley.nyama\Desktop\Vision-Based_Illegal_Waste_Detection")
DATA = REPO / "model/datasets/PlanetWatch"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
MODELS = {
    "M1": REPO / "model/weights/best_v1_map40.pt",
    "M2": REPO / "model/weights/best_v2_map43.pt",
    "M3": REPO / "model/weights/best_dissertation_v1.pt",
    "M4": REPO / "model/weights/best.pt",
}
result = {}
for name, weights in MODELS.items():
    model = YOLO(str(weights))
    r = {"weights": weights.name, "size_mb": weights.stat().st_size / 1e6}
    m = model.val(data=str(DATA / "data.yaml"), split="test", plots=(name == "M4"), verbose=False, workers=0,
                  project=str(OUT / "val"), name=name, exist_ok=True)
    p, rec = float(m.box.mp), float(m.box.mr)
    r["box"] = {"map50": float(m.box.map50), "map": float(m.box.map), "p": p, "r": rec, "f1": 2 * p * rec / (p + rec)}
    r["boxes"] = int(sum(len(l.read_text().split("\n")) for l in (DATA / "test/labels").glob("*.txt") if l.read_text().strip()))
    r["params_m"] = sum(x.numel() for x in model.model.parameters()) / 1e6
    for split in ("valid", "test"):
        images = sorted((DATA / split / "images").iterdir())
        photos = []
        for i in range(0, len(images), 16):
            batch = images[i:i + 16]
            for img, res in zip(batch, model.predict([str(x) for x in batch], conf=0.01, verbose=False)):
                lab = DATA / split / "labels" / (img.stem + ".txt")
                photos.append({"image": img.name, "source": img.name.split("__")[0],
                               "waste": lab.exists() and lab.read_text().strip() != "",
                               "score": max((float(c) for c in res.boxes.conf), default=0.0)})
        r[split] = photos
    # speed: mean end-to-end predict time after 5 warm-ups (GPU: 50 test images, CPU: 30)
    test_imgs = [str(x) for x in sorted((DATA / "test/images").iterdir())]
    for device, n in (("0", 50), ("cpu", 30)):
        model = YOLO(str(weights))  # fresh predictor per device
        for x in test_imgs[:5]:
            model.predict(x, device=device, verbose=False)
        times = []
        for x in test_imgs[:n]:
            if device == "0": torch.cuda.synchronize()
            t = time.perf_counter(); model.predict(x, device=device, verbose=False)
            if device == "0": torch.cuda.synchronize()
            times.append((time.perf_counter() - t) * 1000)
        r["gpu_ms" if device == "0" else "cpu_ms"] = sum(times) / len(times)
    result[name] = r
    print(name, r["box"], r["gpu_ms"], r["cpu_ms"], flush=True)
(OUT / "scores.json").write_text(json.dumps(result, indent=1))
