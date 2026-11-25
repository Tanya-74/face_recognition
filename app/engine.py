"""Core logic: prepare images, keep the known-people embeddings, match faces.

No web code here. The face library is used only through two functions
(get_faces, distance) from face_backend, so it can be swapped.
"""
import base64
import io
import os
import re
import threading
import unicodedata
import uuid
from collections import OrderedDict

import numpy as np
from PIL import Image, ImageOps

import face_backend as backend
import learned

MAX_SIDE = 1600                  # bigger pictures are shrunk to this before processing
MAX_PIXELS = 120_000_000         # refuse absurd pictures (would eat all memory)
MAX_FILE_BYTES = 40 * 1024 * 1024
MAX_PEOPLE_PHOTOS = 5000         # cap for one folder
MAX_SESSIONS = 4                 # old cached folders are dropped
MAX_NAME = 80                    # longest name a person can type for a face
# saved embeddings are only comparable if the same recognition model made them
MODEL = f"{backend.NAME}:{os.path.splitext(backend.REQUIRED[-1])[0]}"
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


def clean_name(raw) -> str:
    """A name typed by the user, trimmed. Raises Problem if it cannot be used."""
    if not isinstance(raw, str):
        raise Problem("Please type a name.")
    name = raw.strip()
    if not name:
        raise Problem("Please type a name.")
    if len(name) > MAX_NAME:
        raise Problem(f"That name is too long. Use {MAX_NAME} characters or fewer.")
    # Cc = control characters, Cs = broken half characters, Zl / Zp = line breaks
    if any(unicodedata.category(c) in ("Cc", "Cs", "Zl", "Zp") for c in name):
        raise Problem("That name contains characters that cannot be used (such as a line break or a tab).")
    if all(unicodedata.category(c) == "Cf" for c in name):          # only invisible characters
        raise Problem("Please type a name.")
    if learned.name_key(name) == "unknown":
        raise Problem('"Unknown" cannot be used as a name. Type the person\'s name.')
    return name


def _area(face):
    return face[0][2] * face[0][3]


class Session:
    """The cached known people of one browser visit, and the faces of its latest group scan."""

    def __init__(self):
        self.names: list[str] = []          # one entry per reference photo
        self.embs: list[np.ndarray] = []
        self.lock = threading.Lock()
        self.analysis_id = None             # identifies the latest group scan
        self.scan_embs: dict = {}           # face id -> embedding, latest scan only; never sent to the browser
        self.scan_saved: dict = {}          # face id -> saved entry id, for faces of that scan that were named

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

    def nearest(self, emb, saved=()):
        """-> (name, distance) of the closest folder photo or saved face. Every sample counts on its own."""
        with self.lock:
            names, embs = list(self.names), list(self.embs)
        for name, other in saved:
            if other.shape == emb.shape:
                names.append(name)
                embs.append(other)
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
        warning = ""
        try:
            saved = learned.load(MODEL)
        except learned.StoreError as e:          # still answer from the folder, and say what is wrong
            saved, warning = [], f"{e} Saved people are not being used."
        out = []
        for i, ((x, y, bw, bh), emb) in enumerate(faces, start=1):
            name, d = self.nearest(emb, saved)
            out.append({"id": i,
                        "box": {"x": x / w, "y": y / h, "w": bw / w, "h": bh / h},
                        "nearest": name, "distance": round(d, 4)})
        buf = io.BytesIO()
        Image.fromarray(img[:, :, ::-1]).save(buf, "JPEG", quality=90)
        analysis_id = uuid.uuid4().hex
        with self.lock:
            self.analysis_id = analysis_id
            self.scan_embs = {i: emb for i, (_, emb) in enumerate(faces, start=1)}
            self.scan_saved = {}
        return {"width": w, "height": h, "faces": out, "analysis_id": analysis_id, "warning": warning,
                "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}

    def label(self, analysis_id, face_id, name) -> dict:
        """Remember one face of the latest scan under a name. Only ever called because the user asked."""
        with self.lock:
            if not self.analysis_id or analysis_id != self.analysis_id:
                raise Problem("This result is out of date, so the name was not saved. "
                              "Press Run, then name the face again.")
            if type(face_id) is not int or face_id not in self.scan_embs:
                raise Problem("That face is not in the latest result. Press Run and try again.")
            name = clean_name(name)
            entry_id, stored = learned.save(name, self.scan_embs[face_id], MODEL,
                                            replace_id=self.scan_saved.get(face_id), folder_names=list(self.names))
            self.scan_saved[face_id] = entry_id      # naming this face again replaces the entry (typo fix)
        return {"face_id": face_id, "name": stored}


def saved_people() -> list:
    return learned.people(MODEL)


def forget_person(name) -> int:
    removed = learned.delete(name) if name else 0
    if not removed:
        raise Problem("There is no saved person with that name.")
    return removed


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
