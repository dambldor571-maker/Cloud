"""Головний конвеєр: кадр -> попередня обробка -> рух -> трекінг -> події."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import cv2
import numpy as np

from .config import Config
from .events import Event, EventLog
from .motion import Box, MotionDetector
from .preprocess import Preprocessor, signal_present
from .source import Frame, VideoSource
from .tracker import Track, Tracker

log = logging.getLogger(__name__)


@dataclass
class Stats:
    frames: int = 0
    processing_time: float = 0.0

    @property
    def fps(self) -> float:
        return self.frames / self.processing_time if self.processing_time else 0.0


class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.pre = Preprocessor(cfg.preprocess)
        self.motion = MotionDetector(cfg.motion)
        self.tracker = Tracker(cfg.tracker)
        self.events = EventLog(cfg.events)
        self.stats = Stats()
        self._no_signal = 0
        self._signal_lost = False

    def _to_frame_box(self, box: Box, frame_shape: tuple[int, ...]) -> list[int]:
        """Координати з кадру аналізу -> координати вихідного кадру."""
        x, y, w, h = box
        sx = self.pre.scale
        # Вертикальний масштаб окремо: деінтерлейс зменшує висоту вдвічі.
        sy = frame_shape[0] / self._analysis_h
        return [round(x * sx), round(y * sy), round(w * sx), round(h * sy)]

    def process(self, frame: Frame) -> list[Track]:
        """Обробляє один кадр, повертає поточні підтверджені треки."""
        t0 = time.perf_counter()
        gray = self.pre(frame.image)
        self._analysis_h = gray.shape[0]

        if not signal_present(gray, self.cfg.signal.min_stddev):
            self._no_signal += 1
            if self._no_signal >= self.cfg.signal.lost_frames and not self._signal_lost:
                self._signal_lost = True
                self._end_all(frame.timestamp)
                self.events.emit(Event("signal_lost", frame.timestamp))
                log.warning("Втрачено відеосигнал")
            self._account(t0)
            return []
        self._no_signal = 0
        if self._signal_lost:
            self._signal_lost = False
            self.motion.reset()
            self.events.emit(Event("signal_restored", frame.timestamp))
            log.info("Відеосигнал відновлено")

        result = self.motion(gray)
        if result.scene_change:
            self._end_all(frame.timestamp)
            self.events.emit(Event("scene_change", frame.timestamp,
                                   extra={"foreground_pct": round(result.foreground_pct, 1)}))
            self._account(t0)
            return []

        h, w = gray.shape[:2]
        started, ended = self.tracker.update(result.boxes, frame.timestamp, (w, h))
        for track in started:
            box = self._to_frame_box(track.box, frame.image.shape)
            self.events.object_started(track, frame.timestamp, frame.image, box)
            log.info("Об'єкт #%d з'явився", track.id)
        for track in ended:
            self.events.object_ended(track)
            log.info("Об'єкт #%d зник", track.id)

        self._account(t0)
        return [t for t in self.tracker.tracks if t.confirmed and t.missed == 0]

    def _end_all(self, ts: float) -> None:
        for track in self.tracker.reset():
            self.events.object_ended(track)

    def _account(self, t0: float) -> None:
        self.stats.frames += 1
        self.stats.processing_time += time.perf_counter() - t0

    def annotate(self, image: np.ndarray, tracks: list[Track]) -> np.ndarray:
        out = image.copy()
        for track in tracks:
            x, y, w, h = self._to_frame_box(track.box, image.shape)
            cv2.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(out, f"#{track.id}", (x, max(12, y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        if self._signal_lost:
            cv2.putText(out, "NO SIGNAL", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0, 0, 255), 2, cv2.LINE_AA)
        return out

    def run(self, source: VideoSource, writer: cv2.VideoWriter | None = None,
            max_frames: int | None = None) -> Stats:
        try:
            for frame in source.frames():
                tracks = self.process(frame)
                if writer is not None:
                    writer.write(self.annotate(frame.image, tracks))
                if max_frames is not None and self.stats.frames >= max_frames:
                    break
        finally:
            source.release()
            self._end_all(0.0)
            self.events.close()
        return self.stats
