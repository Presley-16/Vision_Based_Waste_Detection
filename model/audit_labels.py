"""Find training photos whose labels disagree most with the trained model, and drop them.

    python -m model.audit_labels               # writes datasets/label_audit/excluded.txt
    python -m model.build_dataset              # rebuild without the flagged photos

Each downloaded training photo is scored by how well the model's boxes (conf >= 0.25)
match its labels (F1 at IoU 0.5, averaged over Roboflow's augmented copies). A model
that still disagrees with a label after training on it usually points at a wrong label
or a different labelling style (e.g. five item boxes where we use one box per pile).

Only the worst `--max-fraction` of downloaded training photos are dropped. Photos with
no boxes (clean-scene negatives), large labelled piles the model simply missed, our own
photos, and valid/test are never dropped:
our own flagged photos are listed in review.csv for manual checking instead.
"""
import argparse
import collections
import csv
from pathlib import Path

from ultralytics import YOLO

MODEL_DIR = Path(__file__).resolve().parent
DATA_ROOT = MODEL_DIR / "datasets" / "PlanetWatch"
AUDIT_DIR = MODEL_DIR / "datasets" / "label_audit"
OWN_SLUG = "planetwatch-own"
LARGE_PILE = 0.15  # share of the image a labelled box must cover to count as an obvious pile


def read_boxes(label: Path) -> list[tuple[float, float, float, float]]:
    boxes = []
    for line in label.read_text().splitlines():
        parts = line.split()
        if len(parts) == 5:
            cx, cy, w, h = map(float, parts[1:])
            boxes.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    return boxes


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def f1(truth, predicted) -> float:
    unmatched = list(truth)
    matches = 0
    for box in predicted:  # predictions arrive sorted by confidence
        best = max(unmatched, key=lambda t: iou(t, box), default=None)
        if best is not None and iou(best, box) >= 0.5:
            unmatched.remove(best)
            matches += 1
    return 2 * matches / (len(truth) + len(predicted)) if truth or predicted else 1.0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights", default=str(MODEL_DIR / "weights" / "best.pt"))
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--max-f1", type=float, default=0.2, help="Flag photos scoring at or below this F1")
    parser.add_argument("--max-fraction", type=float, default=0.12,
                        help="Never drop more than this share of downloaded training photos")
    args = parser.parse_args()

    manifest = DATA_ROOT / "manifest.csv"
    if not manifest.exists():
        raise SystemExit("Run `python -m model.build_dataset` first (it writes manifest.csv).")
    rows = [r for r in csv.DictReader(manifest.open(encoding="utf-8")) if r["split"] == "train"]

    model = YOLO(args.weights)
    scores = collections.defaultdict(list)
    print(f"Scoring {len(rows)} training images with {Path(args.weights).name} ...")
    for start in range(0, len(rows), 16):
        batch = rows[start:start + 16]
        images = [next((DATA_ROOT / "train" / "images").glob(r["image"] + ".*")) for r in batch]
        for row, result in zip(batch, model.predict([str(p) for p in images], conf=args.conf, verbose=False)):
            truth = read_boxes(DATA_ROOT / "train" / "labels" / (row["image"] + ".txt"))
            if not truth:
                continue  # clean-scene negatives are always kept
            predicted = [tuple(b) for b in result.boxes.xyxyn.tolist()]
            largest = max((b[2] - b[0]) * (b[3] - b[1]) for b in truth)
            scores[(row["source"], row["original"])].append((f1(truth, predicted), len(truth), len(predicted), largest))

    graded = []
    for (source, original), values in scores.items():
        mean_f1 = sum(v[0] for v in values) / len(values)
        if sum(v[2] for v in values) / len(values) < 0.5 and values[0][3] >= LARGE_PILE:
            continue  # a big labelled pile the model missed: the model is wrong, not the label
        graded.append((mean_f1, source, original, values[0][1], sum(v[2] for v in values) / len(values)))
    graded.sort()

    downloaded = [g for g in graded if g[1] != OWN_SLUG]
    limit = int(len(downloaded) * args.max_fraction)
    dropped = [g for g in downloaded if g[0] <= args.max_f1][:limit]
    own_flagged = [g for g in graded if g[1] == OWN_SLUG and g[0] <= args.max_f1]

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "excluded.txt").write_text(
        f"# Written by `python -m model.audit_labels` ({Path(args.weights).name}, F1 <= {args.max_f1}).\n"
        "# Training photos dropped by build_dataset as label errors. Delete a line to keep that photo.\n"
        + "".join(f"{source}/{original}\n" for _, source, original, _, _ in dropped),
        encoding="utf-8",
    )
    with (AUDIT_DIR / "review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["f1", "source", "original", "label_boxes", "model_boxes", "action"])
        for mean_f1, source, original, n_truth, n_pred in graded:
            if mean_f1 > args.max_f1:
                break
            action = "dropped" if (mean_f1, source, original, n_truth, n_pred) in dropped else (
                "check by hand" if source == OWN_SLUG else "kept (over limit)")
            writer.writerow([f"{mean_f1:.2f}", source, original, n_truth, f"{n_pred:.1f}", action])

    per_source = collections.Counter(g[1] for g in dropped)
    totals = collections.Counter(g[1] for g in downloaded)
    print(f"\nFlagged {len(dropped)} of {len(downloaded)} downloaded training photos (limit {limit}):")
    for source in sorted(totals):
        print(f"  {source:<28} {per_source[source]:>4} / {totals[source]}")
    if own_flagged:
        print(f"\n{len(own_flagged)} of our own photos disagree with the model — check them in Roboflow "
              f"(listed in {AUDIT_DIR / 'review.csv'}); they are not dropped.")
    print(f"\nWrote {AUDIT_DIR / 'excluded.txt'}. Rebuild with: python -m model.build_dataset")


if __name__ == "__main__":
    main()
