# AI Collaboration

How I worked with the AI (Claude Code in VS Code), how we reached a shared understanding, and where I steered it to my own decisions.

**Where the proof is.** The full chat history, from my very first prompt, is in [chat_history/](chat_history/) (start with its
[README](chat_history/README.md)). Every quote below is copied from those files. Times are UTC.
Short names used below: **chat 1** is `01_2026-11-22_...md`, **chat 2** is `02_2026-11-23_to_25_...md`.

**One honest note.** I first planned to write this file myself, and I told the AI so (chat 2, 23 Nov 22:42). At the end I asked the AI to draft it
from the chat records, "whereever i made the meaningful decision" (chat 2, 24 Nov 13:47). So this text was drafted by the AI from the
real history, with the quotes checked against the files. The decisions are mine; they are all visible in the chat.
After adding the naming feature I asked for it to be added here too (chat 2, 25 Nov 14:52).

## How we worked

I gave the AI numbered requirements and let it do the building, one step at a time. I told it to ask before big choices, I kept the choices that
mattered (which library, which threshold, what goes in git), and I set gates: wait for my approval, do not merge until I say so. The AI
did the legwork (installs, scripts, tests, the app) and reported results with the limits; it did not get to decide the research outcome.
My first prompt already set this up: "I will do the research myself and tell you what to build next." (chat 1, 22 Nov 12:12).

---

## Decision 1: One Python version (3.11) for all four libraries

**AI suggested:** Use Python 3.13 first, and install an older Python only for a library that fails (this was the option marked "Recommended").
**I decided:** Use Python 3.11 for all four environments.
**Why:** So the comparison is fairer. The same Python for every library means the install times and problems are comparable. (This is the reason given in the option I chose; I did not write my own reason in the chat.)
**Evidence:** Chat excerpt #1. The result is in RESEARCH.md: every library was tried on Python 3.11.9.

## Decision 2: Time-box the comparison: smoke tests, and do not fight a library that will not install

**AI suggested / did:** Started the full evaluation with DeepFace first. Its first run hung for 10 minutes ("Nothing has been downloaded after 10 minutes, so something is hanging.")
because DeepFace prints an emoji that crashes a Windows console; the fix was `PYTHONUTF8=1`. Earlier, for `face_recognition`, it had offered "Try plain pip first (Recommended)": log exactly how it fails, then try a workaround.
**I decided:** "We are short on time, so change the plan." Stop the full DeepFace run, do a quick smoke test of all four (maximum 10 minutes each), get **one** recommendation, and wait for my approval before any full evaluation. I had accepted plain pip first; I then said that if a library hangs or fails it should log why and move on, and not fight with it.
**Why:** Time, and the install effort is itself research data. I told it to keep the DeepFace install log and timings: "they are part of my research." The AI did not retry after dlib failed to build (it needs the Visual C++ Build Tools).
**Evidence:** Chat excerpt #2 (my message, the move-on instruction, and the AI's table and recommendation); chat 2, 23 Nov 20:13 to 20:54. Results in RESEARCH.md: the smoke-test table, and `face_recognition` listed as rejected for this project, with its tests marked as not run and the reason.

## Decision 3: Pick UniFace, and check the weak spots myself

**AI suggested:** UniFace: the fastest and cleanest install, smallest footprint, fully offline. It named InsightFace as a close second (same model family) and said DeepFace might still be worth a full evaluation for accuracy.
**I decided:** "Yes, run the full evaluation (tests A to D with the threshold sweep) on UniFace only", and added a check of my own first: an annotated copy of `group1.jpg` with every detected face numbered, to see which of the 11 detections is not a real face.
**Why:** The AI's reasons were install effort, size and speed; I approved without changing the pick. I did not write more reasons in the chat. What the chat does show is that I did not accept the one odd number (11 faces in a 10-person photo) without looking at it.
**Evidence:** Chat excerpt #2. The check showed the 11th face is a real person standing in the background (RESEARCH.md, section 2, test C). RESEARCH.md also says plainly that the pick is based on install effort, size and speed and is not proven on accuracy.

## Decision 4: I own the threshold number; the AI only shows the evidence

**AI suggested:** From the sweep, a flat zone from 0.55 to 0.80 with no mistakes, and the middle of it (about 0.60 to 0.70) as the place with room for error. It also said: "I haven't picked one for you."
**I decided:** The app's default strictness is **0.62**, set in my build request, with a slider so a user can change it.
**Why:** I had asked for exactly this split from the start: a table "so I can pick a sensible threshold myself", and later "Do not choose one for me." The chat does not record why I chose 0.62. What it shows is that 0.62 is inside the AI's suggested band; both docs say to re-check it on real photos, because the test photos were easy.
**Evidence:**
> 4. Run each test across a range of thresholds and save a table, so I can pick a sensible threshold myself.

