"""InsightFace wrapper.

Model pack: buffalo_l (the library's default, best-accuracy pack).
Detector  : SCRFD-10G (part of buffalo_l; state of the art, robust to scale).
Embedding : ArcFace ResNet50 (512-d, w600k_r50). Distance: cosine.
Runs on CPU through onnxruntime (CPUExecutionProvider).
Interface shared by all wrappers:
    get_faces(image_bgr) -> [((x, y, w, h), embedding), ...]
    distance(a, b)       -> float, lower = more similar
"""
import numpy as np

NAME = "insightface"
DETECTOR = "SCRFD-10G (buffalo_l)"
MODEL = "ArcFace w600k_r50 (buffalo_l)"
METRIC = "cosine"
THRESHOLDS = [round(float(t), 2) for t in np.arange(0.20, 0.901, 0.05)]

_app = None


def _get_app():
    global _app
    if _app is None:
        from insightface.app import FaceAnalysis
        # only detection + recognition: skips landmark/gender-age models (faster)
        _app = FaceAnalysis(name="buffalo_l",
                            allowed_modules=["detection", "recognition"],
                            providers=["CPUExecutionProvider"])
        _app.prepare(ctx_id=-1, det_size=(640, 640))
    return _app


def get_faces(image):
    """image: BGR numpy array (as from cv2.imread)."""
    out = []
    for f in _get_app().get(image):
        x1, y1, x2, y2 = f.bbox
        emb = np.asarray(f.embedding, dtype=np.float32)
        out.append(((int(x1), int(y1), int(x2 - x1), int(y2 - y1)), emb))
    return out


def distance(a, b):
    return float(1.0 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
