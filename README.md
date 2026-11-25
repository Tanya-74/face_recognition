# Face Recognition

Who is in the photo? You give the app a folder of known people (one photo each, named after the person) and one
group photo. It puts a box and a name on every face, or "Unknown", and lists the results.

It runs on your own computer and works without internet once it is installed. No photo is sent anywhere.

## Quick demo (Windows)

You need [Python 3.11](https://www.python.org/downloads/release/python-3119/) (tick "Add python.exe to PATH" while
installing, or run `winget install Python.Python.3.11`).

1. Get the project: `git clone https://github.com/Tanya-74/face_recognition.git`, or use "Download ZIP" on GitHub
   and unpack it.
2. Double-click **`demo.bat`**.

The first time, it creates a virtual environment in `.venv`, installs the packages (about 500 MB) and downloads the
two face models (about 190 MB). This needs internet and takes a few minutes. Then your browser opens and the app runs
by itself on the sample photos: 50 known people and a group photo with 11 faces, of which 7 should be named and
4 shown as unknown. Reading the 50 photos takes half a minute to a few minutes, depending on the computer.

Keep the black window open while using the app. Closing it stops the app. Later starts of `demo.bat` skip the
installation.

The sample photos come from the public LFW face collection. Names you save during a demo are kept apart from your
own, in `data\demo_faces.json`, and cleared when the next demo starts.

## Using it with your own photos

Double-click **`run_app.bat`** (after `demo.bat` has run once, or after the manual install below). The browser opens
at <http://127.0.0.1:8000>. If another program already uses port 8000, the app takes the next free one and prints the
address in the black window.

1. Click box 1, or drag a folder onto it: one photo per person, named after them, for example `Priya Sharma.jpg`.
2. Click box 2, or drag a photo onto it: the group photo (JPG, PNG, BMP or WEBP).
3. Press **Run**.

Wait for the "Starting up..." note at the top to disappear first. A red note means something is wrong
(see Troubleshooting).

On the result you can:

- point at a face or its card to highlight it, and filter by All, Known or Unknown
- move the **Strictness** slider (default 0.62). Lower means more "Unknown" and fewer wrong names. The labels change
  at once, without reading the photos again
- check the folder with **Known people** (thumbnails) and **Folder notes** (photos that were skipped, and why)
- swap photos with **Change folder** and **Change photo**, or drop a new one on the picture
- save the marked-up picture (**Download PNG**) or the list (**Download CSV**, opens in Excel)

Running again with the same folder is quick, because the folder is only read once until the app is restarted.

The number on each card is the distance between two faces: 0 is identical, larger is more different. In our tests any
limit from 0.55 to 0.80 gave no mistakes ([RESEARCH.md](RESEARCH.md)), but the test photos were easy ones. Check the
slider on your own photos.

## Naming an unknown face

On an Unknown card, press **This is...**, type the name and press **Save**. The app checks the photo again, and from
then on recognises that person in later scans, including after a restart. They do not need a photo in the folder,
although a folder still has to be chosen before you press Run.

- A name has 1 to 80 characters and cannot be "Unknown". An existing name keeps its spelling.
- A face is saved only when you press Save. Nothing is learned on its own, and the models are not retrained.
- Made a mistake? Open **Saved people**, delete the name and label the face again. Deleting removes every saved face
  of that name. A face already shown as Known cannot be renamed on its card.

### What is stored

Only the faces you name, in `data\learned_faces.json`: an id, the name, 512 numbers describing the face, the model
name and the date. No photos are saved. The file is not encrypted and this is biometric data, so treat it with care.

To forget everyone, close the app and delete the `data` folder. To keep the file somewhere else, set the
`FACE_LEARNED_FILE` environment variable to a full path. If the file is damaged, the app warns you, carries on with
the folder photos only, and leaves the file as it is.

## Manual install

`demo.bat` does all of this for you. To do it by hand, in PowerShell, in the project folder:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\download_models.py
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000>. Stop with Ctrl+C.

