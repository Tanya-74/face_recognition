"""Quick smoke test of ONE wrapper (run with that library's own venv python).

Usage: <venv python> experiments/smoke_test.py wrap_deepface
Prints one CSV row per image: library, image, faces, seconds (after a warm-up
call, so model loading is not counted) and appends to results/smoke_test.csv.
Run it with network blocked (dead proxy) to prove offline operation.
"""
import csv, importlib, os, sys, time
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
w = importlib.import_module(sys.argv[1])
IMGS = ["data/folder/Bono.jpg", "data/test_same/Bono.jpg", "data/groups/group1.jpg"]
imgs = {p: cv2.imread(os.path.join(HERE, p)) for p in IMGS}

t = time.time(); w.get_faces(imgs[IMGS[0]]); warm = time.time() - t   # warm-up (model load)
rows, embs = [], {}
for p in IMGS:
    t = time.time(); f = w.get_faces(imgs[p]); dt = time.time() - t
    embs[p] = f[0][1] if f else None
    rows.append([w.NAME, p, len(f), len(f[0][1]) if f else 0, round(dt, 2), round(warm, 1)])
same = w.distance(embs[IMGS[0]], embs[IMGS[1]])
print(f"{w.NAME}: warmup/model-load {warm:.1f}s  same-person dist {same:.3f}")
for r in rows: print(r)
out = os.path.join(HERE, "results", "smoke_test.csv")
new = not os.path.exists(out)
with open(out, "a", newline="") as fh:
    cw = csv.writer(fh)
    if new: cw.writerow(["library", "image", "faces_found", "embedding_dim", "seconds", "warmup_seconds"])
    cw.writerows(rows)
