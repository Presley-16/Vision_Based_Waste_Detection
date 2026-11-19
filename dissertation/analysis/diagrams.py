"""Diagrams of the dissertation (Figures 2.1, 3.1, 3.2) -> ../figures/."""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent.parent / "figures"
plt.rcParams.update({"font.family": "Times New Roman", "savefig.dpi": 200, "savefig.bbox": "tight"})
GREEN_E, GREEN_F = "#1f7a50", "#e6f0ea"
GOLD_E, GOLD_F = "#c8962e", "#fcf3e0"
GREY_E, GREY_F = "#8f8f8f", "#f2f2f2"
DARK = "#1b3a2a"


def box(ax, x, y, w, h, text, kind="green", size=13):
    e, f = {"green": (GREEN_E, GREEN_F), "gold": (GOLD_E, GOLD_F), "grey": (GREY_E, GREY_F)}[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12", ec=e, fc=f, lw=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, linespacing=1.25)


def arrow(ax, a, b, color=DARK, style="-|>", lw=1.8, rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=14, color=color, lw=lw,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


# ---- Figure 2.1 conceptual framework
fig, ax = canvas(16, 8.2)
box(ax, 0.3, 5.0, 3.2, 2.0, "Citizen as sensor\n(VGI: Goodchild, 2007)\nphoto + location + time")
box(ax, 4.65, 5.0, 3.5, 2.0, "Automated verification\n(YOLO11 detector, threshold τ;\nwaste-type classifier)", "gold")
box(ax, 9.3, 5.0, 3.0, 2.0, "Geolocated,\ntime-stamped,\ntyped report")
box(ax, 13.05, 5.0, 2.6, 2.0, "Municipal\naction\n(clean-up)")
box(ax, 0.3, 0.6, 3.2, 2.2, "Feedback to citizen\n(report status)\nsustains participation", "grey")
box(ax, 4.65, 0.6, 3.5, 2.2, "Data quality inputs:\nlocal + public data,\nno-waste images,\nlabel audit, type labels")
box(ax, 9.3, 0.6, 3.0, 2.2, "Location quality:\nGPS / Wi-Fi fix,\naccuracy radius,\nEXIF fallback")
for (x1, x2, t) in ((3.5, 4.65, "submits"), (8.15, 9.3, "accepts"), (12.3, 13.05, "alert")):
    arrow(ax, (x1, 6.0), (x2, 6.0)); ax.text((x1 + x2) / 2, 6.2, t, ha="center", fontsize=12)
arrow(ax, (6.4, 2.8), (6.4, 5.0)); ax.text(6.5, 3.9, "trains", fontsize=12)
arrow(ax, (10.8, 2.8), (10.8, 5.0)); ax.text(10.9, 3.9, "locates", fontsize=12)
arrow(ax, (1.9, 2.8), (1.9, 5.0), color=GREY_E); ax.text(2.0, 3.9, "repeat reporting", fontsize=12, color="grey")
ax.plot([14.35, 14.35, 1.9], [5.0, 0.2, 0.2], color=GREY_E, lw=1.8); arrow(ax, (1.9, 0.2), (1.9, 0.6), color=GREY_E)
ax.text(8.0, 0.32, "status updates (pending → solved)", ha="center", fontsize=12, color="grey")
ax.text(6.4, 7.45, "rejected photos discarded (false reports filtered)", ha="center", fontsize=12, color=GOLD_E, style="italic")
fig.savefig(OUT / "fig2_1_framework.png"); plt.close(fig)

# ---- Figure 3.1 research process
fig, ax = canvas(16, 6)
labels = ["1. Problem\nidentification\n(Ch. 1–2)", "2. Objectives\nof a solution\n(RO1–RO4)",
          "3. Design &\ndevelopment\n(data, models, system)", "4. Demonstration\n(prototype on\nphones + dashboard)",
          "5. Evaluation\n(test split, latency,\nlocation checks)", "6. Communication\n(dissertation)"]
for i, t in enumerate(labels):
    box(ax, 0.3 + i * 2.6, 3.2, 2.35, 2.2, t, size=12)
    if i:
        arrow(ax, (0.3 + i * 2.6 - 0.25, 4.3), (0.3 + i * 2.6, 4.3))
arrow(ax, (13.0, 3.15), (6.6, 3.15), color=GOLD_E, lw=2.2, rad=-0.45)
ax.text(9.8, 1.25, "iterate: dataset v1 → v2 → v3 → v4, threshold tuning, type labelling, Scrum sprints",
        ha="center", fontsize=12.5, color="#8a6417")
ax.text(8.0, 0.35, "Inside step 3: collect & label → merge sources → de-duplicate / group splits → audit labels → "
        "train detector (transfer learning) → crop boxes & label types → train classifier → validate → test once",
        ha="center", fontsize=11, style="italic")
fig.savefig(OUT / "fig3_1_process.png"); plt.close(fig)

# ---- Figure 3.2 architecture
fig, ax = canvas(16, 11.2)
for x, t in ((2.3, "Clients"), (8.0, "Flask backend (Python)"), (13.6, "Outputs")):
    ax.text(x, 10.75, t, ha="center", fontsize=15, weight="bold")
ax.add_patch(FancyBboxPatch((5.3, 0.35), 5.4, 9.9, boxstyle="square,pad=0", ec=GREY_E, fc="#f7f7f7", lw=1.6))
box(ax, 0.3, 8.4, 4.0, 1.6, "Citizen website (PWA)\nHTML/CSS/JS, camera,\nGeolocation API", size=13)
box(ax, 0.3, 6.1, 4.0, 1.6, "Android / iOS app\n(Capacitor wrapper of\nthe same web client)", size=13)
box(ax, 0.3, 3.0, 4.0, 1.6, "Municipal dashboard\nLeaflet + OpenStreetMap,\nwaste types, status workflow", size=13)
bx, bw = 5.6, 4.8
box(ax, bx, 8.7, bw, 1.25, "REST API /api/*\nauth (scrypt hashes, signed tokens)", size=12)
box(ax, bx, 7.05, bw, 1.25, "Report service: location check,\nEXIF time, one report per photo", size=12)
box(ax, bx, 5.4, bw, 1.25, "YOLO11s detector (Ultralytics)\nconf ≥ YOLO_CONF_THRESHOLD", "gold", size=12)
box(ax, bx, 3.75, bw, 1.25, "YOLO11s-cls waste-type classifier\non each box crop (≥ 0.40, else unclassified)", "gold", size=12)
box(ax, bx, 2.1, bw, 1.25, "SQLite via SQLAlchemy:\ncitizens, reports, detections + types", size=12)
box(ax, bx, 0.55, bw, 1.25, "Alert service (background thread):\nSMS gateway / Twilio / e-mail", size=12)
for y1, y2 in ((8.7, 8.3), (7.05, 6.65), (5.4, 5.0), (3.75, 3.35), (2.1, 1.8)):
    arrow(ax, (8.0, y1), (8.0, y2))
arrow(ax, (4.3, 9.2), (5.6, 9.3)); ax.text(4.95, 9.75, "photo +\nlat/lng", ha="center", fontsize=11)
arrow(ax, (4.3, 6.9), (5.6, 8.8))
arrow(ax, (5.6, 2.7), (4.3, 3.6)); ax.text(4.95, 2.35, "reports\nJSON", ha="center", fontsize=11)
box(ax, 11.6, 7.9, 4.1, 1.7, "Rejected photo:\ndeleted, citizen told\n“no waste detected”", "grey", size=13)
box(ax, 11.6, 4.6, 4.1, 1.7, "Map pin + waste type + status\n(pending → reviewed\n→ solved)", size=13)
box(ax, 11.6, 0.8, 4.1, 1.7, "SMS to municipal staff\nwith waste type, Google Maps\nlink and dashboard link", size=13)
arrow(ax, (10.4, 6.0), (11.6, 8.4)); ax.text(11.3, 6.75, "no box", fontsize=11)
arrow(ax, (10.4, 2.7), (11.6, 5.2)); ax.text(11.35, 3.3, "waste\nfound", fontsize=11)
arrow(ax, (10.4, 1.15), (11.6, 1.5))
fig.savefig(OUT / "fig3_2_architecture.png"); plt.close(fig)
print("ok")
