import math, sys, io, urllib.request, numpy as np
from PIL import Image
Z = 12
def tile(x, y):
    url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png"
    a = np.asarray(Image.open(io.BytesIO(urllib.request.urlopen(url, timeout=30).read())).convert("RGB")).astype(np.float64)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
def area(lat, lon, km):
    n = 2 ** Z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    mpp = 40075016.7 * math.cos(math.radians(lat)) / n / 256
    half = km * 1000 / 2 / mpp / 256
    x0, x1, y0, y1 = int(fx - half), int(fx + half), int(fy - half), int(fy + half)
    rows = [np.hstack([tile(x, y) for x in range(x0, x1 + 1)]) for y in range(y0, y1 + 1)]
    big = np.vstack(rows)
    cx, cy = int((fx - x0) * 256), int((fy - y0) * 256)
    hp = int(km * 1000 / 2 / mpp)
    return big[cy - hp:cy + hp, cx - hp:cx + hp], mpp
AREAS = [("emmental", 46.95, 7.75), ("chianti", 43.45, 11.35), ("langhe", 44.60, 8.05), ("zakarpattia", 48.45, 23.30)]
for name, lat, lon in AREAS:
    a, mpp = area(lat, lon, 32)
    np.save(f"dem32/{name}.npy", a); open(f"dem32/{name}.mpp", "w").write(str(mpp))
    print(name, a.shape, round(mpp, 1), a.min(), a.max())
