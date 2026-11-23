"""Draw every detected face on an image: box + running number (+ grid cell).

Usage: <venv python> experiments/annotate_faces.py wrap_uniface data/groups/group1.jpg results/uniface_group1_annotated.jpg
Paths are relative to experiments/. Grid cell = collage position (1 = top-left,
counting left to right, then down), assuming 250 px tiles, 5 columns.
"""
import importlib, os, sys
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
w = importlib.import_module(sys.argv[1])
img = cv2.imread(os.path.join(HERE, sys.argv[2]))
TILE, COLS = 250, 5
for i, ((x, y, bw, bh), _) in enumerate(w.get_faces(img), start=1):
    cell = int((y + bh / 2) // TILE) * COLS + int((x + bw / 2) // TILE) + 1
    print(f"face {i:2d}: box x={x} y={y} w={bw} h={bh}  grid cell {cell}")
    cv2.rectangle(img, (x, y), (x + bw, y + bh), (0, 0, 255), 2)
    cv2.rectangle(img, (x, y), (x + 34, y + 26), (0, 0, 255), -1)
    cv2.putText(img, str(i), (x + 3, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
cv2.imwrite(os.path.join(HERE, sys.argv[3]), img)
