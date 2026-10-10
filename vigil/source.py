"""Джерело відео: V4L2-пристрій (декодер ADV7280-M / USB-грабер), файл або потік."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Iterator

import cv2
import numpy as np

from .config import STANDARDS, SourceConfig

log = logging.getLogger(__name__)


@dataclass
class Frame:
    image: np.ndarray  # BGR
    index: int
    timestamp: float  # секунди: час кадру у файлі або монотонний час для пристрою


def _is_device(uri: str) -> bool:
    return uri.isdigit() or uri.startswith("/dev/video")


class VideoSource:
    def __init__(self, cfg: SourceConfig):
        self.cfg = cfg
        self.width, self.height, self.fps = STANDARDS[cfg.standard]
        self.is_device = _is_device(cfg.uri)
        self.is_stream = "://" in cfg.uri
        self._cap: cv2.VideoCapture | None = None

    @property
    def is_file(self) -> bool:
        return not self.is_device and not self.is_stream

    def _open(self) -> bool:
        uri = self.cfg.uri
        if self.is_device:
            target: int | str = int(uri) if uri.isdigit() else uri
            cap = cv2.VideoCapture(target, cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            # Мінімальний буфер: обробляємо найсвіжіший кадр, а не чергу.
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            cap = cv2.VideoCapture(uri)
        if not cap.isOpened():
            cap.release()
            return False
        if self.is_file:
            self.fps = cap.get(cv2.CAP_PROP_FPS) or self.fps
        self._cap = cap
        return True

    def frames(self) -> Iterator[Frame]:
        """Генерує кадри. Для пристроїв і потоків перепідключається після втрати,
        для файлу — завершується в кінці."""
        index = 0
        start = time.monotonic()
        while True:
            if self._cap is None and not self._open():
                if self.is_file:
                    raise FileNotFoundError(f"Не вдалося відкрити джерело: {self.cfg.uri}")
                log.warning("Джерело %s недоступне, повтор через %.1f с",
                            self.cfg.uri, self.cfg.reconnect_delay)
                time.sleep(self.cfg.reconnect_delay)
                continue

            assert self._cap is not None
            ok, image = self._cap.read()
            if not ok or image is None:
                self.release()
                if self.is_file:
                    return  # кінець файлу
                log.warning("Втрачено кадри з %s, перепідключення", self.cfg.uri)
                time.sleep(self.cfg.reconnect_delay)
                continue

            if self.is_file:
                ts = index / self.fps
                if self.cfg.realtime:
                    delay = start + ts - time.monotonic()
                    if delay > 0:
                        time.sleep(delay)
            else:
                ts = time.monotonic() - start
            yield Frame(image=image, index=index, timestamp=ts)
            index += 1

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class FrameGrabber(threading.Thread):
    """Читає джерело у фоновому потоці й тримає лише останній кадр.

    Споживачі (вивід і детектор) чекають на новий кадр через wait_newer(),
    тому повільний детектор не гальмує виведення відео."""

    def __init__(self, source: VideoSource):
        super().__init__(name="grabber", daemon=True)
        self.source = source
        self._cond = threading.Condition()
        self._frame: Frame | None = None
        self._stop = threading.Event()
        self.finished = False
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            for frame in self.source.frames():
                with self._cond:
                    self._frame = frame
                    self._cond.notify_all()
                if self._stop.is_set():
                    break
        except BaseException as e:  # noqa: BLE001 — передаємо в головний потік
            self.error = e
        finally:
            self.source.release()
            with self._cond:
                self.finished = True
                self._cond.notify_all()

    def wait_newer(self, last_index: int, timeout: float) -> Frame | None:
        """Повертає кадр з індексом більшим за last_index або None (таймаут/кінець)."""
        with self._cond:
            self._cond.wait_for(
                lambda: self.finished
                or (self._frame is not None and self._frame.index > last_index),
                timeout=timeout,
            )
            if self._frame is not None and self._frame.index > last_index:
                return self._frame
            return None

    def stop(self) -> None:
        self._stop.set()
