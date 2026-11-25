"""Set the app up if needed, then start it and run the demo in the browser. Used by demo.bat.

By hand, from the project folder:  py -3.11 scripts/demo.py
Only the standard library is used here, because the packages may not be installed yet.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(ROOT, ".venv")
PYTHON = os.path.join(VENV, "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")
MODELS = [os.path.join(ROOT, "models", n) for n in ("scrfd_10g.onnx", "arcface_resnet.onnx")]
DEMO_FACES = os.path.join(ROOT, "data", "demo_faces.json")      # names saved during a demo go here

RIGHT_PYTHON = "import sys; sys.exit(sys.version_info[:2] != (3, 11))"
PACKAGES_OK = ("from importlib.metadata import version; import fastapi, uvicorn, PIL, numpy, onnxruntime, uniface; "
               "version('python-multipart'); assert version('uniface') == '4.3.0'")


def say(text):
    print(f"\n== {text}", flush=True)


def works(code):
    """Does this line of Python run inside the virtual environment?"""
    return os.path.isfile(PYTHON) and subprocess.run([PYTHON, "-c", code], capture_output=True).returncode == 0


def run(command, if_it_fails):
    if subprocess.run(command, cwd=ROOT).returncode != 0:
        sys.exit(f"\n{if_it_fails}")


def main():
    if not works(RIGHT_PYTHON):
        if os.path.exists(VENV):
            sys.exit("\nThe .venv folder is broken or was made with another Python. "
                     "Delete the .venv folder and double-click demo.bat again.")
        say("1 of 4: creating the virtual environment (.venv)")
        run([sys.executable, "-m", "venv", VENV], "The virtual environment could not be created.")
    else:
        say("1 of 4: virtual environment found")

    if not works(PACKAGES_OK):
        say("2 of 4: installing the packages, about 500 MB. This needs internet and takes a few minutes.")
        run([PYTHON, "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"],
            "The packages could not be installed. Check the internet connection and try again.")
        if not works(PACKAGES_OK):
            sys.exit("\nThe packages are installed but cannot be loaded. On a new Windows computer, install the "
                     "Microsoft Visual C++ Redistributable (x64) and try again.")
    else:
        say("2 of 4: packages already installed")

    if not all(os.path.isfile(m) for m in MODELS):
        say("3 of 4: downloading the two face models, about 190 MB. This needs internet once.")
        run([PYTHON, os.path.join("scripts", "download_models.py")],
            "The models could not be downloaded. Check the internet connection and try again.")
    else:
        say("3 of 4: face models found")

    say("4 of 4: starting the demo. Your browser opens and runs the app on the sample photos.")
    if os.path.isfile(DEMO_FACES):
        os.remove(DEMO_FACES)                   # every demo starts with nobody saved
    env = dict(os.environ, FACE_DEMO="1", FACE_LEARNED_FILE=DEMO_FACES, PYTHONUTF8="1")
    return subprocess.run([PYTHON, os.path.join("scripts", "launch.py")], cwd=ROOT, env=env).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
