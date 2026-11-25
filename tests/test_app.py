"""End-to-end test of the API incl. edge cases and naming unknown faces. Starts its own server.

Run from the project folder (venv active):   python tests/test_app.py
Uses the LFW test data in experiments/data. Network access is blocked for the
server process (dead proxy) to prove it works offline. Saved faces go to a
temporary file, so the real data/learned_faces.json is never touched.
"""
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

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


def new_session(names=(), folder="folder"):
    """A new session with these folder photos loaded."""
    sid = requests.post(f"{BASE}/api/session").json()["session_id"]
    items = [(n + ".jpg", read(folder, n + ".jpg")) for n in names]
    for i in range(0, len(items), 8):
        upload(sid, items[i:i + 8])
    return sid


def read(*parts):
    with open(os.path.join(DATA, *parts), "rb") as f:
        return f.read()


def scan(sid, data):
    r = requests.post(f"{BASE}/api/session/{sid}/group", files={"file": ("g.jpg", data)}, timeout=600)
    r.raise_for_status()
    return r.json()


def label(sid, analysis_id, face_id, name):
    return requests.post(f"{BASE}/api/session/{sid}/label", timeout=60,
                         json={"analysis_id": analysis_id, "face_id": face_id, "name": name})


def people():
    return requests.get(f"{BASE}/api/people", timeout=60)


def forget(name):
    return requests.delete(f"{BASE}/api/people", params={"name": name}, timeout=60)


def rejected(r, word):
    return r.status_code == 400 and word in r.json()["detail"].lower()


def stored():
    if not os.path.exists(LEARNED):
        return []
    with open(LEARNED, encoding="utf-8") as f:
        return json.load(f)


def file_bytes(p):
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return f.read()


def start_server():
    env = dict(os.environ, HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9", PYTHONUTF8="1",
               FACE_LEARNED_FILE=LEARNED)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                             "--port", str(PORT), "--log-level", "critical"], cwd=ROOT, env=env)
    for _ in range(120):
        try:
            if requests.get(f"{BASE}/api/status", timeout=2).json()["ready"]:
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.terminate()
    raise SystemExit("server did not become ready")


def stop_server(proc):
    proc.terminate()
    proc.wait(timeout=20)


