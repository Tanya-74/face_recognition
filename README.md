# Who is in the photo? (offline face recognition)

A small web app that runs **only on your computer**. You give it a folder of known people
(one photo each, the file name is the person's name) and one group photo. It draws a box and
a name on every face and lists the results. After the one-time setup it needs **no internet**.

Face library: [UniFace](https://github.com/yakhyo/uniface) (SCRFD detector + ArcFace). Why this one:
see [RESEARCH.md](RESEARCH.md).

## Install (fresh Windows laptop, once)

You need internet for this part only.

1. **Install Python 3.11.** Download it from <https://www.python.org/downloads/release/python-3119/>
   (tick **"Add python.exe to PATH"**) or run `winget install Python.Python.3.11`.
2. **Get the project.** `git clone https://github.com/Tanya-74/face_recognition.git`
   (or download the ZIP from GitHub and unpack it), then open **PowerShell** in the project folder.
3. **Create the environment and install the packages** (about 500 MB, a few minutes):
   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
4. **Download the face models once** (about 190 MB, saved in the `models\` folder):
   ```powershell
   .venv\Scripts\python.exe scripts\download_models.py
   ```
   You should see two lines starting with `OK`. The model files are not stored in git because they are
   too big (`arcface_resnet.onnx` is 174 MB, `scrfd_10g.onnx` is 17 MB; GitHub refuses single files over 100 MB).
   To set up a second computer that has no internet for step 4: copy the two `.onnx` files from this computer into
   its `models\` folder instead. (Do not copy `.venv\`; a virtual environment only works on the computer that made it.)

## Run

Double-click **`run_app.bat`**. A black window opens (keep it open) and your browser opens
<http://127.0.0.1:8000>. When the grey badge at the top turns green and says **"Ready - works offline"**, go on.

Or by hand: `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

To stop: close the black window (or press Ctrl+C in it).

## How to use it

1. **Choose folder**: pick the folder with the known people, for example `Priya Sharma.jpg`, `Tom Lee.png`.
2. **Choose group photo**: one picture with several people.
3. **Run**. A progress bar shows while the folder is read (about 0.5 to 2 seconds per photo on a normal CPU).
   The result shows the photo with a box and a name on each face, and a list below with name, distance and
   Known / Unknown.
4. **Strictness slider** (default 0.62): lower = stricter (more "Unknown", fewer wrong names),
   higher = more forgiving. It changes the labels at once without reading the photos again.
   Press Run again with the same folder and it skips the folder step, because the results are cached
   (until the app is restarted).

The distance is a cosine distance: 0 = identical, bigger = more different. In our test
(see [RESEARCH.md](RESEARCH.md)) the range 0.55 to 0.80 gave no mistakes, but real photos are harder, so check
the slider on your own photos.

### What happens with odd input

| Situation | What the app does |
|---|---|
| Folder photo with no face | Skipped, listed under "Notes about the folder" |
| Folder photo with several faces | Uses the largest face, and says so in the notes |
| File that is not a picture (`.txt`, broken `.jpg`, empty file) | Ignored or skipped with a note, no crash |
| Two photos with the same name (`Bono.jpg`, `Bono.png`) | Both are used for that person, and a note says so |
| Very large pictures | Shrunk to 1600 px on the long side before processing. Pictures over 120 megapixels or 40 MB are refused with a message |
| Phone photos (rotated by EXIF) | Turned upright automatically |
| Group photo with no faces | Message "No faces were found..." |
| Very large folder | Sent in small batches with a progress bar and a **Cancel** button. Limit: 5000 photos |
| Models missing | The page shows "Face models not found" and tells you to run the download script |

## Test it with the WiFi turned off

1. Finish the install above and run the app once while online (this also proves the models are in `models\`).
2. Close the app. **Turn WiFi off** (and unplug any network cable). Airplane mode is the easiest:
   Windows key, then Airplane mode. Open a browser tab on any website to check that there is really no internet.
3. Double-click `run_app.bat` again. The page opens at `http://127.0.0.1:8000` (that address is your own computer,
   so it works without internet) and the badge turns green: **"Ready - works offline"**.
4. Choose a folder and a group photo, press Run. It should work exactly as before.
5. Optional proof: the app also has an automatic test that blocks all network access for the server:
   `.venv\Scripts\python.exe tests\test_app.py` (takes 2 to 4 minutes, prints PASS / FAIL for 23 checks).

If something needs the internet, the badge shows an error instead of green. The page itself loads no
fonts, scripts or images from the web (everything is in `app\static\`), and the server listens on
127.0.0.1 only, so other computers on your network cannot reach it.

## Project layout

```
app/main.py            web server (FastAPI) and the JSON API
app/engine.py          image preparation, cached embeddings, matching
app/face_backend.py    the face library behind two functions: get_faces(image), distance(a, b)
app/static/            the page (index.html, style.css, app.js, favicon.svg) - all local
models/                the two .onnx model files (downloaded once, not in git)
scripts/download_models.py   one-time model download
tests/test_app.py      end-to-end test with edge cases
run_app.bat            start script
experiments/           the library comparison (smoke tests, full evaluation, charts)
RESEARCH.md            results of the comparison
```

To swap the face library later, write a module with the same two functions as `app/face_backend.py`
(`get_faces` returns `[((x, y, w, h), embedding), ...]`, `distance` returns a number, lower = more similar)
and change the `import face_backend` line in `app/engine.py` and `app/main.py`.

## Troubleshooting

- **"Model files missing ..."**: run step 4 of the install again.
- **`py` is not recognised**: Python 3.11 is not installed or not on PATH; repeat step 1.
- **The page does not open**: look at the black window for an error. Port 8000 may be used by another program;
  start by hand with `--port 8001` and open <http://127.0.0.1:8001>.
- **Very slow first Run**: the first photos can take longer while Windows scans the new files.
  Later runs are faster.
- **A name is wrong or Unknown for someone who should be known**: move the slider, and make sure the folder photo
  shows that person clearly, looking at the camera.
