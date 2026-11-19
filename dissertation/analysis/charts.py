"""Result charts of the dissertation (Figures 4.1-4.3, 4.5-4.7) -> ../figures/.

Run from the repo root: venv/Scripts/python.exe dissertation/analysis/charts.py
"""
import csv, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent; OUT = HERE.parent / "figures"; REPO = Path(r"C:\Users\presley.nyama\Desktop\Vision-Based_Illegal_Waste_Detection")
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 12, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 200, "savefig.bbox": "tight"})
GREY, GOLD, GREEN, BLUE = "#8a8f8a", "#c8962e", "#1f7a50", "#3b6fb0"
D = json.load(open(HERE / "scores.json"))

# Fig 4.1 dataset composition (v4)
rows = [("PlanetWatch own (Zimbabwe)", 42, 9, 6), ("ai-dumping-detection", 249, 8, 3), ("garbage-dumping-detection", 763, 153, 65),
        ("garbage-best", 1466, 162, 57), ("garbage-streets", 334, 76, 25), ("garbage-roadside", 186, 39, 15),
        ("garbage-identification", 3711, 290, 89), ("Own no-waste photos", 140, 23, 8), ("COCO no-waste photos", 637, 124, 39)]
fig, ax = plt.subplots(figsize=(9, 4.4))
y = np.arange(len(rows))[::-1]
for i, (lab, c) in enumerate((("train", GREEN), ("valid", GOLD), ("test", BLUE))):
    left = np.array([sum(r[1:1 + i]) for r in rows])
    ax.barh(y, [r[1 + i] for r in rows], left=left, color=c, label=lab, height=0.8)
for yy, r in zip(y, rows):
    ax.text(sum(r[1:]) + 30, yy, f"{sum(r[1:]):,}", va="center", fontsize=11)
ax.set_yticks(y, [r[0] for r in rows]); ax.set_xlabel("Images"); ax.legend(frameon=False, loc="lower right")
ax.set_xlim(0, 4500)
fig.savefig(OUT / "fig4_1_dataset.png"); plt.close(fig)

# Fig 4.2 M4 training curves
r = list(csv.DictReader(open(REPO / "model/runs/detect/waste_v4_rubble/results.csv")))
ep = [int(x["epoch"]) for x in r]
g = lambda k: [float(x[k]) for x in r]
best = max(r, key=lambda x: float(x["metrics/mAP50-95(B)"]))["epoch"]
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
a.plot(ep, g("train/box_loss"), color=GREEN, label="train box loss")
a.plot(ep, g("val/box_loss"), color=GOLD, label="validation box loss")
a.plot(ep, g("train/cls_loss"), "--", color=GREEN, label="train class loss")
a.plot(ep, g("val/cls_loss"), "--", color=GOLD, label="validation class loss")
a.set_xlabel("Epoch"); a.set_ylabel("Loss"); a.legend(frameon=False, fontsize=10)
b.plot(ep, g("metrics/mAP50(B)"), color=GREEN, label="mAP@0.5")
b.plot(ep, g("metrics/mAP50-95(B)"), color=BLUE, label="mAP@0.5:0.95")
b.axvline(int(best), color="grey", ls=":", lw=1)
b.text(int(best) + 1, 0.05, f"best epoch ({best})", color="grey", fontsize=10)
b.set_ylim(0, 0.6); b.set_xlabel("Epoch"); b.set_ylabel("Validation score"); b.legend(frameon=False, fontsize=10, loc="upper left")
fig.tight_layout(); fig.savefig(OUT / "fig4_2_training.png"); plt.close(fig)
row = r[int(best) - 1]
print("detector best epoch", best, row["metrics/mAP50(B)"], row["metrics/mAP50-95(B)"])
vb = g("val/box_loss"); print("val box loss min epoch", ep[int(np.argmin(vb))])
m50 = g("metrics/mAP50(B)"); print("mAP50 at 25/50:", m50[24], m50[49])


def photo(m, t=0.25):
    ph = D[m]["test"]
    tp = sum(p["waste"] and p["score"] >= t for p in ph); fn = sum(p["waste"] and p["score"] < t for p in ph)
    fp = sum((not p["waste"]) and p["score"] >= t for p in ph); tn = sum((not p["waste"]) and p["score"] < t for p in ph)
    P, R = tp / (tp + fp), tp / (tp + fn)
    return [(tp + tn) / len(ph), R, tn / (tn + fp), 2 * P * R / (P + R)]


# Fig 4.3 box / photo level, four models
labels = {"M1": "M1 YOLO11s (v1 data)", "M2": "M2 YOLO11m (v2 data)", "M3": "M3 YOLO11m (v3 data)",
          "M4": "M4 YOLO11s (v4 data, deployed)"}
