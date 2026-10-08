# -*- coding: utf-8 -*-
"""Генерує текстури наліпок (логотип і напис Rovertech) — стилізований трафарет, PNG з альфою.
Логотип — товарний знак Rovertech: наліпки окремими об'єктами Decal_*, їх можна вимкнути/замінити.
Запуск: python3 make_decals.py   (потрібен Pillow і numpy)"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
S = 4  # суперсемплінг


def worn_alpha(img, seed, amount=0.22):
    """Трафаретна фарба з потертостями: альфа × шум."""
    rng = np.random.default_rng(seed)
    a = np.asarray(img.split()[3]).astype(np.float32) / 255.0
    h, w = a.shape
    n = np.zeros((h, w), np.float32)
    for sc, wt in ((64, 0.5), (24, 0.3), (8, 0.2)):
        g = rng.random((h // sc + 2, w // sc + 2)).astype(np.float32)
        g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
        n += g * wt
    a = a * np.clip((n - amount) * 4.0, 0.0, 1.0) ** 0.6
    out = img.copy()
    out.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return out


def logo(size=512):
    W = H = size * S
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (17, 17, 15, 255)
    # рамка «екран» з антеною
    x0, x1 = 0.10 * W, 0.90 * W
    y0, y1 = 0.30 * H, 0.90 * H
    t = 0.075 * W
    d.rounded_rectangle((x0, y0, x1, y1), radius=0.03 * W, outline=c, width=int(t))
    d.rectangle((0.44 * W, y1 - t - 2, 0.56 * W, y1 + 2), fill=(0, 0, 0, 0))     # розрив знизу
    d.rectangle((0.48 * W, 0.12 * H, 0.52 * W, y0 + 2), fill=c)                  # щогла
    d.ellipse((0.42 * W, 0.04 * H, 0.58 * W, 0.18 * H), fill=c)                  # кулька
    # усередині — два трикутники «краватка» і ромб знизу
    ix0, ix1, iy0, iy1 = x0 + t * 1.6, x1 - t * 1.6, y0 + t * 1.6, y1 - t * 1.2
    d.polygon([(ix0, iy0), (0.47 * W, iy1 - 0.02 * H), (ix0, iy1)], fill=c)
    d.polygon([(ix1, iy0), (0.53 * W, iy1 - 0.02 * H), (ix1, iy1)], fill=c)
    d.polygon([(0.5 * W, iy1 - 0.16 * H), (0.56 * W, iy1 + 0.03 * H), (0.44 * W, iy1 + 0.03 * H)], fill=c)
    im = im.resize((size, size), Image.LANCZOS)
    return worn_alpha(im, 7, 0.10)


def text(w=1024, h=180):
    W, H = w * S, h * S
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(f, int(H * 0.78))
            break
        except OSError:
            font = ImageFont.load_default()
    bb = d.textbbox((0, 0), "Rovertech", font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((W - tw) / 2 - bb[0], (H - th) / 2 - bb[1]), "Rovertech", font=font, fill=(17, 17, 15, 255))
    im = im.resize((w, h), Image.LANCZOS)
    return worn_alpha(im, 11, 0.08)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    logo().save(os.path.join(OUT, "Zmiy_Decal_Logo.png"))
    text().save(os.path.join(OUT, "Zmiy_Decal_Text.png"))
    print("decals ->", OUT)
