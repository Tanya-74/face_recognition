"""Full evaluation of ONE library wrapper (tests A-D + threshold sweep).

Usage: <venv python> experiments/evaluate.py wrap_uniface
Writes to experiments/results/:
  <lib>_timing.csv      time per image + faces found, every image
  <lib>_probes.csv      for every probe face: nearest folder person + distance (raw, no threshold)
  <lib>_testC.csv       faces detected per group photo (out of 10)
  <lib>_sweep.csv       one row per threshold with the results of tests A, B, D
Rule used everywhere: nearest folder person; if distance <= threshold the
probe gets that name, otherwise it is "Unknown".
"""
import csv, glob, importlib, os, sys, time
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
w = importlib.import_module(sys.argv[1])
LIB = w.NAME
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "results")
TILE, COLS, N_POS = 250, 5, 10
THRESHOLDS = [round(t, 3) for t in np.arange(0.10, 0.9001, 0.025)]


def name_of(path):
    return os.path.splitext(os.path.basename(path))[0]


def area(f):
    return f[0][2] * f[0][3]


timing = []   # rows: test, image, faces, seconds


def run(test, path):
    img = cv2.imread(path)
    t = time.time(); faces = w.get_faces(img); dt = time.time() - t
    timing.append([test, os.path.relpath(path, DATA).replace("\\", "/"), len(faces), round(dt, 3)])
    return faces


def biggest(faces):
    return max(faces, key=area)[1] if faces else None


# warm-up so model loading is not counted in the per-image times
w.get_faces(cv2.imread(sorted(glob.glob(os.path.join(DATA, "folder", "*.jpg")))[0]))

# ---- reference set: one embedding per person in folder/ (largest face in the photo)
ref_names, ref_embs = [], []
for p in sorted(glob.glob(os.path.join(DATA, "folder", "*.jpg"))):
    e = biggest(run("folder", p))
    if e is not None:
        ref_names.append(name_of(p)); ref_embs.append(e)
print(f"reference people with a face: {len(ref_names)} / 50", flush=True)


def nearest(emb):
    d = [w.distance(emb, r) for r in ref_embs]
    i = int(np.argmin(d))
    return ref_names[i], d[i]


probes = []   # dict rows for probes.csv ; also used for sweep


def add_probe(test, image, truth, emb, extra=""):
    if emb is None:
        probes.append(dict(test=test, image=image, truth=truth, nearest="", dist="", note="no face detected"))
    else:
        n, d = nearest(emb)
        probes.append(dict(test=test, image=image, truth=truth, nearest=n, dist=round(d, 4), note=extra))


# ---- test A: test_same ; test B: test_unknown
for p in sorted(glob.glob(os.path.join(DATA, "test_same", "*.jpg"))):
    add_probe("A", "test_same/" + os.path.basename(p), name_of(p), biggest(run("test_same", p)))
for p in sorted(glob.glob(os.path.join(DATA, "test_unknown", "*.jpg"))):
    add_probe("B", "test_unknown/" + os.path.basename(p), "Unknown", biggest(run("test_unknown", p)))

# ---- tests C and D: groups
answers = {}
with open(os.path.join(DATA, "groups", "answers.csv"), encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        answers[(r["group_photo"], int(r["position"]))] = (r["name"], r["in_folder"] == "yes")

testC = []
for p in sorted(glob.glob(os.path.join(DATA, "groups", "group*.jpg"))):
    g = os.path.basename(p)
    faces = run("groups", p)
    cells = {}
    for f in faces:
        x, y, bw, bh = f[0]
        cell = int((y + bh / 2) // TILE) * COLS + int((x + bw / 2) // TILE) + 1
        cells.setdefault(cell, []).append(f)
    found = sum(1 for c in range(1, N_POS + 1) if c in cells)
    extra = len(faces) - found
    testC.append([LIB, g, len(faces), found, N_POS, extra])
    for c in range(1, N_POS + 1):
        truth = answers[(g, c)][0] if answers[(g, c)][1] else "Unknown"
        if c in cells:
            main = max(cells[c], key=area)
            add_probe("D", g, f"{truth}|pos{c}|{answers[(g, c)][0]}", main[1])
            for o in cells[c]:
                if o is not main:
                    add_probe("D_extra", g, f"extra|pos{c}", o[1], "second face in same cell (background person)")
        else:
            add_probe("D", g, f"{truth}|pos{c}|{answers[(g, c)][0]}", None)

# ---- save raw tables
def save(name, header, rows):
    with open(os.path.join(OUT, f"{LIB}_{name}.csv"), "w", newline="", encoding="utf-8") as fh:
        cw = csv.writer(fh); cw.writerow(header); cw.writerows(rows)

save("timing", ["test_set", "image", "faces_found", "seconds"], timing)
save("probes", ["test", "image", "truth", "nearest", "dist", "note"],
     [[r["test"], r["image"], r["truth"], r["nearest"], r["dist"], r["note"]] for r in probes])
save("testC", ["library", "group_photo", "faces_detected_total", "positions_with_a_face", "expected", "extra_faces"], testC)

# ---- threshold sweep
rows = []
for t in THRESHOLDS:
    row = dict(threshold=t)
    # A
    A = [r for r in probes if r["test"] == "A"]
    ok = wrong = unk = nof = 0
    for r in A:
        if r["dist"] == "": nof += 1
        elif r["dist"] > t: unk += 1
        elif r["nearest"] == r["truth"]: ok += 1
        else: wrong += 1
    row.update(A_correct=ok, A_wrong_name=wrong, A_said_unknown=unk, A_no_face=nof, A_total=len(A))
    # B
    B = [r for r in probes if r["test"] == "B"]
    fm = sum(1 for r in B if r["dist"] != "" and r["dist"] <= t)
    row.update(B_false_matches=fm, B_correct_unknown=len(B) - fm, B_total=len(B))
    # D (10 positions per photo)
    D = [r for r in probes if r["test"] == "D"]
    cn = cu = wn = mk = nd = 0   # correct name, correct unknown, wrong name, known said Unknown, not detected
    for r in D:
        truth, _, real = r["truth"].split("|")
        if r["dist"] == "": nd += 1; continue
        named = r["dist"] <= t
        if truth == "Unknown":
            if named: wn += 1
            else: cu += 1
        else:
            if not named: mk += 1
            elif r["nearest"] == real: cn += 1
            else: wn += 1
    ex = [r for r in probes if r["test"] == "D_extra"]
    ex_named = sum(1 for r in ex if r["dist"] != "" and r["dist"] <= t)
    row.update(D_correct_names=cn, D_correct_unknown=cu, D_wrong_names=wn,
               D_known_missed_as_unknown=mk, D_not_detected=nd, D_total=len(D),
               D_extra_faces=len(ex), D_extra_faces_given_a_name=ex_named)
    rows.append(row)
save("sweep", list(rows[0].keys()), [list(r.values()) for r in rows])

times = [r[3] for r in timing if r[0] != "folder" or True]
print(f"{LIB}: median {np.median(times):.2f}s/image, mean {np.mean(times):.2f}s over {len(times)} images")
print("done; files in", OUT)
