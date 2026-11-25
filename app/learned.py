"""Faces a person has named by hand ("This is..."), kept in one JSON file on this computer.

Only this is written for each face: id, name, embedding, recognition model, date added. No photos.
A file that is damaged or cannot be read is reported and never overwritten.
No web code and no face library here.
"""
import datetime
import json
import math
import os
import tempfile
import threading
import unicodedata
import uuid

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_lock = threading.Lock()        # every read and write of the file goes through this


class StoreError(Exception):
    """The saved-faces file cannot be used (message is shown to the user as is)."""


def path() -> str:
    return os.environ.get("FACE_LEARNED_FILE") or os.path.join(ROOT, "data", "learned_faces.json")


def name_key(name: str) -> str:
    """Names that differ only in upper / lower case are the same person."""
    return unicodedata.normalize("NFC", name).casefold()


def _check(entries):
    """Raise ValueError unless this is a list of well-formed entries."""
    if not isinstance(entries, list):
        raise ValueError("not a list")
    sizes = {}                                       # embeddings of one model must all have the same length
    for e in entries:
        if not isinstance(e, dict) or not all(isinstance(e.get(k), str) for k in ("id", "name", "model", "added")):
            raise ValueError("an entry is missing a field")
        emb = e.get("embedding")
        if not e["name"].strip() or not isinstance(emb, list) or not emb:
            raise ValueError("an entry has no name or no embedding")
        if not all(type(v) in (int, float) and math.isfinite(v) for v in emb) or not any(emb):
            raise ValueError("an embedding is not a list of usable numbers")
        if sizes.setdefault(e["model"], len(emb)) != len(emb):
            raise ValueError("embeddings have different lengths")


def _read() -> list:
    p = path()
    try:
        with open(p, "r", encoding="utf-8") as f:
            entries = json.load(f)
        _check(entries)
    except FileNotFoundError:
        return []                                    # nothing saved yet
    except Exception as e:
        raise StoreError(f"The saved faces file is damaged or cannot be read: {p}. It was left unchanged. "
                         "Repair it, or delete it to start again with no saved people.") from e
    return entries


def _write(entries: list):
    """Write a temporary file next to the real one, then swap it in, so a crash cannot leave half a file."""
    p = os.path.abspath(path())
    tmp = None
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix="learned_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except OSError as e:
        raise StoreError(f"The saved faces file could not be written: {p}. Nothing was changed.") from e
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def load(model: str) -> list:
    """[(name, embedding), ...] made with this recognition model. Other models' entries are not comparable."""
    with _lock:
        entries = _read()
    return [(e["name"], np.asarray(e["embedding"], dtype=np.float32)) for e in entries if e["model"] == model]


def save(name: str, embedding, model: str, replace_id: str = None, folder_names=()):
    """Add one face, or overwrite entry `replace_id`. -> (entry id, name as stored).

    If the name already exists (in the folder, or saved) ignoring case, that spelling is used.
    The entry being replaced does not count, so that a typo in it can be corrected.
    """
    with _lock:
        entries = _read()
        old = next((e for e in entries if e["id"] == replace_id), None)
        existing = list(folder_names) + [e["name"] for e in entries if e is not old]
        name = next((n for n in existing if name_key(n) == name_key(name)), name)
        new = {"id": old["id"] if old else uuid.uuid4().hex,
               "name": name,
               "embedding": [float(v) for v in embedding],
               "model": model,
               "added": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        if old:
            entries[entries.index(old)] = new
        else:
            entries.append(new)
        _write(entries)
    return new["id"], name


def people(model: str) -> list:
    """[{"name", "samples"}], one row per person, sorted by name."""
    with _lock:
        entries = _read()
    rows = {}
    for e in entries:
        if e["model"] == model:
            row = rows.setdefault(name_key(e["name"]), {"name": e["name"], "samples": 0})
            row["samples"] += 1
    return [rows[k] for k in sorted(rows)]


def delete(name: str) -> int:
    """Remove every saved sample of this person. -> how many were removed."""
    with _lock:
        entries = _read()
        keep = [e for e in entries if name_key(e["name"]) != name_key(name)]
        if len(keep) != len(entries):
            _write(keep)
    return len(entries) - len(keep)
