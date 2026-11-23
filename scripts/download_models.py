"""Download the UniFace model files into ./models (needs internet, run once).

Usage (from the project folder, venv active):
    python scripts/download_models.py            (saves into ./models)
    python scripts/download_models.py <folder>   (optional: another folder)

After this the app runs fully offline. Files are checked with SHA-256 by UniFace.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "models")
os.makedirs(MODELS, exist_ok=True)
os.environ["UNIFACE_CACHE_DIR"] = MODELS      # tell UniFace to use ./models

from uniface.constants import ArcFaceWeights, SCRFDWeights
from uniface.model_store import verify_model_weights

for weights in (SCRFDWeights.SCRFD_10G_KPS, ArcFaceWeights.RESNET):
    try:
        path = verify_model_weights(weights, root=MODELS)
    except Exception as e:   # no internet, blocked host, ...
        sys.exit(f"\nCould not get {weights.value}: {e}\n"
                 "Check your internet connection and run this script again.")
    print(f"OK  {os.path.basename(path)}  ({os.path.getsize(path) / 1e6:.0f} MB)")
print("\nAll models are in", MODELS, "- the app can now run without internet.")
