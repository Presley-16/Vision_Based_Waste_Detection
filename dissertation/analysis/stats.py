import json, math, sys
from math import comb
from collections import defaultdict
from pathlib import Path
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent / "scores.json"))
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-h)/d, (c+h)/d)
def cm(photos, t):
    tp = sum(p["waste"] and p["score"] >= t for p in photos); fn = sum(p["waste"] and p["score"] < t for p in photos)
    fp = sum((not p["waste"]) and p["score"] >= t for p in photos); tn = sum((not p["waste"]) and p["score"] < t for p in photos)
    return tp, fn, fp, tn
def metrics(photos, t):
    tp, fn, fp, tn = cm(photos, t); n = tp+fn+fp+tn
    P = tp/(tp+fp) if tp+fp else 1.0; R = tp/(tp+fn); S = tn/(tn+fp)
    return dict(tp=tp, fn=fn, fp=fp, tn=tn, n=n, acc=(tp+tn)/n, p=P, r=R, s=S, f1=2*P*R/(P+R),
                acc_ci=wilson(tp+tn, n), p_ci=wilson(tp, tp+fp), r_ci=wilson(tp, tp+fn), s_ci=wilson(tn, tn+fp))
def fmt(m):
    return (f"TP/FN/FP/TN {m['tp']}/{m['fn']}/{m['fp']}/{m['tn']} acc {m['acc']:.3f} [{m['acc_ci'][0]:.3f},{m['acc_ci'][1]:.3f}] "
            f"P {m['p']:.3f} [{m['p_ci'][0]:.3f},{m['p_ci'][1]:.3f}] R {m['r']:.3f} [{m['r_ci'][0]:.3f},{m['r_ci'][1]:.3f}] "
            f"S {m['s']:.3f} [{m['s_ci'][0]:.3f},{m['s_ci'][1]:.3f}] F1 {m['f1']:.3f}")
def mcnemar(a, b, t):
    ca = [(p["score"] >= t) == p["waste"] for p in a]; cb = [(p["score"] >= t) == p["waste"] for p in b]
    b_only = sum(y and not x for x, y in zip(ca, cb)); a_only = sum(x and not y for x, y in zip(ca, cb))
    n = a_only + b_only; k = min(a_only, b_only)
    pval = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0
    return b_only, a_only, pval
T = 0.25
NEW = {"garbage-identification"}
rubble_test = lambda p: p["source"] == "planetwatch-own" and p["image"] in RUB
RUB = {p["image"] for p in D["M4"]["test"] if p["source"]=="planetwatch-own"}
print("== Test split, tau 0.25")
for m in D:
    t = D[m]["test"]; print(m, len(t), fmt(metrics(t, T)))
print("== Old 217-photo subset (sanity: excludes garbage-identification and the new rubble test photo)")
import re
for m in D:
    t = [p for p in D[m]["test"] if p["source"] not in NEW and "fa8dadf48084" not in p["image"]]
    print(m, len(t), fmt(metrics(t, T)))
print("== McNemar")
for a, b in (("M1","M2"),("M2","M3"),("M3","M4")):
    print(a, "->", b, "b right only, a right only, p =", mcnemar(D[a]["test"], D[b]["test"], T))
print("== Box")
for m in D: print(m, {k: round(v,3) for k,v in D[m]["box"].items()}, "boxes", D[m]["boxes"], "params", round(D[m]["params_m"],1), "gpu", round(D[m]["gpu_ms"],1), "cpu", round(D[m]["cpu_ms"],1), "MB", round(D[m]["size_mb"],1))
TH = (0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.60)
for split in ("valid","test"):
    for m in ("M2","M3","M4"):
        ph = D[m][split]; print(f"== {split} sweep {m} (n={len(ph)}, waste={sum(p['waste'] for p in ph)})")
        for t in TH:
            x = metrics(ph, t); print(f"  {t:.2f} {x['tp']}/{x['fn']}/{x['fp']}/{x['tn']} acc {x['acc']:.3f} P {x['p']:.3f} R {x['r']:.3f} S {x['s']:.3f} F1 {x['f1']:.3f}")
v = D["M4"]["valid"]
best = max((round(0.05+0.01*i,2) for i in range(60)), key=lambda t: metrics(v,t)["p"]); chosen = 0.25; print("M4 max valid precision", best, metrics(v,best)["p"])
print("M4 rule (lowest tau with valid precision >= 0.99, step 0.01):", chosen, fmt(metrics(v, chosen)))

for m in ("M3","M4"):
    print(f"== per source {m} test")
    g = defaultdict(list)
    for p in D[m]["test"]: g[p["source"]].append(p)
    for s, ph in sorted(g.items(), key=lambda kv: -len(kv[1])):
        c = sum((p["score"] >= T) == p["waste"] for p in ph); print(f"  {s:28} {len(ph):4} {c:4} {c/len(ph):.3f}")
    vt = D[m]["valid"] + D[m]["test"]
    for name, sel in (("own waste", lambda p: p["source"]=="planetwatch-own" and p["waste"]),
                      ("own clean", lambda p: p["source"]=="negatives-own"),
                      ("coco", lambda p: p["source"]=="coco-negatives")):
        ph = [p for p in vt if sel(p)]; c = sum((p["score"] >= T) == p["waste"] for p in ph); lo, hi = wilson(c, len(ph))
        print(f"  valid+test {name}: {c}/{len(ph)} {c/len(ph):.3f} [{lo:.3f},{hi:.3f}]")
        if name != "coco":
            print("     wrong:", [(p["image"], round(p["score"],2)) for p in ph if (p["score"] >= T) != p["waste"]])
