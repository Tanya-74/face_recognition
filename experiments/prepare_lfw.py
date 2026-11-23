"""Build the test set from the LFW dataset (no recognition code here).

Output (all inside experiments/data/):
  folder/        50 people, one photo each, named "Firstname Lastname.jpg"
  test_same/     a DIFFERENT photo of the same 50 people
  test_unknown/  20 other people, one photo each
  groups/        3 collage "group photos" + answers.csv

Run:  python experiments/prepare_lfw.py
"""
import csv
import os
import random
import shutil

from PIL import Image

# ---- settings ----
SEED = 42                      # fixed seed -> same result every run
N_KNOWN = 50                   # people in the folder
N_UNKNOWN = 20                 # people NOT in the folder
KNOWN_PER_GROUP = [7, 6, 5]    # how many known people in each group photo
PEOPLE_PER_GROUP = 10          # total faces per group photo
COLS = 5                       # collage grid: 5 columns x 2 rows

# LFW location (where scikit-learn downloaded it)
LFW_DIR = os.path.join(os.path.expanduser("~"), "scikit_learn_data", "lfw_home", "lfw_funneled")

# output location (relative to this script, so it works from anywhere)
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FOLDER = os.path.join(DATA, "folder")
SAME = os.path.join(DATA, "test_same")
UNKNOWN = os.path.join(DATA, "test_unknown")
GROUPS = os.path.join(DATA, "groups")

rng = random.Random(SEED)


def pretty_name(dir_name):
    """'Aaron_Eckhart' -> 'Aaron Eckhart'"""
    return dir_name.replace("_", " ")


def photos_of(person):
    """Sorted list of full photo paths for one person."""
    d = os.path.join(LFW_DIR, person)
    return [os.path.join(d, f) for f in sorted(os.listdir(d))]


def save_jpg(src, dst):
    """Copy a photo as an RGB jpg."""
    Image.open(src).convert("RGB").save(dst, quality=95)


# 1. start from clean output folders (so re-running gives identical results)
for d in (FOLDER, SAME, UNKNOWN, GROUPS):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)

# 2. list all people (sorted, so the seed gives the same picks every time)
everyone = sorted(p for p in os.listdir(LFW_DIR) if os.path.isdir(os.path.join(LFW_DIR, p)))
with_2plus = [p for p in everyone if len(photos_of(p)) >= 2]
print(f"LFW: {len(everyone)} people, {len(with_2plus)} have 2+ photos")

# 3. pick the 50 known people
known = sorted(rng.sample(with_2plus, N_KNOWN))

# 4. pick 20 unknown people (anyone not in the 50)
others = [p for p in everyone if p not in known]
unknown = sorted(rng.sample(others, N_UNKNOWN))

# 5. save the photos
same_photo = {}     # name -> path of the test_same photo (used for collages)
for person in known:
    name = pretty_name(person)
    a, b = rng.sample(photos_of(person), 2)     # two different photos
    save_jpg(a, os.path.join(FOLDER, name + ".jpg"))
    save_jpg(b, os.path.join(SAME, name + ".jpg"))
    same_photo[name] = os.path.join(SAME, name + ".jpg")

unknown_photo = {}  # name -> path of the test_unknown photo
for person in unknown:
    name = pretty_name(person)
    src = rng.choice(photos_of(person))
    save_jpg(src, os.path.join(UNKNOWN, name + ".jpg"))
    unknown_photo[name] = os.path.join(UNKNOWN, name + ".jpg")

# 6. build the group photos (each person is used in at most one group)
known_names = sorted(same_photo)
unknown_names = sorted(unknown_photo)
rng.shuffle(known_names)
rng.shuffle(unknown_names)

rows = []   # rows for answers.csv
for g, n_known in enumerate(KNOWN_PER_GROUP, start=1):
    n_unknown = PEOPLE_PER_GROUP - n_known

    # take the next people from each shuffled list
    members = [(known_names.pop(), True) for _ in range(n_known)]
    members += [(unknown_names.pop(), False) for _ in range(n_unknown)]
    rng.shuffle(members)    # mix known and unknown positions

    # paste faces into a grid
    tile = 250
    n_rows = (len(members) + COLS - 1) // COLS
    canvas = Image.new("RGB", (COLS * tile, n_rows * tile), "white")
    for i, (name, in_folder) in enumerate(members):
        path = same_photo[name] if in_folder else unknown_photo[name]
        face = Image.open(path).convert("RGB").resize((tile, tile))
        canvas.paste(face, ((i % COLS) * tile, (i // COLS) * tile))
        rows.append([f"group{g}.jpg", i + 1, name, "yes" if in_folder else "no"])

    canvas.save(os.path.join(GROUPS, f"group{g}.jpg"), quality=95)

# 7. save the answers (position 1 = top-left, counting left to right, then down)
with open(os.path.join(GROUPS, "answers.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["group_photo", "position", "name", "in_folder"])
    w.writerows(rows)

print(f"folder: {len(os.listdir(FOLDER))}, test_same: {len(os.listdir(SAME))}, "
      f"test_unknown: {len(os.listdir(UNKNOWN))}, groups: 3 + answers.csv")
