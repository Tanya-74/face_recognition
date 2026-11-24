# Face Recognition (offline)

A small web app that runs **only on your computer**. You give it a folder of known people
(one photo each, the file name is the person's name) and one group photo. It draws a box and
a name on every face and lists the results. After the one-time setup it needs **no internet**.

Face library: [UniFace](https://github.com/yakhyo/uniface) (SCRFD detector + ArcFace).
Why this one: [RESEARCH.md](RESEARCH.md). How the app is built: [ARCHITECTURE.md](ARCHITECTURE.md).

## Install (fresh Windows laptop, once)

You need internet for this part only.

### 1. Python 3.11
Download it from <https://www.python.org/downloads/release/python-3119/> and tick
**"Add python.exe to PATH"** in the installer, or run `winget install Python.Python.3.11`.
Check it: open PowerShell and run `py -3.11 --version`.

### 2. Get the project
```powershell
git clone https://github.com/Tanya-74/face_recognition.git
cd face_recognition
```
(or download the ZIP from GitHub, unpack it, and open PowerShell in that folder).

### 3. Create the virtual environment and install the packages
About 500 MB, a few minutes.
```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```
If PowerShell says scripts are disabled, skip the `activate` line and write
`.venv\Scripts\python.exe` instead of `python` in the commands below.

### 4. Get the two model files (about 190 MB)
The models are not stored in git: `arcface_resnet.onnx` is 174 MB, and GitHub rejects single files over 100 MB.
Use **one** of these two ways. Both end with the two files inside the `models\` folder.

**Way A: download script** (easiest)
```powershell
python scripts\download_models.py
```
You should see two lines starting with `OK`. The script checks each file with a SHA-256 hash.

**Way B: from the GitHub Release** (no script, e.g. if the script is blocked)
1. Open the project's **Releases** page: <https://github.com/Tanya-74/face_recognition/releases>
2. Download the two files `scrfd_10g.onnx` (17 MB) and `arcface_resnet.onnx` (174 MB) from the newest release.
3. Put both in the `models\` folder of the project (next to `.gitkeep`).
4. Optional check in PowerShell: `Get-FileHash models\*.onnx -Algorithm SHA256`. The hashes must be:

   | File | SHA-256 |
   |---|---|
   | `scrfd_10g.onnx` | `5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91` |
   | `arcface_resnet.onnx` | `4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43` |

> For the repository owner: a Release has to be created once by hand (GitHub, Releases, Draft a new release,
> attach the two files from your `models\` folder). It is not created automatically.
> To set up a computer that has no internet at all, copy the two `.onnx` files over by USB stick into `models\`.
> (The Python packages in step 3 still need internet once.)

## Run

**Easy way:** double-click **`run_app.bat`**. It activates the environment, starts the server and opens your
browser at <http://127.0.0.1:8000>. Keep the black window open while you use the app; close it to stop the app.

**By hand** (in PowerShell, in the project folder):
```powershell
.venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Then open <http://127.0.0.1:8000>. Stop with Ctrl+C.

While the top of the page shows **"Starting up..."**, the face models are loading: wait until that note disappears.
When there is no note at all, everything is ready. A **red** note means a problem (see Troubleshooting).
The Run button stays grey until the models are ready and you have chosen a folder and a photo.

## Use the page (3 steps)

The page uses a dark theme (the only look) and everything fits on one screen: Run at the top, the photo on the left, the list of faces on the right,
and the strictness slider at the bottom. The download buttons sit at the top, on the right.

1. **Choose the folder of known people**: click the big box **1** (or drag the folder onto it).
   One photo per person, named after them, for example `Priya Sharma.jpg`, `Tom Lee.png`.
   The button **Known people** then shows small pictures of everyone, so you can check you picked the right folder.
2. **Choose one group photo** (JPG, PNG, BMP or WEBP): click the big box **2** or drag the photo onto it.
   The file names then appear at the top with small **Change folder** / **Change photo** links, so you can pick again
   at any time. You can also drop a new photo (or folder) straight onto the picture.
3. **Press Run.** A progress bar with a percentage shows while the folder is read (about 0.5 to 2 seconds per photo
   on a normal CPU). The photo then appears with a box and a name on every face. On the right you see how many
   faces were found, how many are known and unknown, and one card per face. Point at a face (or a card) to
   highlight the other one, click to select, and use **All / Known / Unknown** to filter.
   **Download PNG** (the photo with boxes and names) and **Download CSV** (the list, opens in Excel) are at the top right.

**Strictness slider** (bottom left, default 0.62): lower = stricter (more "Unknown", fewer wrong names); higher = more forgiving.
It changes the labels at once without reading any photo again. Pressing Run again with the same folder skips the
folder step (results are cached until the app is restarted). To try another group photo, drop it on the photo
and press Run.

The distance is a cosine distance: 0 = identical, bigger = more different. In our test
(see [RESEARCH.md](RESEARCH.md)) the range 0.55 to 0.80 gave no mistakes, but real photos are harder,
so check the slider on your own photos.

### What happens with odd input

| Situation | What the app does |
|---|---|
| Folder photo with no face | Skipped, listed under **Folder notes** (button at the top) |
| Folder photo with several faces | Uses the largest face, and says so in the notes |
| File that is not a picture (`.txt`, broken `.jpg`, empty file) | Ignored or skipped with a note, no crash |
| Two photos with the same name (`Bono.jpg`, `Bono.png`) | Both are used for that person, and a note says so |
| Very large pictures | Shrunk to 1600 px on the long side before processing. Pictures over 120 megapixels or 40 MB are refused with a message |
| Phone photos (rotated by EXIF) | Turned upright automatically |
| Group photo with no faces | Message "No faces were found..." |
| Very large folder | Sent in small batches with a progress bar and a **Cancel** button. Limit: 5000 photos. The **Known people** drawer shows the first 48, then "Show all" |
| Models missing | The page shows "Face models not found" and tells you to repeat step 4 |

## Test it with the WiFi turned off

1. Finish the install above and run the app once while online. This also proves the models are in `models\`.
2. Close the app. **Turn WiFi off** (and unplug any network cable). Airplane mode is the easiest:
   Windows key, then Airplane mode. Open any website in a browser tab to check that there really is no internet.
3. Double-click `run_app.bat` again. The page opens at `http://127.0.0.1:8000` (that address is your own
   computer, so it works without internet). After a few seconds the "Starting up..." note disappears: the models were
   loaded from the `models\` folder.
4. Choose a folder and a group photo, press Run. It should work exactly as before.
5. Optional proof: an automatic test starts the server with all network access blocked and checks 22 things:
   `python tests\test_app.py` (2 to 4 minutes, prints PASS or FAIL for each).

If something needed the internet, a red note would appear at the top instead. The page loads no fonts,
scripts or images from the web (everything is in `app\static\`), and the server listens on 127.0.0.1 only, so
other computers on your network cannot reach it.

## Troubleshooting

| Problem | What to do |
|---|---|
| `py` is not recognised | Python 3.11 is missing or not on PATH. Repeat step 1 and reopen PowerShell. |
| PowerShell: "running scripts is disabled" | Do not use `activate`. Write `.venv\Scripts\python.exe` instead of `python`. (`run_app.bat` is not affected.) |
| Red note "Face models not found" at the top, or the page says "Model files missing" | The `.onnx` files are not in `models\`. Repeat step 4 (way A or B). Both files must be there. |
| `download_models.py` says "Could not get ..." | No internet or a blocked connection. Fix the connection, or use way B. |
| `pip install` fails | Check that `py -3.11 --version` works and you are online. Run the command again. |
| The page does not open / "Cannot reach the app" | The black window must stay open. If it shows an error, read it. Port 8000 may be taken: start by hand with `--port 8001` and open <http://127.0.0.1:8001>. |
| "Your session expired" | The app was restarted. Choose the folder again and press Run. |
| First Run is very slow | Normal for a big folder (every photo is read once). The first start can also be slow while Windows scans the new files. |
| Someone who should be known shows as Unknown | Raise the slider a little, and check that their folder photo shows the face clearly, looking at the camera. |
| A stranger gets a name | Lower the slider. |

## Project layout

```
app/main.py            web server (FastAPI) and the JSON API
app/engine.py          image preparation, cached embeddings, matching
app/face_backend.py    the face library behind two functions: get_faces(image), distance(a, b)
app/static/            the page (index.html, style.css, app.js, favicon.svg), all local
models/                the two .onnx model files (not in git)
scripts/download_models.py   one-time model download
tests/test_app.py      end-to-end test with edge cases
run_app.bat            start script
docs/                  architecture diagram (SVG, PNG, interactive HTML) and its source
experiments/           the library comparison (smoke tests, full evaluation, charts)
RESEARCH.md            results of the comparison
ARCHITECTURE.md        how the app is built, and the trade-offs
```
