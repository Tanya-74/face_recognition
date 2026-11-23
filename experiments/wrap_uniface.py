"""UniFace wrapper.

Detector : SCRFD-10G with 5 landmarks (largest/most accurate detector UniFace
           ships; UniFace's own default is the lighter RetinaFace-MobileNetV2).
Embedding: ArcFace ResNet (512-d; UniFace's default ArcFace is the small MNET,
           we take the stronger RESNET weights). Distance: cosine.
Runs on CPU through onnxruntime.
NOTE: these weights are the same family as InsightFace's buffalo_l, so the two
      libraries may behave very similarly - the difference is the library
      (API, install, speed), not a different model.
Interface shared by all wrappers:
    get_faces(image_bgr) -> [((x, y, w, h), embedding), ...]
    distance(a, b)       -> float, lower = more similar
"""
import numpy as np

NAME = "uniface"
DETECTOR = "SCRFD-10G-KPS"
MODEL = "ArcFace ResNet"
METRIC = "cosine"
THRESHOLDS = [round(float(t), 2) for t in np.arange(0.20, 0.901, 0.05)]

_det = _rec = None


def _load():
    global _det, _rec
    if _det is None:
        from uniface import SCRFD, ArcFace
        from uniface.constants import ArcFaceWeights, SCRFDWeights
        cpu = ["CPUExecutionProvider"]
        _det = SCRFD(model_name=SCRFDWeights.SCRFD_10G_KPS, providers=cpu)
        _rec = ArcFace(model_name=ArcFaceWeights.RESNET, providers=cpu)


def get_faces(image):
    """image: BGR numpy array (as from cv2.imread)."""
    _load()
    out = []
    for f in _det.detect(image):
        emb = _rec.get_normalized_embedding(image, f.landmarks)
        x, y, w, h = f.bbox_xywh
        out.append(((int(x), int(y), int(w), int(h)), np.asarray(emb, dtype=np.float32).ravel()))
    return out


def distance(a, b):
    return float(1.0 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
