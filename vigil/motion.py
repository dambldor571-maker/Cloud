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
        self._zone_mask: np.ndarray | None = None
        self.reset()

    def _active_mask(self, shape: tuple[int, int]) -> np.ndarray | None:
        """Маска 255 там, де рух аналізується, 0 — у зонах ігнорування."""
        if not self.cfg.ignore_zones:
            return None
        if self._zone_mask is None or self._zone_mask.shape != shape:
            h, w = shape
            mask = np.full((h, w), 255, np.uint8)
            for zone in self.cfg.ignore_zones:
                pts = np.array([[round(x * w), round(y * h)] for x, y in zone], np.int32)
                cv2.fillPoly(mask, [pts], 0)
            self._zone_mask = mask
        return self._zone_mask

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

        active = self._active_mask(gray.shape[:2])
        if active is not None:
            mask = cv2.bitwise_and(mask, active)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
        mask = cv2.dilate(mask, self._kernel, iterations=self.cfg.dilate_iterations)
        area = mask.size if active is None else max(1, cv2.countNonZero(active))
        fg_pct = 100.0 * cv2.countNonZero(mask) / area

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
