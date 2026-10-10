"""Малювання рамок і службових написів поверх кадру.

Шрифти OpenCV (Hershey) не мають кирилиці, тому написи латиницею."""

from __future__ import annotations

import time

import cv2
import numpy as np

from .config import DisplayConfig
from .pipeline import (STATUS_NO_SIGNAL, STATUS_SCENE_CHANGE, STATUS_WARMUP,
                       DetectionState)

FONT = cv2.FONT_HERSHEY_SIMPLEX
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)

STATUS_TEXT = {
    STATUS_NO_SIGNAL: ("NO SIGNAL", RED),
    STATUS_WARMUP: ("LEARNING BACKGROUND", YELLOW),
    STATUS_SCENE_CHANGE: ("SCENE CHANGE", YELLOW),
}


def _text(img: np.ndarray, text: str, org: tuple[int, int], scale: float,
          color: tuple[int, int, int], thickness: int) -> None:
    """Текст з чорним обведенням — читається і на світлому, і на темному фоні."""
    cv2.putText(img, text, org, FONT, scale, BLACK, thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, scale, color, thickness, cv2.LINE_AA)


def draw(image: np.ndarray, state: DetectionState | None, cfg: DisplayConfig,
         now: float | None = None) -> np.ndarray:
    """Малює поверх image (змінює його на місці) і повертає його ж."""
    h, w = image.shape[:2]
    scale = cfg.font_scale * w / 720
    thick = max(1, round(2 * w / 720))
    line_h = round(30 * scale / 0.7)
    color = tuple(int(c) for c in cfg.box_color)

    if state is not None:
        for obj in state.objects:
            x, y, bw, bh = obj.box
            cv2.rectangle(image, (x, y), (x + bw, y + bh), color, cfg.box_thickness)

    # Відступ від країв: аналогові монітори обрізають краї кадру (overscan).
    margin_x, margin_y = round(w * 0.05), round(h * 0.05)

    if cfg.show_clock:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        _text(image, stamp, (margin_x, margin_y + line_h), scale, WHITE, thick)

    if cfg.show_count and state is not None and state.objects:
        label = f"OBJ: {len(state.objects)}"
        (tw, _), _ = cv2.getTextSize(label, FONT, scale, thick)
        _text(image, label, (w - margin_x - tw, margin_y + line_h), scale, RED, thick)

    if cfg.show_status and state is not None and state.status in STATUS_TEXT:
        label, col = STATUS_TEXT[state.status]
        big = scale * (1.6 if state.status == STATUS_NO_SIGNAL else 1.0)
        (tw, th), _ = cv2.getTextSize(label, FONT, big, thick + 1)
        if state.status == STATUS_NO_SIGNAL:
            org = ((w - tw) // 2, (h + th) // 2)
        else:
            org = (margin_x, h - margin_y)
        _text(image, label, org, big, col, thick + 1)
    return image
