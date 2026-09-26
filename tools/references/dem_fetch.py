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
for name, lat, lon in [("carpathians", 48.15, 24.53), ("alps", 46.55, 8.0), ("caucasus", 43.25, 42.6)]:
    a, mpp = area(lat, lon, 24)
    np.save(f"dem/{name}.npy", a); open(f"dem/{name}.mpp", "w").write(str(mpp))
    print(name, a.shape, round(mpp, 1), a.min(), a.max())
