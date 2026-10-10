"""Детектор: кадр -> попередня обробка -> рух -> трекінг -> стан для виводу."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from .config import Config
from .events import Event, EventLog
from .motion import Box, MotionDetector
from .preprocess import Preprocessor, signal_present
from .source import Frame
from .tracker import Track, Tracker

log = logging.getLogger(__name__)

# Статуси, що показуються на екрані.
STATUS_OK = "ok"
STATUS_WARMUP = "warmup"  # фон ще навчається
STATUS_NO_SIGNAL = "no_signal"
STATUS_SCENE_CHANGE = "scene_change"  # фон скинуто після різкої зміни


@dataclass
class Detection:
    track_id: int
    box: tuple[int, int, int, int]  # у координатах вихідного кадру


@dataclass
class DetectionState:
    frame_index: int
    status: str
    objects: list[Detection] = field(default_factory=list)
    new_ids: list[int] = field(default_factory=list)


class Detector:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.pre = Preprocessor(cfg.preprocess)
        self.motion = MotionDetector(cfg.motion)
        self.tracker = Tracker(cfg.tracker)
        self.events = EventLog(cfg.events) if cfg.events.enabled else None
        self.frames = 0
        self.busy_time = 0.0
        self._no_signal = 0
        self._signal_lost = False
        self._scene_change_until = -1.0

    @property
    def fps(self) -> float:
        return self.frames / self.busy_time if self.busy_time else 0.0

    def _emit(self, event: Event) -> None:
        if self.events is not None:
            self.events.emit(event)

    def _scale_box(self, box: Box, frame_shape: tuple[int, ...],
                   analysis_shape: tuple[int, ...]) -> tuple[int, int, int, int]:
        x, y, w, h = box
        sx = frame_shape[1] / analysis_shape[1]
        sy = frame_shape[0] / analysis_shape[0]  # деінтерлейс змінює лише висоту
        return round(x * sx), round(y * sy), round(w * sx), round(h * sy)

    def process(self, frame: Frame) -> DetectionState:
        t0 = time.perf_counter()
        try:
            return self._process(frame)
        finally:
            self.frames += 1
            self.busy_time += time.perf_counter() - t0

    def _process(self, frame: Frame) -> DetectionState:
        gray = self.pre(frame.image)

        if not signal_present(gray, self.cfg.signal.min_stddev):
            self._no_signal += 1
            if self._no_signal >= self.cfg.signal.lost_frames and not self._signal_lost:
                self._signal_lost = True
                self._end_all()
                self._emit(Event("signal_lost", frame.timestamp))
                log.warning("Втрачено відеосигнал")
            status = STATUS_NO_SIGNAL if self._signal_lost else STATUS_OK
            return DetectionState(frame.index, status)
        self._no_signal = 0
        if self._signal_lost:
            self._signal_lost = False
            self.motion.reset()
            self._emit(Event("signal_restored", frame.timestamp))
            log.info("Відеосигнал відновлено")

        result = self.motion(gray)
        if result.scene_change:
            self._end_all()
            self._emit(Event("scene_change", frame.timestamp,
                             extra={"foreground_pct": round(result.foreground_pct, 1)}))
            log.info("Різка зміна сцени (%.0f%% кадру), фон скинуто", result.foreground_pct)
            return DetectionState(frame.index, STATUS_SCENE_CHANGE)
        if result.warming_up:
            return DetectionState(frame.index, STATUS_WARMUP)

        h, w = gray.shape[:2]
        started, ended = self.tracker.update(result.boxes, frame.timestamp, (w, h))
        for track in ended:
            if self.events is not None:
                self.events.object_ended(track)
            log.info("Об'єкт #%d зник", track.id)

        objects = [
            Detection(t.id, self._scale_box(t.box, frame.image.shape, gray.shape))
            for t in self.tracker.tracks if t.confirmed and t.missed == 0
        ]
        for track in started:
            log.info("Об'єкт #%d з'явився", track.id)
            if self.events is not None:
                box = self._scale_box(track.box, frame.image.shape, gray.shape)
                self.events.object_started(track, frame.timestamp, frame.image, list(box))
        return DetectionState(frame.index, STATUS_OK, objects, [t.id for t in started])

    def _end_all(self) -> None:
        ended: list[Track] = self.tracker.reset()
        if self.events is not None:
            for track in ended:
                self.events.object_ended(track)

    def close(self) -> None:
        self._end_all()
        if self.events is not None:
            self.events.close()
