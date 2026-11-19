"""Score the waste-type classifier on the held-out test crops.

Reports what the dissertation needs, separately for our own Zimbabwe crops and the
downloaded ones: accuracy, top-2 accuracy, per-type precision / recall / F1, and the
confusion matrix (which types get mistaken for which).

    python -m model.evaluate_classifier
    python -m model.evaluate_classifier --weights model/runs/classify/waste_type2/weights/best.pt

Writes model/runs/classify/evaluation/{per_type.csv, confusion.csv, predictions.csv}.
"""
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from ultralytics import YOLO

from model.build_classification import OWN_SOURCES
from model.waste_types import TYPE_NAMES

MODEL_DIR = Path(__file__).resolve().parent


def scores(rows: list[dict]) -> tuple[dict, dict]:
    """Overall numbers and per-type precision/recall/F1 for a list of prediction rows."""
    total = len(rows)
    overall = {
        "crops": total,
        "accuracy": sum(r["true"] == r["predicted"] for r in rows) / total if total else 0.0,
        "top2_accuracy": sum(r["true"] in (r["predicted"], r["second"]) for r in rows) / total if total else 0.0,
    }
    per_type = {}
    for waste_type in TYPE_NAMES:
        tp = sum(r["true"] == waste_type and r["predicted"] == waste_type for r in rows)
        predicted = sum(r["predicted"] == waste_type for r in rows)
        actual = sum(r["true"] == waste_type for r in rows)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_type[waste_type] = {"support": actual, "precision": precision, "recall": recall, "f1": f1}
    overall["macro_f1"] = sum(v["f1"] for v in per_type.values() if v["support"]) / max(1, sum(1 for v in per_type.values() if v["support"]))
    return overall, per_type


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights", default=str(MODEL_DIR / "weights" / "waste_type.pt"))
    parser.add_argument("--data", default=str(MODEL_DIR / "datasets" / "WasteTypes"))
    parser.add_argument("--out", default=str(MODEL_DIR / "runs" / "classify" / "evaluation"))
    args = parser.parse_args()

    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(data / "manifest.csv", newline="", encoding="utf-8") as f:
        test = [m for m in csv.DictReader(f) if m["split"] == "test"]

    model = YOLO(args.weights)
    rows = []
    for start in range(0, len(test), 64):
        batch = test[start:start + 64]
        for item, result in zip(batch, model.predict([str(data / m["file"]) for m in batch], verbose=False)):
            top = result.probs.top5
            rows.append({"file": item["file"], "source": item["source"], "true": item["type"],
                         "predicted": result.names[top[0]], "second": result.names[top[1]],
                         "confidence": round(float(result.probs.top1conf), 3)})

    groups = {"all test crops": rows,
              "own Zimbabwe crops": [r for r in rows if r["source"] in OWN_SOURCES],
              "downloaded crops": [r for r in rows if r["source"] not in OWN_SOURCES]}
    per_type_rows = []
    for name, group in groups.items():
        if not group:
            print(f"\n{name}: none in the test split")
            continue
        overall, per_type = scores(group)
        print(f"\n{name}: {overall['crops']} crops   accuracy {overall['accuracy']:.1%}   "
              f"top-2 {overall['top2_accuracy']:.1%}   macro F1 {overall['macro_f1']:.3f}")
        print(f"  {'type':22}{'n':>5}{'precision':>11}{'recall':>8}{'F1':>7}")
        for waste_type, s in per_type.items():
            print(f"  {waste_type:22}{s['support']:>5}{s['precision']:>11.2f}{s['recall']:>8.2f}{s['f1']:>7.2f}")
            per_type_rows.append({"group": name, "type": waste_type, **{k: round(v, 4) for k, v in s.items()}})

    confusion = defaultdict(Counter)
    for r in rows:
        confusion[r["true"]][r["predicted"]] += 1
    with open(out / "confusion.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["true \\ predicted", *TYPE_NAMES])
        for waste_type in TYPE_NAMES:
            writer.writerow([waste_type, *(confusion[waste_type][p] for p in TYPE_NAMES)])
    with open(out / "per_type.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_type_rows[0]))
        writer.writeheader()
        writer.writerows(per_type_rows)
    with open(out / "predictions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nConfusion matrix, per-type scores and every prediction: {out}")


if __name__ == "__main__":
    main()
