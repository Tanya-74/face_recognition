# Chat 1 of 3: project setup and test data (22 Nov 2026)

Exported from a Claude Code session (VS Code extension). See `README.md` in this folder for what is kept, shortened and left out.
Messages: 4 from the user, 5 from Claude. Times are UTC.

## [2026-11-22 12:12 UTC] You

> I'm working on a take-home task: an offline face recognition app (match faces in a group photo against a folder of 50 named photos, mark others "Unknown").
>
> Right now I only want the project skeleton. Please do ONLY this:
> 1. Run git init.
> 2. Create these folders: chat_history/, experiments/data/, experiments/results/, app/
> 3. Create empty placeholder files: README.md, AI_COLLAB.md, RESEARCH.md, ARCHITECTURE.md (just a title in each, no content).
> 4. Create a .gitignore that ignores: Python junk (__pycache__, .venv), model weight files (*.onnx, *.pt, *.h5), .env, and experiments/data/ (large photos).
> 5. Make one first git commit.
>
> Do NOT write any research, code, or design decisions. I will do the research myself and tell you what to build next.

## [2026-11-22 12:13 UTC] Claude

Claude stopped here because Fable 5.2 now requires usage credits. Switch models, or send a message to choose again.

## [2026-11-22 12:13 UTC] You

> I'm working on a take-home task: an offline face recognition app (match faces in a group photo against a folder of 50 named photos, mark others "Unknown").
>
> Right now I only want the project skeleton. Please do ONLY this:
> 1. Run git init.
> 2. Create these folders: chat_history/, experiments/data/, experiments/results/, app/
> 3. Create empty placeholder files: README.md, AI_COLLAB.md, RESEARCH.md, ARCHITECTURE.md (just a title in each, no content).
> 4. Create a .gitignore that ignores: Python junk (__pycache__, .venv), model weight files (*.onnx, *.pt, *.h5), .env, and experiments/data/ (large photos).
> 5. Make one first git commit.
>
> Do NOT write any research, code, or design decisions. I will do the research myself and tell you what to build next.
> Show

<details><summary>1 tool call(s)</summary>

- Bash: Init repo, create skeleton, commit

</details>

## [2026-11-22 12:13 UTC] Claude

The skeleton is in place and committed as `0c1f7c4` on `master`. The working tree is clean.

- **Git:** The repo already existed, so `git init` just reinitialized it. This was the first commit.
- **Folders:** I created `chat_history/`, `experiments/data/`, `experiments/results/` and `app/`.
- **Placeholders:** `README.md`, `AI_COLLAB.md`, `RESEARCH.md` and `ARCHITECTURE.md` each hold only a title.
- **`.gitignore`:** It ignores `__pycache__/`, `*.pyc`, `.venv/`, `*.onnx`, `*.pt`, `*.h5`, `.env` and `experiments/data/`.
- **Empty folders:** Git doesn't track empty folders, so I put a `.gitkeep` in `chat_history/`, `experiments/results/` and `app/`. `experiments/data/` has no `.gitkeep` because the whole folder is ignored, so it exists only on your disk and won't appear in a fresh clone. Create it yourself after cloning.
- **Line endings:** Git warned that it will convert the files from LF to CRLF. That's harmless.

I didn't write any research, code or design content. Tell me what to build next.

## [2026-11-22 12:41 UTC] You

> is the dataset installed?

<details><summary>2 tool call(s)</summary>

- Bash: Inspect download script and data folder
- Bash: Check sklearn default LFW cache

</details>

## [2026-11-22 12:41 UTC] Claude

Yes, LFW is downloaded, but it isn't in the project folder.

- **Location:** [download_lfw.py](download_lfw.py) uses scikit-learn's `fetch_lfw_people`. That function caches to `C:\Users\<user>\scikit_learn_data\lfw_home`, which is outside the repo.
- **Size:** The cache is 363 MB. It holds the `lfw_funneled` images plus the pairs files and a joblib cache.
- **Project data folder:** `experiments/data/` is empty. Nothing has been copied or exported there yet.