TMP = tempfile.mkdtemp(prefix="face_test_")
LEARNED = os.path.join(TMP, "learned_faces.json")
REAL = os.path.join(ROOT, "data", "learned_faces.json")
real_before = file_bytes(REAL)
server = start_server()
try:
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

    # ==================== naming an unknown face ("This is...") ====================
    print("\n--- naming unknown faces ---")
    check(not os.path.exists(LEARNED), "scanning alone saves nothing (no store file yet)")
    # `held_out` are people of group1 who are NOT put in this folder, so their faces are unknown at first.
    # We know which face is whose from the full-folder scan `g` above (face order is the same every scan).
    held_out = {f["nearest"]: f["id"] for f in g["faces"] if f["distance"] <= 0.62 and f["nearest"] in known_in_g1}
    person = "Eddy Merckx" if "Eddy Merckx" in held_out else sorted(held_out)[0]
    target = held_out[person]
    small = [n[:-4] for n in folder if n[:-4] not in answers][:10]
    sid = new_session(small)

    r = requests.post(f"{BASE}/api/session/{sid}/group", files={"file": ("g.jpg", group1)}, timeout=600)
    first = r.json()
    check(isinstance(first.get("analysis_id"), str) and len(first["analysis_id"]) >= 32, "scan returns a random analysis_id")
    check("embedding" not in r.text and all(set(f) == {"id", "box", "nearest", "distance"} for f in first["faces"]),
          "no embeddings are sent to the browser")
    check(all(f["distance"] > 0.62 for f in first["faces"]), f"with this folder every face starts as Unknown ({person} is face {target})")

    # ---------- rejected requests (5)
    aid = first["analysis_id"]
    check(rejected(label(sid, aid, 999, "A Name"), "face"), "unknown face_id (999) rejected")
    check(all(rejected(label(sid, aid, x, "A Name"), "face") for x in (0, -1, str(target), None, True, 1.5, [1])),
          "wrong kinds of face_id rejected")
    check(rejected(label(sid, aid, target, ""), "name") and rejected(label(sid, aid, target, "   "), "name"), "empty name rejected")
    check(rejected(label(sid, aid, target, "x" * 81), "too long"), "81-character name rejected")
    check(all(rejected(label(sid, aid, target, x), "unknown") for x in ("unknown", "Unknown", "  UNKNOWN  ")),
          "'unknown' in any casing rejected")
    check(all(rejected(label(sid, aid, target, x), "characters") for x in ("a\nb", "a\tb", "a\x00b", "a\u2028b")),
          "control characters and line breaks rejected")
    check(all(rejected(label(sid, aid, target, x), "name") for x in (None, 5, ["a"], "\u200b")), "missing or non-text name rejected")
    check(rejected(requests.post(f"{BASE}/api/session/{sid}/label", json=[1, 2]), "request"), "wrong request shape -> plain message")
    check(rejected(label("nope", aid, target, "A Name"), "expired"), "label on an expired session rejected")
    second = scan(sid, group1)
    check(second["analysis_id"] != aid and rejected(label(sid, aid, target, "A Name"), "out of date"), "old analysis_id rejected after a new scan")
    check(rejected(label(empty_sid, aid, target, "A Name"), "out of date"), "another session's analysis_id rejected")
    check(not os.path.exists(LEARNED), "none of the rejected requests saved anything")

    # ---------- label, fix a typo (6)
    aid = second["analysis_id"]
    typo = "  " + person[:-1] + "  "
    r = label(sid, aid, target, typo)
    check(r.status_code == 200 and r.json()["name"] == person[:-1] and len(stored()) == 1, "face labelled (name is trimmed)")
    first_id = stored()[0]["id"]
    r = label(sid, aid, target, person.lower())
    check(r.status_code == 200 and len(stored()) == 1 and stored()[0]["id"] == first_id and stored()[0]["name"] == person.lower(),
          "labelling the same face again replaces the entry (no second one)")
    r = label(sid, aid, target, person)
    check(len(stored()) == 1 and stored()[0]["name"] == person and r.json()["name"] == person,
          "a capital-letter typo can be fixed the same way")
    entry = stored()[0]
    check(set(entry) == {"id", "name", "embedding", "model", "added"} and len(entry["embedding"]) == 512
          and entry["model"] == "uniface:arcface_resnet", f"stored: id, name, embedding, model, date only (model {entry['model']})")
    check(os.listdir(TMP) == ["learned_faces.json"], "only the one file is written (no photos, no temporary files left)")

    # ---------- same photo again (1) and the other faces (4)
    again = scan(sid, group1)
    t_face = again["faces"][target - 1]
    check(t_face["nearest"] == person and t_face["distance"] < 0.001,
          f"same photo again: face {target} is {t_face['nearest']}, distance {t_face['distance']}")
    others = [f for f in again["faces"] if f["id"] != target]
    wrong = [(f["id"], f["distance"]) for f in others if f["nearest"] == person and f["distance"] <= 0.62]
    closest = min(f["distance"] for f in others if f["nearest"] == person) if any(f["nearest"] == person for f in others) else None
    check(not wrong, f"none of the other {len(others)} faces gets the new name at 0.62 (closest other: {closest})")

    # ---------- survives a restart (2), different photo (3)
    stop_server(server)
    server = start_server()
    check(people().json() == {"people": [{"name": person, "samples": 1}]}, "saved name is listed after a server restart")
    sid = new_session(small)
    r1 = scan(sid, group1)["faces"][target - 1]
    check(r1["nearest"] == person and r1["distance"] < 0.001, "recognised in a new session after a server restart")
    # the collage faces are the test_same photos (see prepare_lfw.py), so the DIFFERENT photo is the one in folder/,
    # which this session did not load
    other_photo = scan(sid, read("folder", person + ".jpg"))["faces"]
    best = min(other_photo, key=lambda f: f["distance"])
    verdict = "within" if best["distance"] <= 0.62 else "ABOVE (would show as Unknown at)"
    print(f"      different photo of {person}: nearest {best['nearest']}, distance {best['distance']} -> {verdict} 0.62")
    check(best["nearest"] == person, "a different photo of the same person is matched to the saved name")

    # ---------- spelling reuse, several samples, listing and delete (6)
    third = scan(sid, group1)
    second_face = next(f for n, f in held_out.items() if n != person)
    r = label(sid, third["analysis_id"], second_face, person.upper())
    check(r.json()["name"] == person and people().json()["people"] == [{"name": person, "samples": 2}],
          "an existing saved name is reused with its spelling; two samples are kept separately")
    third_face = next(x["id"] for x in third["faces"] if x["id"] not in (target, second_face))
    r = label(sid, third["analysis_id"], third_face, small[0].upper())
    check(r.json()["name"] == small[0], "an existing folder name is reused with its spelling")
    check(rejected(forget("Nobody At All"), "no saved person") and rejected(forget(""), "no saved person"), "deleting an unsaved name -> plain message")
    r = forget(person.upper())
    check(r.status_code == 200 and r.json()["removed"] == 2 and [p["name"] for p in people().json()["people"]] == [small[0]],
          "delete removes every sample of that name and nothing else")
    f = scan(sid, group1)["faces"][target - 1]
    check(f["nearest"] != person and f["distance"] > 0.62, "after deleting the name the face is Unknown again")
    forget(small[0])
    check(stored() == [], "store is empty after deleting everything")

    # ---------- several saves at the same moment
    now = scan(sid, group1)
    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(lambda x: label(sid, now["analysis_id"], x["id"], f"Parallel {x['id']}").status_code, now["faces"]))
    check(codes == [200] * 11 and sorted(e["name"] for e in stored()) == sorted(f"Parallel {i}" for i in range(1, 12)),
          "11 saves sent at once are all kept")

    # ---------- entries from another recognition model are ignored, and kept
    os.remove(LEARNED)
    now = scan(sid, group1)
    label(sid, now["analysis_id"], target, "Old Model Person")
    entries = stored()
    entries[0]["model"] = "some-other-model"
    with open(LEARNED, "w", encoding="utf-8") as fh:
        json.dump(entries, fh)
    f = scan(sid, group1)["faces"][target - 1]
    check(f["nearest"] != "Old Model Person" and people().json()["people"] == [], "entry made with another model is ignored")
    now = scan(sid, group1)
    label(sid, now["analysis_id"], target, person)
    check([e["model"] for e in stored()] == ["some-other-model", "uniface:arcface_resnet"], "...and is not thrown away by a later save")

    # ---------- how far is a different photo, for every held-out person (report only)
    os.remove(LEARNED)
    now = scan(sid, group1)
    for n, fid in held_out.items():
        label(sid, now["analysis_id"], fid, n)
    results = []
    for n in sorted(held_out):
        b = min(scan(sid, read("folder", n + ".jpg"))["faces"], key=lambda x: x["distance"])
        results.append((n, b["nearest"], b["distance"]))
    print("      saved from group1, then matched against a different photo of the same person:")
    for n, got, d in results:
        print(f"        {n:28s} -> {got:28s} {d:.4f} {'' if d <= 0.62 else 'ABOVE 0.62'}")
    good = sum(got == n and d <= 0.62 for n, got, d in results)
    print(f"      {good} of {len(results)} would be named at the default 0.62")

    # ---------- damaged store file (7)
    for what, bad in (("not JSON", b"{this is not json"), ("wrong shape", b'{"faces": []}'),
                      ("half an entry", b'[{"id": "1", "name": "A"}]'), ("empty file", b""), ("not text", b"\xff\xfe\x00\x81")):
        with open(LEARNED, "wb") as fh:
            fh.write(bad)
        now = scan(sid, group1)                          # still works, from the folder only
        answers_ok = [rejected(x, "damaged") for x in (people(), label(sid, now["analysis_id"], target, "A Name"), forget("A"))]
        check(all(answers_ok) and "damaged" in now["warning"] and len(now["faces"]) == 11 and file_bytes(LEARNED) == bad,
              f"damaged store ({what}): reported, scan still works, file left unchanged")
    os.remove(LEARNED)
    os.mkdir(LEARNED)                                    # a folder where the file should be: cannot be read
    check(rejected(people(), "cannot be read") and os.path.isdir(LEARNED), "unreadable store: reported and left alone")
    os.rmdir(LEARNED)
    check(scan(sid, group1)["warning"] == "" and people().json() == {"people": []}, "once the bad file is removed all is normal")
    check(file_bytes(REAL) == real_before, "the real data/learned_faces.json was not touched")
finally:
    stop_server(server)
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
