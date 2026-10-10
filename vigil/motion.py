"""Виявлення рухомих об'єктів відніманням фону (для нерухомої камери)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .config import MotionConfig

Box = tuple[int, int, int, int]  # x, y, w, h


@dataclass
class MotionResult:
    boxes: list[Box]
    mask: np.ndarray
    foreground_pct: float
    scene_change: bool
    warming_up: bool


class MotionDetector:
    def __init__(self, cfg: MotionConfig):
        self.cfg = cfg
        k = max(1, cfg.morph_kernel)
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        self.reset()

    def reset(self) -> None:
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=self.cfg.history,
            varThreshold=self.cfg.var_threshold,
            detectShadows=False,
        )
        self._frames = 0

    def __call__(self, gray: np.ndarray) -> MotionResult:
        mask = self._bg.apply(gray)
        self._frames += 1
        if self._frames <= self.cfg.warmup_frames:
            return MotionResult([], mask, 0.0, False, True)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
        mask = cv2.dilate(mask, self._kernel, iterations=self.cfg.dilate_iterations)
        fg_pct = 100.0 * cv2.countNonZero(mask) / mask.size

        if fg_pct > self.cfg.scene_change_pct:
            # Різка зміна освітлення, завада чи зсув камери: перенавчаємо фон,
            # інакше кілька секунд увесь кадр буде «рухомим об'єктом».
            self.reset()
            return MotionResult([], mask, fg_pct, True, False)

        min_area = self.cfg.min_area_pct / 100.0 * mask.size
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = [
            cv2.boundingRect(c) for c in contours if cv2.contourArea(c) >= min_area
        ]
        return MotionResult(boxes, mask, fg_pct, False, False)
