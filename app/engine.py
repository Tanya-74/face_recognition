"""Core logic: prepare images, keep the known-people embeddings, match faces.

No web code here. The face library is used only through two functions
(get_faces, distance) from face_backend, so it can be swapped.
"""
import base64
import io
import os
import re
import threading
import uuid
from collections import OrderedDict

import numpy as np
from PIL import Image, ImageOps

import face_backend as backend

MAX_SIDE = 1600                  # bigger pictures are shrunk to this before processing
MAX_PIXELS = 120_000_000         # refuse absurd pictures (would eat all memory)
MAX_FILE_BYTES = 40 * 1024 * 1024
MAX_PEOPLE_PHOTOS = 5000         # cap for one folder
MAX_SESSIONS = 4                 # old cached folders are dropped
Image.MAX_IMAGE_PIXELS = None    # we do our own size check below


class Problem(Exception):
    """An error the user can understand (message is shown as is)."""


def prepare_image(data: bytes, label: str = "picture"):
    """bytes -> (BGR uint8 array no bigger than MAX_SIDE, original (w, h)).

    Raises Problem for non-images, empty files and gigantic pictures.
    """
    if not data:
        raise Problem(f"The file '{label}' is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise Problem(f"'{label}' is too big ({len(data) // 2**20} MB). "
                      f"The limit is {MAX_FILE_BYTES // 2**20} MB per picture.")
    try:
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        if w * h > MAX_PIXELS:
            raise Problem(f"'{label}' is huge ({w}x{h} pixels). Please use a smaller copy.")
        if img.format == "JPEG":                 # decode JPEGs at reduced size (fast, low memory)
            img.draft("RGB", (MAX_SIDE, MAX_SIDE))
        img = ImageOps.exif_transpose(img)       # phone photos: rotate upright
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    except Problem:
        raise
    except Exception:
        raise Problem(f"'{label}' is not a picture I can read (use JPG, PNG, BMP or WEBP).")
    arr = np.asarray(img)[:, :, ::-1].copy()     # RGB -> BGR
    return arr, (w, h)


def person_name(filename: str) -> str:
    """'folder/sub\\Priya Sharma.jpg' -> 'Priya Sharma'"""
    base = re.split(r"[\\/]", filename)[-1]
    return os.path.splitext(base)[0].strip()


def _area(face):
    return face[0][2] * face[0][3]


class Session:
    """The cached known people of one browser visit."""

    def __init__(self):
        self.names: list[str] = []          # one entry per reference photo
        self.embs: list[np.ndarray] = []
        self.lock = threading.Lock()

    @property
    def n_photos(self):
        return len(self.names)

    @property
    def n_people(self):
        return len(set(self.names))

    def add_reference(self, filename: str, data: bytes) -> dict:
        """Process one folder photo. Returns {file, status: ok|skipped, note}."""
        res = {"file": filename, "status": "skipped", "note": ""}
        name = person_name(filename)
        if not name:
            res["note"] = "Skipped: the file has no name."
            return res
        if self.n_photos >= MAX_PEOPLE_PHOTOS:
            res["note"] = f"Skipped: the folder has more than {MAX_PEOPLE_PHOTOS} photos."
            return res
        try:
            img, _ = prepare_image(data, filename)
            faces = backend.get_faces(img)
        except Problem as e:
            res["note"] = f"Skipped: {e}"
            return res
        except Exception:
            res["note"] = "Skipped: something went wrong while reading this photo."
            return res
        if not faces:
            res["note"] = "Skipped: no face found in this photo."
            return res
        notes = []
        if len(faces) > 1:
            notes.append(f"{len(faces)} faces found, used the largest")
        with self.lock:
            if name in self.names:
                notes.append("another photo with this name exists, both are used")
            self.names.append(name)
            self.embs.append(max(faces, key=_area)[1])
        res["status"] = "ok"
        res["note"] = ("Note: " + "; ".join(notes) + ".") if notes else ""
        return res

    def nearest(self, emb):
        """-> (name, distance) of the closest known photo."""
        with self.lock:
            names, embs = list(self.names), list(self.embs)
        dists = [backend.distance(emb, r) for r in embs]
        i = int(np.argmin(dists))
        return names[i], float(dists[i])

    def analyse_group(self, data: bytes, label: str = "group photo") -> dict:
        """Find faces in the group photo; return processed image + nearest person per face.

        The threshold is NOT applied here, so the page can change it instantly.
        """
        if self.n_photos == 0:
            raise Problem("No known people are loaded yet. Choose the folder first.")
        img, _ = prepare_image(data, label)
        h, w = img.shape[:2]
        faces = backend.get_faces(img)
        # reading order: rows top to bottom, then left to right
        if faces:
            row_h = max(1.0, float(np.median([f[0][3] for f in faces])))
            faces.sort(key=lambda f: (int((f[0][1] + f[0][3] / 2) // row_h), f[0][0]))
        out = []
        for i, ((x, y, bw, bh), emb) in enumerate(faces, start=1):
            name, d = self.nearest(emb)
            out.append({"id": i,
                        "box": {"x": x / w, "y": y / h, "w": bw / w, "h": bh / h},
                        "nearest": name, "distance": round(d, 4)})
        buf = io.BytesIO()
        Image.fromarray(img[:, :, ::-1]).save(buf, "JPEG", quality=90)
        return {"width": w, "height": h, "faces": out,
                "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}


_sessions: "OrderedDict[str, Session]" = OrderedDict()
_sessions_lock = threading.Lock()


def new_session() -> str:
    sid = uuid.uuid4().hex
    with _sessions_lock:
        _sessions[sid] = Session()
        while len(_sessions) > MAX_SESSIONS:
            _sessions.popitem(last=False)
    return sid


def get_session(sid: str) -> Session:
    with _sessions_lock:
        s = _sessions.get(sid)
        if s is not None:
            _sessions.move_to_end(sid)
    if s is None:
        raise Problem("Your session expired (the app was restarted). Please choose the folder again.")
    return s