cols = {"M1": GREY, "M2": GOLD, "M3": GREEN, "M4": BLUE}
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6))
w = 0.2; x = np.arange(4)
for i, m in enumerate(D):
    bx = D[m]["box"]
    bars = a.bar(x + (i - 1.5) * w, [bx["map50"], bx["map"], bx["p"], bx["r"]], w, color=cols[m], label=labels[m])
    a.bar_label(bars, fmt="%.2f", fontsize=8, padding=1)
    bars = b.bar(x + (i - 1.5) * w, photo(m), w, color=cols[m])
    b.bar_label(bars, fmt="%.2f", fontsize=8, padding=1)
a.set_xticks(x, ["mAP@0.5", "mAP@0.5:0.95", "Precision", "Recall"]); a.set_ylim(0, 0.75); a.set_title("Box level (test split)")
a.legend(frameon=False, fontsize=9, loc="upper left")
b.set_xticks(x, ["Accuracy", "Recall\n(waste found)", "Specificity\n(clean rejected)", "F1"]); b.set_ylim(0, 1.1)
b.set_title("Photo level, confidence \u2265 0.25 (test split)")
fig.tight_layout(); fig.savefig(OUT / "fig4_3_models.png"); plt.close(fig)

# Fig 4.5 threshold sweep on test
TH = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60]
fig, ax = plt.subplots(figsize=(8, 4.6))
for m in ("M2", "M3", "M4"):
    ph = D[m]["test"]; W = [p for p in ph if p["waste"]]; C = [p for p in ph if not p["waste"]]
    rec = [sum(p["score"] >= t for p in W) / len(W) for t in TH]
    spe = [sum(p["score"] < t for p in C) / len(C) for t in TH]
    name = labels[m].split(" (")[0]
    ax.plot(TH, rec, "-o", color=cols[m], ms=4, label=f"{name} recall")
    ax.plot(TH, spe, "--s", color=cols[m], ms=4, label=f"{name} specificity")
for t, txt in ((0.25, "default 0.25"), (0.40, "0.40")):
    ax.axvline(t, color="grey", ls=":", lw=1); ax.text(t + 0.005, 0.66, txt, color="grey", fontsize=10)
ax.set_ylim(0.4, 1.02); ax.set_xlabel("Confidence threshold"); ax.set_ylabel("Proportion of test photos")
ax.legend(frameon=False, fontsize=10, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.14))
fig.savefig(OUT / "fig4_5_threshold.png"); plt.close(fig)

# Fig 4.7 classifier confusion matrix (row-normalised colour, counts shown)
rows = list(csv.reader(open(REPO / "model/runs/classify/evaluation/confusion.csv")))
names = ["Plastic", "Paper/cardboard", "Organic", "Metal/glass", "Construction rubble", "Bulky items", "Hazardous", "Mixed household"]
M = np.array([[int(v) for v in r[1:]] for r in rows[1:]]); N = M / M.sum(1, keepdims=True)
fig, ax = plt.subplots(figsize=(7.6, 6.2))
im = ax.imshow(N, cmap="Greens", vmin=0, vmax=1)
for i in range(8):
    for j in range(8):
        if M[i, j]:
            ax.text(j, i, M[i, j], ha="center", va="center", fontsize=10, color="white" if N[i, j] > 0.55 else "black")
ax.set_xticks(range(8), names, rotation=40, ha="right")
ax.set_yticks(range(8), [f"{n} ({M[i].sum()})" for i, n in enumerate(names)])
ax.set_xlabel("Predicted type"); ax.set_ylabel("True type (number of test crops)")
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03); cb.set_label("Share of the true type's test crops")
fig.savefig(OUT / "fig4_7_confusion.png"); plt.close(fig)

# Fig 4.8 classifier training curve
r = list(csv.DictReader(open(REPO / "model/runs/classify/waste_type/results.csv")))
ep = [int(x["epoch"]) for x in r]
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.4))
a.plot(ep, [float(x["train/loss"]) for x in r], color=GREEN, label="train loss")
a.plot(ep, [float(x["val/loss"]) for x in r], color=GOLD, label="validation loss")
a.set_xlabel("Epoch"); a.set_ylabel("Loss"); a.legend(frameon=False, fontsize=10)
b.plot(ep, [float(x["metrics/accuracy_top1"]) for x in r], color=GREEN, label="top-1 accuracy")
b.plot(ep, [float(x["metrics/accuracy_top5"]) for x in r], color=BLUE, label="top-5 accuracy")
cb_best = max(r, key=lambda x: float(x["metrics/accuracy_top1"]))["epoch"]
b.axvline(int(cb_best), color="grey", ls=":", lw=1)
b.text(int(cb_best) + 0.5, 0.45, f"best epoch ({cb_best})", color="grey", fontsize=10)
b.set_ylim(0.4, 1.02); b.set_xlabel("Epoch"); b.set_ylabel("Validation accuracy"); b.legend(frameon=False, fontsize=10, loc="center right")
fig.tight_layout(); fig.savefig(OUT / "fig4_6_classifier_training.png"); plt.close(fig)
print("classifier best epoch", cb_best, "epochs run", len(r))
