"""Draws the T-72 hull-top detail map used by tools/models/weathered.gdshader.

The map is a top-down view of the hull in model (file) coordinates: forward is
-X, image x runs along X, image y along Z. Channels:
  R  height   (0.5 = hull surface; raised parts brighter, recesses darker)
  G  cavity   (baked ambient occlusion: dark in seams and around raised parts)
  B  metal    (grille mesh / bare steel mask)
The shader turns height into lighting (so shadows follow the sun in every
facing) and multiplies the paint by the cavity.

Run:  python3 tools/models/make_t72_hull_detail.py
"""
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np

PPM = 200  # pixels per metre
X0, X1, Z0, Z1 = -3.2, 3.7, -1.85, 1.85  # must match "detail_rect" in render_units.gd
W, H = int((X1 - X0) * PPM), int((Z1 - Z0) * PPM)
BASE, UP, DOWN = 128, 200, 60

height = Image.new('L', (W, H), BASE)
metal = Image.new('L', (W, H), 0)
h = ImageDraw.Draw(height)
m = ImageDraw.Draw(metal)


def px(x, z):
    return ((x - X0) * PPM, (z - Z0) * PPM)


def rect(x0, z0, x1, z1):
    a, b = px(x0, z0), px(x1, z1)
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]


def box(x0, z0, x1, z1, lift=UP, radius=0.04, seams=(), handles=()):
    """Raised stowage box with a lid seam, section seams and handles."""
    h.rounded_rectangle(rect(x0, z0, x1, z1), radius * PPM, fill=lift)
    h.rounded_rectangle(rect(x0 + 0.04, z0 + 0.04, x1 - 0.04, z1 - 0.04), radius * PPM,
                        outline=lift - 70, width=2)
    for sx in seams:
        h.line([px(sx, z0 + 0.02), px(sx, z1 - 0.02)], fill=lift - 90, width=3)
    for hx in handles:  # latch: small raised bar across the lid edge
        zc = (z0 + z1) / 2
        h.rectangle(rect(hx - 0.05, zc - 0.015, hx + 0.05, zc + 0.015), fill=min(255, lift + 45))
        h.rectangle(rect(hx - 0.07, zc - 0.03, hx - 0.05, zc + 0.03), fill=min(255, lift + 30))
        h.rectangle(rect(hx + 0.05, zc - 0.03, hx + 0.07, zc + 0.03), fill=min(255, lift + 30))


def bolts(x0, z0, x1, z1, step=0.22, r=0.018):
    n = max(1, int(np.hypot(x1 - x0, z1 - z0) / step))
    for i in range(n + 1):
        t = i / n
        cx, cz = px(x0 + (x1 - x0) * t, z0 + (z1 - z0) * t)
        h.ellipse([cx - r * PPM, cz - r * PPM, cx + r * PPM, cz + r * PPM], fill=225)


def seam(x0, z0, x1, z1, fill=DOWN + 20, width=3):
    h.line([px(x0, z0), px(x1, z1)], fill=fill, width=width)


def grille(x0, z0, x1, z1):
    """Engine grille: recessed mesh with a raised frame and X bracing."""
    h.rectangle(rect(x0, z0, x1, z1), fill=DOWN + 25)
    m.rectangle(rect(x0, z0, x1, z1), fill=255)
    step = 0.045
    x = x0 + step
    while x < x1:  # mesh bars
        h.line([px(x, z0), px(x, z1)], fill=BASE - 10, width=2)
        x += step
    z = z0 + step
    while z < z1:
        h.line([px(x0, z), px(x1, z)], fill=BASE - 10, width=2)
        z += step
    h.rectangle(rect(x0, z0, x1, z1), outline=UP, width=7)
    h.line([px(x0, z0), px(x1, z1)], fill=UP, width=9)
    h.line([px(x0, z1), px(x1, z0)], fill=UP, width=9)


for side in (-1, 1):
    zi, zo = (1.12, 1.66)  # fender strip between the hull edge and the outer rim
    z0, z1 = (side * zi, side * zo) if side > 0 else (side * zo, side * zi)
    # Front fender: ribbed mudguard, a big box with latches, and a toolbox.
    for i in range(5):
        x = -3.05 + i * 0.05
        seam(x, z0 + 0.03, x, z1 - 0.03, fill=UP - 20, width=4)
    box(-2.75, z0 + 0.05, -1.55, z1 - 0.05, seams=(-2.15,), handles=(-2.45, -1.85))
    box(-1.45, z0 + 0.08, -0.95, z1 - 0.08, lift=UP - 20, handles=(-1.2,))
    # Rear fender: long boxes in sections with handles.
    box(0.85, z0 + 0.05, 2.05, z1 - 0.05, seams=(1.45,), handles=(1.15, 1.75))
    box(2.15, z0 + 0.05, 3.3, z1 - 0.05, seams=(2.72,), handles=(2.43, 3.0))
    # Bolt rows along the outer rim and the hull edge.
    zr = side * (zo + 0.05)
    bolts(-3.05, zr, 3.45, zr)
    bolts(-0.9, side * (zi - 0.03), 0.8, side * (zi - 0.03), step=0.3)

# Glacis: weld seams at the edges and a splash board.
seam(-2.75, -1.05, -1.4, -1.05); seam(-2.75, 1.05, -1.4, 1.05)
h.line([px(-2.55, -0.9), px(-2.2, 0.0), px(-2.55, 0.9)], fill=UP, width=10)  # V splash board

# Engine deck, front to rear: louvres, access hatch with a rim, two grilles.
for i in range(9):
    x = 1.45 + i * 0.045
    seam(x, -0.85, x, 0.85, fill=DOWN, width=4)
h.rounded_rectangle(rect(1.95, -0.88, 2.62, 0.88), 0.1 * PPM, outline=UP, width=9)
h.rounded_rectangle(rect(2.03, -0.8, 2.54, 0.8), 0.08 * PPM, outline=DOWN + 30, width=3)
bolts(2.0, -0.84, 2.57, -0.84, step=0.14)
bolts(2.0, 0.84, 2.57, 0.84, step=0.14)
for i in range(3):  # lifting eyes / hinges on the hatch
    x, z = px(2.3, -0.5 + i * 0.5)
    h.ellipse([x - 8, z - 8, x + 8, z + 8], fill=UP + 30)
grille(2.72, -0.9, 3.42, -0.06)
grille(2.72, 0.06, 3.42, 0.9)
seam(3.47, -1.0, 3.47, 1.0, fill=DOWN, width=5)  # stern edge seam

height = height.filter(ImageFilter.GaussianBlur(1.2))  # soft bevels
harr = np.asarray(height, dtype=np.float32) / 255.0
# Cavity: darker where the surface sits below its surroundings (seams, the
# ground around raised boxes).
wide = np.asarray(height.filter(ImageFilter.GaussianBlur(9)), dtype=np.float32) / 255.0
cavity = np.clip(1.0 - np.maximum(wide - harr, 0.0) * 5.0, 0.0, 1.0)
out = np.stack([harr, cavity, np.asarray(metal, dtype=np.float32) / 255.0], axis=2)
Image.fromarray((out * 255).astype(np.uint8), 'RGB').save('tools/models/t72_hull_detail.png')
print('wrote tools/models/t72_hull_detail.png', W, H)
