"""DeepFace wrapper.

Detector : retinaface  (accurate on small / non-frontal faces; plain "opencv"
           Haar cascade is explicitly NOT used, as requested).
Embedding: Facenet512 (512-d). Distance: cosine (DeepFace's own recommended
           metric for this model).
Interface shared by all wrappers:
    get_faces(image_bgr) -> [((x, y, w, h), embedding), ...]
    distance(a, b)       -> float, lower = more similar
"""
import numpy as np

NAME = "deepface"
DETECTOR = "retinaface"
MODEL = "Facenet512"
METRIC = "cosine"
# thresholds swept by the evaluation script (distance <= t  => same person)
THRESHOLDS = [round(float(t), 2) for t in np.arange(0.10, 0.801, 0.05)]

_loaded = False


def _lazy():
    global _loaded
    if not _loaded:
        from deepface import DeepFace  # noqa: F401 (import is slow, do it once)
        _loaded = True


def get_faces(image):
    """image: BGR numpy array (as from cv2.imread)."""
    _lazy()
    from deepface import DeepFace
    res = DeepFace.represent(
        img_path=image, model_name=MODEL, detector_backend=DETECTOR,
        enforce_detection=False, align=True,
    )
    faces = []
    for r in res:
        # with enforce_detection=False DeepFace returns the whole image
        # (confidence 0) when nothing is found -> not a real detection.
        if r.get("face_confidence", 1) <= 0:
            continue
        a = r["facial_area"]
        faces.append(((int(a["x"]), int(a["y"]), int(a["w"]), int(a["h"])),
                      np.asarray(r["embedding"], dtype=np.float32)))
    return faces


def distance(a, b):
    return float(1.0 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
