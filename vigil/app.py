"""Застосунок: захоплення -> детекція -> рамки й написи -> монітор, зумер, реле.

Режими роботи:
- потоковий (камера, потік, файл у реальному темпі): захоплення, детекція і
  виведення — окремі потоки, тож повільна детекція не гальмує відео на моніторі;
- послідовний (файл без realtime): кожен кадр проходить усі етапи по черзі —
  детерміновано, для налаштування й тестів."""

from __future__ import annotations

import logging
import signal
import threading
import time
from dataclasses import dataclass

from . import overlay
from .config import Config
from .display import Display, create_display
from .gpio import BypassRelay, Buzzer, make_pin
from .pipeline import DetectionState, Detector
from .source import FrameGrabber, VideoSource

log = logging.getLogger(__name__)


@dataclass
class RunStats:
    displayed: int = 0
    detected: int = 0
    detector_fps: float = 0.0
    wall_time: float = 0.0

    @property
    def display_fps(self) -> float:
        return self.displayed / self.wall_time if self.wall_time else 0.0


class App:
    def __init__(self, cfg: Config, display: Display | None = None,
                 virtual_gpio: bool = False):
        self.cfg = cfg
        self.source = VideoSource(cfg.source)
        self.detector = Detector(cfg)
        self.display = display if display is not None else create_display(
            cfg.display, self.source.fps)
        self.buzzer = Buzzer(cfg.buzzer, make_pin(cfg.buzzer.gpio, "buzzer",
                                                  virtual=virtual_gpio or not cfg.buzzer.enabled))
        self.relay = None
        if cfg.relay.enabled:
            self.relay = BypassRelay(cfg.relay, make_pin(
                cfg.relay.gpio, "relay", cfg.relay.active_high, virtual=virtual_gpio))
        self.stats = RunStats()
        self._stop = threading.Event()
        self._state: DetectionState | None = None
        self._state_lock = threading.Lock()

    @property
    def threaded(self) -> bool:
        return not self.source.is_file or self.cfg.source.realtime

    def stop(self) -> None:
        self._stop.set()

    def run(self, max_frames: int | None = None) -> RunStats:
        start = time.monotonic()
        try:
            if self.threaded:
                self._run_threaded(max_frames)
            else:
                self._run_sequential(max_frames)
        finally:
            self.stats.wall_time = time.monotonic() - start
            self.stats.detected = self.detector.frames
            self.stats.detector_fps = self.detector.fps
            self.close()
        return self.stats

    def _show(self, image, state: DetectionState | None) -> None:
        frame = overlay.draw(image, state, self.cfg.display)
        self.display.show(frame)
        self.stats.displayed += 1
        if self.relay is not None:
            self.relay.feed()

    def _on_detection(self, state: DetectionState, now: float) -> None:
        self.buzzer.update(len(state.new_ids), len(state.objects), now)

    def _run_sequential(self, max_frames: int | None) -> None:
        for frame in self.source.frames():
            state = self.detector.process(frame)
            self._on_detection(state, frame.timestamp)
            self._show(frame.image.copy(), state)
            if self._stop.is_set() or (max_frames and self.stats.displayed >= max_frames):
                break

    def _detect_loop(self, grabber: FrameGrabber) -> None:
        last = -1
        while not self._stop.is_set():
            frame = grabber.wait_newer(last, timeout=0.5)
            if frame is None:
                if grabber.finished:
                    return
                continue
            last = frame.index
            state = self.detector.process(frame)
            with self._state_lock:
                self._state = state
            self._on_detection(state, time.monotonic())

    def _run_threaded(self, max_frames: int | None) -> None:
        grabber = FrameGrabber(self.source)
        detector = threading.Thread(target=self._detect_loop, args=(grabber,),
                                    name="detector", daemon=True)
        grabber.start()
        detector.start()
        last = -1
        try:
            while not self._stop.is_set():
                frame = grabber.wait_newer(last, timeout=0.5)
                if frame is None:
                    if grabber.finished:
                        break
                    continue  # кадрів немає — реле саме відпуститься за stall_timeout
                last = frame.index
                with self._state_lock:
                    state = self._state
                self._show(frame.image.copy(), state)
                if max_frames and self.stats.displayed >= max_frames:
                    break
        finally:
            self._stop.set()
            grabber.stop()
            detector.join(timeout=2.0)
            grabber.join(timeout=2.0)
        if grabber.error is not None:
            raise grabber.error

    def close(self) -> None:
        if self.relay is not None:
            self.relay.close()
        self.buzzer.close()
        self.detector.close()
        self.display.close()


def install_signal_handlers(app: App) -> None:
    """systemd зупиняє сервіс через SIGTERM — завершуємось акуратно (реле відпускається)."""
    def handler(signum, _frame):
        log.info("Отримано сигнал %d, зупинка", signum)
        app.stop()
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
