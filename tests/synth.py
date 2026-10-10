"""Синтетичне «аналогове» відео для тестів: текстурований фон, шум, рухомий об'єкт."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

W, H = 720, 576


@dataclass
class Mover:
    start: int  # кадр появи
    end: int  # кадр зникнення
    x0: float
    y0: float
    vx: float  # пікселів за кадр
    vy: float
    w: int = 40
    h: int = 70

    def box(self, i: int) -> tuple[int, int, int, int] | None:
        if not self.start <= i < self.end:
            return None
        t = i - self.start
        return round(self.x0 + self.vx * t), round(self.y0 + self.vy * t), self.w, self.h


def background(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.integers(60, 180, (H // 16, W // 16, 3), dtype=np.uint8)
    bg = cv2.resize(base, (W, H), interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(bg, (7, 7), 0)


def frames(n: int, movers: list[Mover], noise: float = 6.0, seed: int = 0,
           brightness: dict[int, int] | None = None):
    """Генерує (кадр, [справжні рамки]). brightness: {з_кадру: зсув яскравості}."""
    rng = np.random.default_rng(seed + 1)
    bg = background(seed).astype(np.int16)
    shift = 0
    for i in range(n):
        if brightness and i in brightness:
            shift = brightness[i]
        img = bg + shift + rng.normal(0, noise, bg.shape).astype(np.int16)
        truth = []
        for m in movers:
            b = m.box(i)
            if b is not None:
                x, y, w, h = b
                img[y:y + h, x:x + w] = (30, 30, 200)
                truth.append(b)
        yield np.clip(img, 0, 255).astype(np.uint8), truth


def write_video(path: Path, n: int, movers: list[Mover], fps: float = 25.0, **kw) -> list:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (W, H))
    truths = []
    for img, truth in frames(n, movers, **kw):
        writer.write(img)
        truths.append(truth)
    writer.release()
    return truths