The models are not in the repository because one of them is 174 MB and GitHub refuses files over 100 MB.
`download_models.py` (also run by `demo.bat` and `run_app.bat` when needed) checks each file with its SHA-256 hash.

For a computer with no internet at all, copy both files into `models\` from another computer, and compare them with
`Get-FileHash models\*.onnx -Algorithm SHA256`. The Python packages still have to be installed.

| File | SHA-256 |
|---|---|
| `scrfd_10g.onnx` | `5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91` |
| `arcface_resnet.onnx` | `4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43` |

## Checking that it works offline

Run the app once while online, close it, turn Wi-Fi off, and start `run_app.bat` again. Everything should work as
before: the page loads nothing from the web, and the server only listens on `127.0.0.1`, so other computers cannot
reach it.

There is also an automatic test with network access blocked:

```powershell
.venv\Scripts\python.exe tests\test_app.py
```

It runs 65 checks (bad files, very large pictures, naming faces, a damaged saved-faces file and so on), takes one to
six minutes, and never touches your `data` folder.

## Unusual input

- A folder photo with no face is skipped. With several faces, the largest one is used. Both are listed in Folder notes.
- Files that are not pictures are ignored or skipped with a note.
- Two photos with the same name are both used for that person.
- Pictures are shrunk to 1600 px on the long side. Anything over 120 megapixels or 40 MB is refused.
- Phone photos are turned upright automatically.
- A folder can hold up to 5000 photos. Large folders show a progress bar and a Cancel button.

## Troubleshooting

| Problem | What to do |
|---|---|
| `demo.bat` says Python 3.11 was not found | Install Python 3.11, tick "Add python.exe to PATH", and double-click it again. |
| Packages fail to install | Check the internet connection and run it again. |
| Packages install but cannot be loaded | Install the Microsoft Visual C++ Redistributable (x64). |
| "The .venv folder is broken" | Delete the `.venv` folder and run `demo.bat` again. |
| "Face models not found" or "Model files missing" | Run `run_app.bat` while online, or copy the two files into `models\` (see Manual install). |
| The page does not open, or "Cannot reach the app" | Keep the black window open and read what it says. Use the address printed there. |
| "Your session expired" | The app was restarted. Choose the folder again and press Run. |
| Someone known shows as Unknown | Raise the slider a little and check that their folder photo shows the face clearly. |
| A stranger gets a name | Lower the slider. If the name was saved with "This is...", delete it under Saved people. |
| PowerShell blocks scripts | Use the `.venv\Scripts\python.exe` commands shown above. The `.bat` files are not affected. |

## Limits

The tests used collages made from LFW face photos, where every face is large, sharp and facing the camera. Real group
photos are harder: small, turned or partly hidden faces may be missed or come out as Unknown. This has not been tested.
See "Limits of the testing" in [ARCHITECTURE.md](ARCHITECTURE.md).

## What is in the repository

```
demo.bat                    sets up and runs the demo
run_app.bat                 starts the app
requirements.txt            Python packages
app/main.py                 web server (FastAPI) and JSON API
app/engine.py               picture preparation and matching
app/face_backend.py         the face library, behind two functions
app/learned.py              the saved faces file
app/static/                 the web page (HTML, CSS, JavaScript)
scripts/demo.py             the steps behind demo.bat
scripts/launch.py           finds a free port and opens the browser
scripts/download_models.py  one-time model download
models/                     model files (not in git)
tests/test_app.py           end-to-end test
experiments/                library comparison, test photos and results
download_lfw.py             fetches the LFW photos for the experiments (not needed to run the app)
docs/                       architecture diagram
chat_history/               AI chat history
```

## More

- [RESEARCH.md](RESEARCH.md): the libraries compared and why [UniFace](https://github.com/yakhyo/uniface)
  (SCRFD detector, ArcFace recognition) was chosen
- [ARCHITECTURE.md](ARCHITECTURE.md): how the app is built, and the trade-offs
- [AI_COLLAB.md](AI_COLLAB.md): how AI was used on this project, and which decisions were mine
