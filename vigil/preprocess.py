"""Підготовка кадру аналогової камери до аналізу."""

from __future__ import annotations

import cv2
import numpy as np

from .config import PreprocessConfig


class Preprocessor:
    def __init__(self, cfg: PreprocessConfig):
        self.cfg = cfg
        self.scale = 1.0  # множник: координати аналізу -> координати вихідного кадру

    def __call__(self, image: np.ndarray) -> np.ndarray:
        """BGR-кадр -> зменшений, знешумлений кадр у відтінках сірого."""
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if self.cfg.deinterlace:
            # Беремо лише парні рядки (одне поле) — на рухомих об'єктах
            # зникає «гребінка», яка інакше дає хибні контури.
            gray = gray[::2]
        target_w = min(self.cfg.process_width, w)
        target_h = round(h * target_w / w)
        gray = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)
        self.scale = w / target_w
        k = self.cfg.blur_kernel
        if k > 1:
            gray = cv2.GaussianBlur(gray, (k | 1, k | 1), 0)
        return gray


def signal_present(gray: np.ndarray, min_stddev: float) -> bool:
    """Без сигналу аналоговий приймач/декодер видає рівний синій або чорний кадр."""
    return float(gray.std()) >= min_stddev
