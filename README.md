# Face Recognition (offline)

A small web app that runs **only on your computer**. You give it a folder of known people
(one photo each, the file name is the person's name) and one group photo. It draws a box and
a name on every face and lists the results. After the one-time setup it needs **no internet**.
If a face shows as "Unknown", you can type the person's name and the app
[remembers it](#name-an-unknown-face) for later scans.

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
They go into the `models\` folder. You do not have to do anything extra:
**`run_app.bat` downloads them automatically the first time** if they are missing (internet needed this one time).

To get them before the first start, or if you start the app by hand, run:
```powershell
python scripts\download_models.py
```
You should see two lines starting with `OK`. The script checks each file with a SHA-256 hash.

**A computer with no internet at all:** copy the two files `scrfd_10g.onnx` and `arcface_resnet.onnx` from another
computer (where the step above worked) into the `models\` folder, for example with a USB stick. Optional check in
PowerShell: `Get-FileHash models\*.onnx -Algorithm SHA256`. The hashes must be:

| File | SHA-256 |
|---|---|
| `scrfd_10g.onnx` | `5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91` |
| `arcface_resnet.onnx` | `4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43` |

(The Python packages in step 3 also need internet once.)

## Run

**Easy way:** double-click **`run_app.bat`**. It activates the environment, gets the models if they are missing,
starts the server and opens your browser at <http://127.0.0.1:8000> as soon as the server answers. If another program is
already using port 8000, it takes the next free port (8001, 8002, ...) and prints the address in the window.
Keep the black window open while you use the app; close it to stop the app.

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

### Name an unknown face

1. On the card of an **Unknown** face press **This is...**, type the name and press **Save** (or Enter).
   Before you save, the card says: "This face will be remembered on this computer as *the name you typed*."
2. The app checks the same group photo again, so boxes, cards, counts and downloads are up to date.
   The folder is not read again and the slider stays where it is.
3. From now on, every scan compares faces with the folder photos **and** the saved faces, also after a restart.
   A saved person does not need a photo in the folder. (You still choose a folder before you press Run.)

**Wrong name or typo?** Open **Saved people** (top bar), press **Delete** next to the name, confirm, and name the
face again. Delete removes all saved faces of that name. A face that already shows as Known cannot be renamed on its card.

The name must be 1 to 80 characters and cannot be "Unknown". If the name already exists (in the folder or saved),
the existing spelling is used. Nothing is learned automatically: a face is saved only when you press Save.
The face models are not retrained.

### Saved faces: where they are, and how to delete them

Saved faces are kept in **`data\learned_faces.json`** inside the project folder. The file appears the first time you
save a name. For each saved face it holds an id, the name, the embedding (512 numbers that describe the face), the
recognition model's name and the date. **No photos or face pictures are saved.** The file is not in git.

This is personal (biometric) data and it is **not encrypted**: anyone who can read your files can read it.

- Delete one person: **Saved people**, then **Delete**.
- Delete everyone: close the app and delete the file (or the whole `data` folder). Do this before a demonstration
  if you do not want earlier names to show up.
- To keep the file somewhere else, set the environment variable `FACE_LEARNED_FILE` to its full path before starting.
- If the file is damaged or cannot be read, the app says so, goes on with the folder photos only, and does **not**
  overwrite the file. Repair it or delete it.

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
| Saved-faces file damaged | A warning names the file. Scans use the folder only, saving and deleting are refused, the file is left unchanged |
| Naming a face from an out-of-date result | Refused with "Press Run, then name the face again", so a name cannot land on the wrong face |

## Test it with the WiFi turned off

1. Finish the install above and run the app once while online. This also proves the models are in `models\`.
2. Close the app. **Turn WiFi off** (and unplug any network cable). Airplane mode is the easiest:
   Windows key, then Airplane mode. Open any website in a browser tab to check that there really is no internet.
3. Double-click `run_app.bat` again. The page opens at `http://127.0.0.1:8000`, or the next free port (that address
   is your own computer, so it works without internet). After a few seconds the "Starting up..." note disappears: the models were
   loaded from the `models\` folder.
4. Choose a folder and a group photo, press Run. It should work exactly as before.
5. Optional proof: an automatic test starts the server with all network access blocked and checks 65 things:
   `python tests\test_app.py` (1 to 6 minutes depending on the machine, prints PASS or FAIL for each). It saves test names to a
   temporary file, never to your `data` folder.

If something needed the internet, a red note would appear at the top instead. The page loads no fonts,
scripts or images from the web (everything is in `app\static\`), and the server listens on 127.0.0.1 only, so
other computers on your network cannot reach it.

## Troubleshooting

| Problem | What to do |
|---|---|
| `py` is not recognised | Python 3.11 is missing or not on PATH. Repeat step 1 and reopen PowerShell. |
| PowerShell: "running scripts is disabled" | Do not use `activate`. Write `.venv\Scripts\python.exe` instead of `python`. (`run_app.bat` is not affected.) |
| Red note "Face models not found" at the top, or the page says "Model files missing" | The `.onnx` files are not in `models\`. Double-click `run_app.bat` (it downloads them) or repeat step 4. Both files must be there. |
| `download_models.py` says "Could not get ..." | No internet or a blocked connection. Fix the connection and run it again, or copy the two files by hand (see step 4). |
| `pip install` fails | Check that `py -3.11 --version` works and you are online. Run the command again. |
| The page does not open / "Cannot reach the app" | The black window must stay open. If it shows an error, read it. Use the address printed in that window: it is not 8000 when another program holds that port. (Starting by hand: add `--port 8001` instead.) |
| "Your session expired" | The app was restarted. Choose the folder again and press Run. |
| First Run is very slow | Normal for a big folder (every photo is read once). The first start can also be slow while Windows scans the new files. |
| Someone who should be known shows as Unknown | Raise the slider a little, and check that their folder photo shows the face clearly, looking at the camera. |
| A stranger gets a name | Lower the slider. If the name came from **This is...**, delete it under **Saved people**. |
| "The saved faces file is damaged or cannot be read" | See "Saved faces" above: repair or delete the file named in the message. |

## Project layout

```
app/main.py            web server (FastAPI) and the JSON API
app/engine.py          image preparation, cached embeddings, matching
app/face_backend.py    the face library behind two functions: get_faces(image), distance(a, b)
app/learned.py         reads and writes the faces you named
data/                  your saved faces (created when you name one; not in git)
app/static/            the page (index.html, style.css, app.js, favicon.svg), all local
models/                the two .onnx model files (not in git)
scripts/download_models.py   one-time model download
tests/test_app.py      end-to-end test with edge cases
run_app.bat            start script
scripts/launch.py      picks a free port, starts the server, opens the browser when it is ready
docs/                  architecture diagram (SVG, PNG, interactive HTML) and its source
experiments/           the library comparison (smoke tests, full evaluation, charts)
RESEARCH.md            results of the comparison
ARCHITECTURE.md        how the app is built, and the trade-offs
```