I haven't checked that the download finished cleanly, for example the image count. I also didn't run the script.

Do you want me to export a sample set of photos into `experiments/data/` (for example 50 named people plus a group photo)? I haven't built anything yet, because you said you'd tell me what to build next.

## [2026-11-22 13:04 UTC] You

> Yes, please build the test set. First, check that the LFW download is complete: print the number of people and images, and open a few images to confirm they are colour and the right size.
>
> Then write experiments/prepare_lfw.py that:
> 1. Picks 50 people with at least 2 photos.
> 2. Saves ONE photo per person to experiments/data/folder/ named "Firstname Lastname.jpg" (with spaces, not underscores).
> 3. Saves a DIFFERENT photo of the same 50 people to experiments/data/test_same/.
> 4. Picks 20 other people NOT in the 50 and saves one photo each to experiments/data/test_unknown/.
> 5. Builds 3 simple collage "group photos" (about 10 people each) in experiments/data/groups/, where some people are from the 50 and some are from the 20 unknown. Save an answers.csv saying who is in each group photo and whether they are in the folder.
>
> Keep the code simple with easy comments. Use a fixed random seed so results are the same every time. Don't write any recognition code yet.

<details><summary>4 tool call(s)</summary>

- Bash: Verify LFW completeness and image format
- Write `c:\Users\<user>\OneDrive\Documents\TASK A\experiments\prepare_lfw.py`
- Bash: Run script twice, check determinism
- Read `c:\Users\<user>\OneDrive\Documents\TASK A\experiments\data\groups\group1.jpg`

</details>

## [2026-11-22 13:05 UTC] Claude

The LFW folder also holds a `pairs.txt` file, so I'll make the script list only the person folders.

<details><summary>3 tool call(s)</summary>

- Edit `c:\Users\<user>\OneDrive\Documents\TASK A\experiments\prepare_lfw.py`
- Bash: Run script twice, check determinism
- Read `c:\Users\<user>\OneDrive\Documents\TASK A\experiments\data\groups\group1.jpg`

</details>

## [2026-11-22 13:05 UTC] Claude

The LFW download is complete, and the test set is built. I ran `prepare_lfw.py` twice, and the answers file and a group photo were byte-identical both times.

**Download check**
- LFW has 5,749 people and 13,233 images, which matches the official LFW totals.
- 1,680 people have at least 2 photos.
- A sample of 4 images were all RGB, 250×250 pixels. I also opened `group1.jpg` and the faces are in colour.

**What `prepare_lfw.py` makes** in `experiments/data/` (script: [prepare_lfw.py](experiments/prepare_lfw.py)):
- **`folder/`:** 50 photos, one per person, named like `Adolfo Aguilar Zinser.jpg`.
- **`test_same/`:** a different photo of the same 50 people.
- **`test_unknown/`:** 20 other people, one photo each.
- **`groups/`:** `group1.jpg`, `group2.jpg` and `group3.jpg`, each 10 faces in a 5×2 grid. They have 7, 6 and 5 people from the folder, and the rest are unknown. No person appears in more than one group.
- **`groups/answers.csv`:** columns are `group_photo`, `position`, `name` and `in_folder` (yes/no). Position 1 is top-left, counting left to right and then down.

The group photos use the `test_same` photos for known people, so they differ from the reference photo in `folder/`. The collage tiles are plain LFW crops, not real group shots with faces at different sizes and angles.

The script reads LFW from `C:\Users\<user>\scikit_learn_data`, so it only runs on a machine that already has that download. It deletes and rebuilds the four output folders each time it runs.

I haven't committed anything. `experiments/data/` is git-ignored, so only `prepare_lfw.py` and your untracked `download_lfw.py` would show up. Tell me if you want them committed.

