"""Generated flat-lay photos of single leaves (tip up, base down, on white) -> clean cut-out leaf cards for 3D plants.

    python3 leaf_cutout.py OUT_DIR leaf1.webp leaf2.webp ... [--solid] [--delight] [--keep-stem]

Per leaf: OUT_DIR/<name>_col.png (RGBA, the white fringe at the edge re-coloured from inside the leaf, the petiole stub removed,
2048 px tall), <name>_bump.png (veins in grooves, the panels between them puffed), and OUT_DIR/atlas.json (aspect, where the
petiole joins as UV v from the bottom, the midrib's column as UV u) so a generator can place each card on its twig.
  --solid      no holes in the leaf (pale bands or a pale midrib must not be cut out as background)
  --delight    take the broad studio highlight out (small glossy leaves: it repeats on every card and reads milky / plastic)
  --keep-stem  keep the petiole (when the stem is what attaches the card)
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT, SRC = Path(args[0]), [Path(a) for a in args[1:]]
SOLID, DELIGHT, KEEP_STEM = "--solid" in sys.argv, "--delight" in sys.argv, "--keep-stem" in sys.argv
HPX = 2048
OUT.mkdir(parents=True, exist_ok=True)
atlas_f = OUT / "atlas.json"
atlas = json.loads(atlas_f.read_text()) if atlas_f.exists() else {}
for f in SRC:
    name = f.stem.replace("_0", "")
    img = cv2.cvtColor(cv2.imread(str(f)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    hsv = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32) / 255
    # the leaf by its colour (saturated green / yellow / bronze); the soft grey drop shadow is not saturated
    m = (hsv[..., 1] > 0.2) | ((img[..., 1] - np.maximum(img[..., 0], img[..., 2]) > 0.05) & (img.min(-1) < 0.8)) | (img.max(-1) < 0.62)
    m = m.astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)   # the leaf only
    if SOLID:                                                            # everything inside the outline
        ff = m.copy() * 255; mask_ = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8)
        cv2.floodFill(ff, mask_, (0, 0), 128)
        m = (ff != 128).astype(np.uint8)
    inv = 1 - m                                                          # specular glints read as background: fill the small ones
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 600:
            m[lab == i] = 1
    H, W = m.shape
    ys, xs = np.nonzero(m)
    cx = int(np.median(xs[ys < ys.min() + (ys.max() - ys.min()) * 0.5]))    # the midrib's column (upper half)
    loose = ((1 - img.min(-1)) > 0.1).astype(np.uint8)                  # a pale midrib: keep its column by a looser test
    band = np.zeros_like(m); band[ys.min():ys.max() + 1, cx - 40:cx + 41] = 1
    m = np.maximum(m, loose * band)
    if not KEEP_STEM:                                                    # the petiole stub: thin, bottom-centre, opened away
        low = np.zeros_like(m); low[int(ys.min() + 0.75 * (ys.max() - ys.min())):, cx - W // 8:cx + W // 8] = 1
        opened = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (131, 131)))
        m = np.where(low > 0, opened, m)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    col = m[:, cx]; yj = y1
    while yj > y0 and col[yj] == 0:                                      # the petiole joint, up the midrib from the bottom
        yj -= 1
    edge = (cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2) - cv2.erode(m, np.ones((3, 3), np.uint8), iterations=3)).astype(np.uint8)
    fixed = cv2.inpaint((img * 255).astype(np.uint8), edge, 5, cv2.INPAINT_TELEA).astype(np.float32) / 255   # no white fringe
    alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8)
    pad = 12
    x0, x1, y0, y1 = max(x0 - pad, 0), min(x1 + pad, W - 1), max(y0 - pad, 0), min(y1 + pad, H - 1)
    rgba = np.dstack([fixed, alpha])[y0:y1 + 1, x0:x1 + 1]
    h, w = rgba.shape[:2]
    rgba = cv2.resize(rgba, (max(int(round(HPX * w / h)), 64), HPX), interpolation=cv2.INTER_AREA)
    if DELIGHT:                                                          # divide out the broad lighting inside the leaf
        a_ = rgba[..., 3]; inside = (a_ > 0.5).astype(np.float32)
        L = rgba[..., :3].mean(-1); sig = rgba.shape[1] * 0.12
        Lb = cv2.GaussianBlur(L * inside, (0, 0), sig) / (cv2.GaussianBlur(inside, (0, 0), sig) + 1e-6)
        gain = np.clip(np.percentile(L[inside > 0], 30) / (Lb + 1e-4), 0.3, 1.6) ** 0.9
        rgba[..., :3] = np.clip(rgba[..., :3] * gain[..., None], 0, 1)
    lum = cv2.cvtColor((rgba[..., :3] * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    hp = lum - cv2.GaussianBlur(lum, (0, 0), 6)
    bump = 0.5 - hp * 3.0 - cv2.GaussianBlur(hp, (0, 0), 14) * 4.0
    bump = (bump - np.percentile(bump, 1)) / (np.percentile(bump, 99) - np.percentile(bump, 1) + 1e-6)
    cv2.imwrite(str(OUT / f"{name}_col.png"), cv2.cvtColor((np.clip(rgba, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
    cv2.imwrite(str(OUT / f"{name}_bump.png"), (np.clip(bump, 0, 1) * 255).astype(np.uint8))
    atlas[name] = {"aspect": round(w / h, 4), "joint_v": round(float(1 - (yj - y0) / h), 4), "midrib_u": round(float((cx - x0) / w), 4)}
    print(name, atlas[name])
atlas_f.write_text(json.dumps(atlas, indent=1))