> - Tell me in simple words which threshold range looks sensible and why. Do not choose one for me.

> - **Middle of the zone:** About 0.60–0.70 leaves room for error on both sides. Real photos are harder, so same-person distances will rise and stranger distances will fall, and the safe zone will shrink.

> - **Next step:** I'd re-check on some of your own real photos before fixing a number. I haven't picked one for you.

> - Threshold slider in the UI. Default 0.62. Changing the slider should update the labels without re-processing the images (cache the embeddings).

(chat 2: my first prompt 23 Nov 20:12; my evaluation request 21:38; the AI's evaluation report 21:43; my build request with the 0.62 default 22:15.)

## Decision 5: The browser applies the threshold, so the slider is instant

**AI suggested:** A design where the server does the heavy work once and returns each face's nearest person and distance, and the browser decides "Known" or "Unknown". This satisfied my requirement.
**I decided:** I required that the slider change the labels without re-processing, and I accepted this design, listing it in the trade-offs I asked ARCHITECTURE.md to explain ("threshold applied in the browser so the slider is instant, in-memory embedding cache").
**Why:** I wanted the slider to change the labels "without re-processing the images" (my words), so that moving it is instant.
**Evidence:** The AI's five-line plan, line 3:
> 3. **Backend:** FastAPI with in-memory embedding sessions. The known-people photos are uploaded in small batches so the page can show a real progress bar. Each group-photo face comes back with its nearest person and distance, and the browser applies the threshold, so moving the slider needs no re-processing.

(chat 2, 23 Nov 22:16.) The cost is written down in ARCHITECTURE.md: the rule lives in JavaScript, and the server returns only the single nearest person.

## Decision 6: Keep the model files out of git, and make the first start download them

**AI suggested:** Keep both model files out of git (174 MB and 17 MB; GitHub refuses files over 100 MB), use a download script, and it asked whether I wanted them in git anyway through LFS.
**I decided:** Keep them out. I asked for the README to cover two ways to get them (the script, or a GitHub Release) and for ARCHITECTURE.md to explain this trade-off. Later, when I learned the Release did not exist, I told the AI: "do whatever is convenient for the company to aces" (sic). The AI then removed the dead Release route and made `run_app.bat` download the models on the first start. It tested three cases (models present, missing, and missing with no internet).
**Why:** The 100 MB limit, and my own standing rule that model files are never committed.
**Evidence:** Chat excerpt #3. One thing the AI weighed that I had not raised: committing the models would add about 190 MB to the repo permanently, because history is never rewritten.

## Decision 7: A dashboard UI that fits on one screen, in a dark theme, and I decide when it merges

**AI suggested / did:** The first UI was three stacked step cards on a scrolling page. It worked, but I wanted more.
**I decided:** A sequence of requests: nine polish features in order, then "Layout, like a dashboard" that fits on ONE screen with no page scrolling at 1366x768 and up, then small fixes (the repeated "works offline" text, the empty space in the top bar), then removing the Choose buttons and making dark the only look. I also set a gate on the work: do it on a branch and merge only after the tests pass and I say it looks good.
**Why:** My requests say who it is for: "Keep it simple for non-technical office staff. Big clear buttons, plain English." And the task brief says "The app should be easy to use and look good. The UI is part of the score." I did not stop at the first working layout; each round was a written request that changed it.
**Evidence:**
> - First commit the current state. Then work on a git branch called ui-polish. Merge to main only after the tests pass and I confirm it looks good.

> Layout, like a dashboard:

> - Face labels on the photo must not pile up on each other: shrink the text when faces are close, and put the label inside the box when there is no room.

> 1. The top bar says "Ready - works offline" and then "works offline · uniface" next to it. That is repeated. Keep the green status pill, and show only "uniface" (or nothing) in the small text.

> 5. Make the whole page a dark (black) theme, as the only look:

> The UI looks good. Please merge ui-polish into main with a normal merge (no force push), run the API test and the browser test once on main, push, and tell me which branch I am on and the last commit message.

The AI added its own check: a script that measures the text contrast of every visible piece of text in every state. It found a real bug that the eye missed:
> - **Real fix:** The test found one real problem. The count number in the selected filter chip was only 3.2:1, and I fixed it.

(chat 2: 24 Nov 10:32, 11:38, 12:03, 12:44, 13:10.)

## Decision 8: How the AI handles git (rules, and no AI trailers)

**AI suggested / did:** By default, the AI's commits carry a "Co-Authored-By: Claude" trailer and a "Generated with Claude Code" line.
**I decided:** Turn that off for this project, use short one-line plain English messages, commit and push after each step, check `git status` before every commit, and never force-push, hard-reset, rewrite history, or change the repo's visibility or settings.
**Why:** In my words: messages "in the style of a normal developer, with no trailers", and a check before every commit so that no "model files, .venv folders, API keys, or private photos" get added.
**Result:** Commits made after this point have one-line messages and no trailer. Five older commits (the skeleton and the first four library wrappers) still carry the "Co-Authored-By" line, because they were made before I gave this instruction and I told the AI not to rewrite or amend old commits.
**Evidence:**
> 1. Turn off commit attribution in your Claude Code settings for this project, so commits and PRs get no "Co-Authored-By: Claude" trailer and no "Generated with Claude Code" line. Use the correct current setting name for my Claude Code version (check the settings docs if unsure) and put it in the project's local settings file.

> - Before every commit, run git status and check that no model files, .venv folders, API keys, or private photos are being added. If anything looks wrong, stop and tell me.

> - Never use force push, reset --hard, or rewrite history.

(chat 2, 23 Nov 21:00 and 21:37.) The commit log shows the result: one-line messages and no trailers.

## Decision 9: Say the weak spots out loud

**AI suggested:** Nothing; this came from me first. The test photos are collages built from clean, large LFW faces, which is easier than a real group photo.
**I decided:** Every result must come with its limits, and the docs must be honest, not just good-looking. I asked for the limits in RESEARCH.md and for "Keep it honest" in ARCHITECTURE.md.
**Why:** In my own words, "real group photos will be harder". The task brief also says the demo uses a real group photo from the company's own folder, so the honest limits matter.
**Evidence:**
> - Note the limits of the test (collage faces are large and clean, so real group photos will be harder).

The AI wrote the limits into RESEARCH.md (section 3) and ARCHITECTURE.md ("Limits of the testing (please read)"), including that only UniFace was fully evaluated, the 0.62 default is a guess from easy data, and real small faces were not tested.

## Decision 10: Let a person name an "Unknown" face, by adding reference data only

**AI suggested:** The feature was not an AI suggestion in this chat: I pasted it in as a written task spec. While building it, the AI settled points the spec left open (for example, with a damaged saved-faces file, scans carry on with the folder photos and show a warning) and reported where two of the rules meet awkwardly on the page (fixing a typo, below).
**I decided:** A "This is..." step on an Unknown card saves that one face's embedding under the typed name, and later scans compare against the folder photos and the saved faces, also after a restart. The models are not retrained. Nothing is learned automatically, no photos are saved, a wrong name can be deleted from the page, and renaming a face that is already Known is out of scope.
**Why:** The goal in the spec: "so the same person is now recognised." It also gives reasons for its safety rules, for example refusing an out-of-date scan "so a name cannot land on the wrong face".
**Evidence:** From my message (chat 2, 25 Nov 13:57):
> This feedback loop adds reference data. **Do not retrain or fine-tune** the SCRFD or ArcFace models.

> - Save an embedding **only** when someone explicitly labels a face. Never learn automatically from matches.
> - Save no photos or face crops, only the data listed above.

> - Out of scope: relabelling faces already shown as Known, accounts or login, a database.

> 3. A **different** photo of the same person is matched to that name. Report the distance, and report it
>    honestly if it is above the 0.62 default.

From the AI's report (chat 2, 25 Nov 14:28):
> - **Fixing a typo:** relabelling replaces the entry through the API, as you specified. On the page, the face shows as Known after saving and relabelling Known faces was out of scope, so you **delete the name and label it again**.

**Result and cost:** The API test grew to 65 checks, all passing. For six people, a face saved from a group collage matched a different photo of the same person at distances 0.17 to 0.44. That is the same easy test data, not real photos. The cost, written in README.md and ARCHITECTURE.md: the app now writes biometric data to disk (`data/learned_faces.json`, not encrypted, not in git), where before it wrote nothing about people.

---

## Chat excerpt #1: Python version for the four environments

(chat 2, 23 Nov 20:13 asked, 20:25 answered)

> **Claude asked:** Some libraries may not support Python 3.13. May I install extra Python versions, such as 3.11 or 3.12 through winget or uv, for the separate environments?
> - *Yes, only if 3.13 fails (Recommended)*: Use 3.13 first. If a library won't install, log the failure and install an older Python for that library only.
> - *Yes, use 3.11 for all*: One consistent older Python for all four environments, so the comparison is fairer.

I chose **"Yes, use 3.11 for all"**, not the recommended option. The AI replied:

> You approved Python 3.11 for all four environments. I'll install it with winget.

## Chat excerpt #2: the plan change, and the recommendation I approved

(chat 2, 23 Nov 20:47 my message; 20:54 the AI's reply; 21:38 my approval)

> We are short on time, so change the plan.
> 1. Stop the full DeepFace evaluation. Keep its install log and the timing facts you have already gathered, they are part of my research.
> [...]
> If one hangs or fails, log exactly why and move on. Do not fight with it.
> [...]
> 3. Give me a short comparison table of these smoke test results and your recommendation of ONE library, with reasons. Do NOT run the full evaluation yet. Wait for my approval.

The AI's reply (after the smoke-test table; "[...]" marks parts left out here):

> - **Install:** It had the fastest, cleanest install of the three that work, with no problems.
> [...]
> - **Closest rival:** InsightFace is a close second, with the same models and more weight. Pick it instead if you want the more widely used library.
> - **Not DeepFace:** It is slower, its environment is 4 times bigger and it had two install problems. Its Facenet512 embedding is a different model, so it may still be worth a full evaluation if you care about accuracy over speed.
> [...]
> Should I run the full evaluation (tests A–D and the threshold sweep) on UniFace only? I can also switch it to InsightFace or DeepFace.

My answer:

> Yes, run the full evaluation (tests A to D with the threshold sweep) on UniFace only.
> Before that, one check: save an annotated copy of group1.jpg with every detected face boxed and numbered, so I can look at it and see which of the 11 detections is not a real face. Save it in experiments/results/.

## Chat excerpt #3: where the model files live

(chat 2: the AI's question 23 Nov 22:29; my next message 22:42; my last word on it 24 Nov 13:33)

The AI, after building the app:

> The files are `arcface_resnet.onnx` (174 MB) and `scrfd_10g.onnx` (17 MB), 191 MB in total. They are both ignored by git, and only `models/.gitkeep` is tracked. GitHub rejects any single file over 100 MB, so ArcFace could only be committed with Git LFS. My suggestion is to keep them out and use `scripts/download_models.py`. I tested that script from an empty folder, and the files it fetched were byte-identical to the ones in `models/`. Do you want them in git anyway, through LFS?

My next message asked for the trade-off to be explained, with the models kept out of git:

> 4. Write ARCHITECTURE.md: embed the diagram, explain each part in simple words, and add a short trade-offs section: UniFace over the other 3 libraries, models kept out of git (GitHub 100 MB limit, download script plus Release), threshold applied in the browser so the slider is instant, in-memory embedding cache, one library fully evaluated because of time, collage test data limits. Keep it honest.

Later, when the Release turned out not to exist:

> do whatever is convenient for the company to aces

and the AI's report:

> I did not commit the model files into the repo. That would have made the setup even simpler, but it adds about 190 MB to the repo permanently, because we never rewrite git history. It also goes against your standing rule that model files are never staged. The ARCHITECTURE.md trade-offs paragraph explains this.

---

## Honest notes: where the AI was wrong, and what I did not do

- **A too-broad command.** While chasing the DeepFace hang the AI tried a command that would kill every `python.exe`. Claude Code's safety check blocked it, and the AI said: "Killing every `python.exe` was too broad. I'll stop only my own background task." (chat 2, 23 Nov 20:39).
- **A wrong number in its own docs.** The AI had written "23 API checks" in the README and ARCHITECTURE.md. While updating the UI docs it caught that the test has 22 (the 23rd match was a helper function) and fixed both files (chat 2, 24 Nov 11:16).
- **A dead link it had put in.** The README told people to download the models from a GitHub Release that did not exist. The AI flagged it when I asked whether the project was complete (chat 2, 24 Nov 13:20), and it was then removed (Decision 6).
- **A test that compared a photo with itself.** The AI's first "different photo" check for the naming feature gave distances near zero. It found the cause and said so: "My first version of that check showed about 0.007, because the group collages are built from the `test_same` photos, so it was comparing a photo with itself." (chat 2, 25 Nov 14:28). The numbers in Decision 10 are from the corrected check.
- **Public data, offline app.** The test photos are the public LFW collection (see RESEARCH.md, section 4). No online AI or API is used inside the solution; the app runs fully offline.
- **Not yet proven.** I have not tested real group photos with small faces, with or without saved names; RESEARCH.md and ARCHITECTURE.md say so.
