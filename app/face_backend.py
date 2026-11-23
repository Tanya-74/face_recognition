"""Face backend = UniFace, same interface as experiments/wrap_*.py:

    get_faces(image_bgr) -> [((x, y, w, h), embedding), ...]
    distance(a, b)       -> float, lower = more similar (cosine distance)

Detector SCRFD-10G + ArcFace ResNet, CPU only. Model files are read from the
project's models/ folder (never from ~/.uniface, never from the internet).
To swap the library later, write another module with these two functions and
change the import in app/engine.py.
"""
import os
import threading

import numpy as np

NAME = "uniface"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.environ.get("FACE_MODELS_DIR", os.path.join(ROOT, "models"))
REQUIRED = ["scrfd_10g.onnx", "arcface_resnet.onnx"]

_det = _rec = None
_lock = threading.Lock()


class ModelsMissing(RuntimeError):
    pass


def check_models():
    """Raise a plain-English error if the model files are not in models/."""
    missing = [f for f in REQUIRED if not os.path.isfile(os.path.join(MODELS_DIR, f))]
    if missing:
        raise ModelsMissing(
            f"Model files missing in '{MODELS_DIR}': {', '.join(missing)}. "
            "Run  python scripts/download_models.py  once (needs internet).")


def load():
    """Load both models (once). Safe to call many times."""
    global _det, _rec
    with _lock:
        if _det is not None:
            return
        check_models()
        os.environ["UNIFACE_CACHE_DIR"] = MODELS_DIR     # look here only
        from uniface import SCRFD, ArcFace
        from uniface.constants import ArcFaceWeights, SCRFDWeights
        cpu = ["CPUExecutionProvider"]
        _det = SCRFD(model_name=SCRFDWeights.SCRFD_10G_KPS, providers=cpu)
        _rec = ArcFace(model_name=ArcFaceWeights.RESNET, providers=cpu)


def get_faces(image):
    """image: BGR numpy array."""
    load()
    with _lock:                      # one image at a time (simple and safe)
        out = []
        for f in _det.detect(image):
            emb = _rec.get_normalized_embedding(image, f.landmarks)
            x, y, w, h = f.bbox_xywh
            out.append(((int(x), int(y), int(w), int(h)),
                        np.asarray(emb, dtype=np.float32).ravel()))
    return out


def distance(a, b):
    return float(1.0 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
