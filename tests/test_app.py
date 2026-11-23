"""End-to-end test of the API incl. edge cases. Starts its own server.

Run from the project folder (venv active):   python tests/test_app.py
Uses the LFW test data in experiments/data. Network access is blocked for the
server process (dead proxy) to prove it works offline.
"""
import csv
import io
import os
import subprocess
import sys
import time

import requests
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "experiments", "data")
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
fails = []


def check(cond, what):
    print(("PASS  " if cond else "FAIL  ") + what)
    if not cond:
        fails.append(what)


def jpg_bytes(img, **kw):
    b = io.BytesIO(); img.save(b, "JPEG", **kw); return b.getvalue()


def upload(sid, items):
    """items: [(filename, bytes)] -> response of /known"""
    files = [("files", (n, d, "application/octet-stream")) for n, d in items]
    return requests.post(f"{BASE}/api/session/{sid}/known", files=files, timeout=600)


env = dict(os.environ, HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9", PYTHONUTF8="1")
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                           "--port", str(PORT), "--log-level", "warning"], cwd=ROOT, env=env)
try:
    for _ in range(120):
        try:
            if requests.get(f"{BASE}/api/status", timeout=2).json()["ready"]:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise SystemExit("server did not become ready")
    check(True, "server started and models loaded (offline)")
    check(requests.get(BASE + "/").status_code == 200, "page is served at /")

    # ---------- known people: 50 good photos + edge cases
    sid = requests.post(f"{BASE}/api/session").json()["session_id"]
    folder = sorted(os.listdir(os.path.join(DATA, "folder")))
    items = [(n, open(os.path.join(DATA, "folder", n), "rb").read()) for n in folder]
    t = time.time()
    for i in range(0, len(items), 8):                       # batches of 8, like the page
        r = upload(sid, items[i:i + 8]).json()
    check(r["people"] == 50, f"50 known people loaded in {time.time() - t:.0f}s (got {r['people']})")

    group1 = open(os.path.join(DATA, "groups", "group1.jpg"), "rb").read()
    huge = jpg_bytes(Image.effect_noise((9000, 9000), 40).convert("RGB"), quality=30)
    edge = [
        ("Blank.jpg", jpg_bytes(Image.new("RGB", (400, 400), "white"))),     # no face
        ("Crowd.jpg", group1),                                                # several faces
        ("notes.txt", b"hello, this is not a picture"),                       # non-image
        ("fake.jpg", b"not really a jpg"),                                    # non-image with image name
        ("Empty.jpg", b""),                                                   # empty
        ("Bono.png", open(os.path.join(DATA, "folder", "Bono.jpg"), "rb").read()),  # duplicate name
        ("Huge.jpg", huge),                                                   # 81 megapixels
        ("sub/dir\\Ethan Hawke.jpg", open(os.path.join(DATA, "test_same", "Ethan Hawke.jpg"), "rb").read()),
    ]
    r = upload(sid, edge)
    check(r.status_code == 200, "edge-case batch does not crash")
    res = {x["file"]: x for x in r.json()["results"]}
    check(res["Blank.jpg"]["status"] == "skipped" and "no face" in res["Blank.jpg"]["note"], "photo with no face is skipped, with a message")
    check(res["Crowd.jpg"]["status"] == "ok" and "largest" in res["Crowd.jpg"]["note"], "photo with several faces uses the largest")
    check(res["notes.txt"]["status"] == "skipped" and "not a picture" in res["notes.txt"]["note"], "non-image file is skipped")
    check(res["fake.jpg"]["status"] == "skipped", "fake .jpg is skipped")
    check(res["Empty.jpg"]["status"] == "skipped" and "empty" in res["Empty.jpg"]["note"], "empty file is skipped")
    check("both are used" in res["Bono.png"]["note"], "duplicate name is noticed")
    print("      huge image ->", res["Huge.jpg"]["status"], res["Huge.jpg"]["note"][:70])
    check(res["Huge.jpg"]["status"] in ("ok", "skipped"), "81-megapixel image handled without crash")
    check(res["sub/dir\\Ethan Hawke.jpg"]["status"] == "ok", "path in file name is reduced to the person name")

    # ---------- group photo
    r = requests.post(f"{BASE}/api/session/{sid}/group", files={"file": ("group1.jpg", group1)}, timeout=600)
    check(r.status_code == 200, "group photo analysed")
    g = r.json()
    check(len(g["faces"]) == 11, f"group1: 11 faces (10 + 1 background) (got {len(g['faces'])})")
    check(g["image"].startswith("data:image/jpeg;base64,"), "processed image returned")
    answers = {}
    for row in csv.DictReader(open(os.path.join(DATA, "groups", "answers.csv"), encoding="utf-8")):
        if row["group_photo"] == "group1.jpg":
            answers[row["name"]] = row["in_folder"]
    named = [f["nearest"] for f in g["faces"] if f["distance"] <= 0.62]
    known_in_g1 = [n for n, v in answers.items() if v == "yes"]
    # "Crowd.jpg" (added above as an edge case) IS one of group1's faces, so that face matches "Crowd"
    missing = [n for n in known_in_g1 if n not in named]
    check(len(missing) <= 1 and (not missing or "Crowd" in named), f"at threshold 0.62 all known people of group1 are named (missing: {missing})")
    check(len(named) == len(known_in_g1), f"... and nobody else gets a name ({len(named)} named, {len(known_in_g1)} expected)")

    r = requests.post(f"{BASE}/api/session/{sid}/group",
                      files={"file": ("empty.jpg", jpg_bytes(Image.new("RGB", (800, 600), "gray")))})
    check(r.status_code == 200 and r.json()["faces"] == [], "group photo without faces -> empty list, no crash")
    r = requests.post(f"{BASE}/api/session/{sid}/group", files={"file": ("x.pdf", b"%PDF-1.4 hello")})
    check(r.status_code == 400 and "not a picture" in r.json()["detail"], "non-image group photo -> clear 400 message")
    r = requests.post(f"{BASE}/api/session/{sid}/group", files={"file": ("big.jpg", huge)}, timeout=600)
    check(r.status_code in (200, 400), "81-megapixel group photo handled")
    r = requests.post(f"{BASE}/api/session/nope/group", files={"file": ("g.jpg", group1)})
    check(r.status_code == 400 and "expired" in r.json()["detail"], "unknown session -> plain message")
    empty_sid = requests.post(f"{BASE}/api/session").json()["session_id"]
    r = requests.post(f"{BASE}/api/session/{empty_sid}/group", files={"file": ("g.jpg", group1)})
    check(r.status_code == 400 and "folder" in r.json()["detail"], "no known people yet -> plain message")
finally:
    server.terminate()
    server.wait(timeout=20)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
