"""A generated texture photo -> a tileable colour map + a height map (the bonsai's bark step, kept as a tool).

    python3 plants/make_tileable.py IN.webp OUT_PREFIX [--px 4096]
      -> OUT_PREFIX_col.jpg, OUT_PREFIX_h.png

Tileable: each edge cross-faded into the opposite one (a wrap blend over 12 % of the size), so a tile meets its neighbour
with no seam. The broad lighting is taken out (the image's own soft light shading would repeat every tile). Height: the
luminance's band-pass (crevices dark, plates high), stretched to 0..1.
"""
import sys

import cv2
import numpy as np

src, out = sys.argv[1], sys.argv[2]
px = int(sys.argv[sys.argv.index("--px") + 1]) if "--px" in sys.argv else 4096
img = cv2.imread(src, cv2.IMREAD_COLOR).astype(np.float32) / 255
img = cv2.resize(img, (px, px), interpolation=cv2.INTER_AREA)
# de-light: divide out a very wide blur of the luminance
L = img.mean(-1)
Lb = cv2.GaussianBlur(L, (0, 0), px * 0.08)
img = np.clip(img * (np.median(L) / (Lb + 1e-4))[..., None] ** 0.85, 0, 1)
# wrap blend: roll by half, cross-fade the old edges (now a cross in the middle) with the unrolled image
b = int(px * 0.12)
rolled = np.roll(np.roll(img, px // 2, 0), px // 2, 1)
w = np.ones(px, np.float32)
c = px // 2
ramp = np.clip(np.abs(np.arange(px) - c) / b, 0, 1)                  # 0 at the seam cross, 1 away from it
w = np.minimum(ramp[:, None], ramp[None, :])
# away from the seams keep the rolled image; at the seams use the original (whose middle has no seam)
orig_shift = img                                                     # the original's centre is seamless
res = rolled * w[..., None] + orig_shift * (1 - w[..., None])
L = res.mean(-1)
hp = L - cv2.GaussianBlur(L, (0, 0), px * 0.02)
h = cv2.GaussianBlur(hp, (0, 0), 1.5)
h = (h - np.percentile(h, 1)) / (np.percentile(h, 99) - np.percentile(h, 1) + 1e-6)
cv2.imwrite(f"{out}_col.jpg", (np.clip(res, 0, 1) * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 93])
cv2.imwrite(f"{out}_h.png", (np.clip(h, 0, 1) * 255).astype(np.uint8))
print("wrote", f"{out}_col.jpg", f"{out}_h.png")
