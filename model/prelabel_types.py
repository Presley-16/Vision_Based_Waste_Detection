"""Suggest a waste type for every crop, so labelling means correcting rather than starting blank.

Uses CLIP zero-shot matching against the descriptions in waste_types.py. Unlike a
classifier trained on the public datasets, it can suggest construction rubble and
hazardous waste, which no downloaded dataset covers. Suggestions are only a starting
point: every crop still gets checked by a person before it is used for training or
evaluation.

Output (model/datasets/type_labelling/):
  roboflow_upload/<type>/<crop>.jpg   one folder per suggested type; upload as-is to a
                                      Roboflow classification project
  suggestions.csv                     crop, source, split, suggested type + confidence,
                                      runner-up, and needs_check for unsure crops

    python -m model.crop_detections   # first
    python -m model.prelabel_types
"""
import argparse
import csv
import shutil
from pathlib import Path

import open_clip
import torch
from PIL import Image

from model.waste_types import TYPE_NAMES, WASTE_TYPES

MODEL_DIR = Path(__file__).resolve().parent
LABEL_DIR = MODEL_DIR / "datasets" / "type_labelling"


@torch.no_grad()
def type_embeddings(model, tokenizer, device) -> torch.Tensor:
    """One averaged, normalised text embedding per waste type."""
    rows = []
    for name in TYPE_NAMES:
        tokens = tokenizer(WASTE_TYPES[name]["prompts"]).to(device)
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
        mean = embedding.mean(dim=0)
        rows.append(mean / mean.norm())
    return torch.stack(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="ViT-B-32")
    parser.add_argument("--pretrained", default="laion2b_s34b_b79k")
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--check-below", type=float, default=0.5,
                        help="Mark crops whose top suggestion is below this confidence as needs_check")
    args = parser.parse_args()

    crops_csv = LABEL_DIR / "crops.csv"
    if not crops_csv.exists():
        raise FileNotFoundError(f"{crops_csv} not found. Run `python -m model.crop_detections` first.")
    with open(crops_csv, newline="", encoding="utf-8") as f:
        crops = list(csv.DictReader(f))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(args.model, pretrained=args.pretrained, device=device)
    model.eval()
    text = type_embeddings(model, open_clip.get_tokenizer(args.model), device)

    upload_dir = LABEL_DIR / "roboflow_upload"
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    results = []
    for start in range(0, len(crops), args.batch):
        batch = crops[start:start + args.batch]
        images = torch.stack([preprocess(Image.open(LABEL_DIR / "crops" / c["crop"]).convert("RGB")) for c in batch]).to(device)
        with torch.no_grad():
            features = model.encode_image(images)
            features = features / features.norm(dim=-1, keepdim=True)
            probs = (100.0 * features @ text.T).softmax(dim=-1).cpu()
        for crop, p in zip(batch, probs):
            top = p.topk(2)
            first, second = TYPE_NAMES[top.indices[0]], TYPE_NAMES[top.indices[1]]
            results.append({
                "crop": crop["crop"], "source": crop["source"], "split": crop["split"],
                "suggested": first, "confidence": round(float(top.values[0]), 3),
                "runner_up": second, "runner_up_confidence": round(float(top.values[1]), 3),
                "needs_check": int(float(top.values[0]) < args.check_below),
            })
            # Flat file names (source prefix kept) so Roboflow sees one image per crop.
            destination = upload_dir / first / crop["crop"].replace("/", "__")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(LABEL_DIR / "crops" / crop["crop"], destination)
        print(f"  {min(start + args.batch, len(crops))}/{len(crops)}", end="\r")

    results.sort(key=lambda r: r["confidence"])  # least sure first: check those first
    with open(LABEL_DIR / "suggestions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSuggested types for {len(results)} crops -> {upload_dir}")
    for name in TYPE_NAMES:
        chosen = [r for r in results if r["suggested"] == name]
        unsure = sum(r["needs_check"] for r in chosen)
        print(f"  {name:20} {len(chosen):5}   ({unsure} unsure)")


if __name__ == "__main__":
    main()
