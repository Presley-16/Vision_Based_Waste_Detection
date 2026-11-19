# Dissertation results and figures

Everything behind the numbers and figures in Chapter 4 of
`Nyama_N02539164N_MScCompSci_Dissertation_v1.docx` (updated 18 November 2026 for the
deployed M4 detector and the waste-type classifier). Run the commands from the repo root.

| File | What it is |
| --- | --- |
| `scores.json` | M1–M4 on the version-4 dataset: box metrics on the test split, every valid/test photo's highest box confidence, speed |
| `stats.txt` | Output of `stats.py`: Tables 4.3–4.7 and D.1 (confusion counts, Wilson CIs, McNemar, threshold sweeps, per source, Zimbabwe photos) |
| `M4_BoxPR_curve.png`, `M4_confusion_matrix.png` | Ultralytics validator plots for M4 on the test split (Figure 4.4) |
| `fp_sheet.jpg` | Highest-scoring "no-waste" validation photos accepted by M4, several are mislabelled waste (Section 4.5.1) |
| `own_errors.jpg` | M4's Zimbabwe-photo errors: missed litter in grass, accepted meme screenshot, and the dark photo M3 accepted (Section 4.5.2) |
| `../figures/` | All figures used in the dissertation, at the numbers they have in the document |

## Regenerating

```
venv/Scripts/python.exe dissertation/analysis/score_models.py   # ~15 min; needs the GPU; rewrites scores.json
venv/Scripts/python.exe dissertation/analysis/stats.py > dissertation/analysis/stats.txt
venv/Scripts/python.exe dissertation/analysis/charts.py         # Figures 4.1-4.3, 4.5, 4.6, 4.7
venv/Scripts/python.exe dissertation/analysis/diagrams.py       # Figures 2.1, 3.1, 3.2
```

`score_models.py` expects the four detectors in `model/weights/`: `best_v1_map40.pt` (M1),
`best_v2_map43.pt` (M2), `best_dissertation_v1.pt` (M3) and `best.pt` (M4).
The classifier figures read `model/runs/classify/` (from `model.train_classifier` and
`model.evaluate_classifier`); the M4 training curve reads `model/runs/detect/waste_v4_rubble/`.

### End-to-end latency (Table 4.13)

```
venv/Scripts/python.exe dissertation/analysis/latency.py                          # GPU
CUDA_VISIBLE_DEVICES=-1 venv/Scripts/python.exe dissertation/analysis/latency.py  # CPU (-1, not empty)
```

Posts 20 waste and 10 clean test photos (fixed random sample, seed 0) through the real Flask
app with a scratch database and alerts switched off. Results recorded for the dissertation:

| Device | Waste mean / median / p95 (ms) | Clean mean / median / p95 (ms) | First request | Accepted / rejected |
| --- | --- | --- | --- | --- |
| CPU | 122 / 123 / 139 | 92 / 92 / 117 | 3.8 s | 20/20 waste, 10/10 clean |
| GPU | 55 / 58 / 72 | 31 / 26 / 45 | 4.8 s | 20/20 waste, 10/10 clean |

### Dashboard screenshot (Figure 4.8a)

`screenshot.py` submits three photos to a scratch database and photographs the municipal
dashboard in Microsoft Edge. It needs Playwright, which is not in the project venv:
`pip install playwright` (it uses the installed Edge, so no browser download is needed).
