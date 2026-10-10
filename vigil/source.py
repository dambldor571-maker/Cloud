"""Джерело відео: V4L2-пристрій (аналоговий декодер / USB-грабер), файл або потік."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterator

import cv2
import numpy as np

from .config import SourceConfig

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
        self.is_device = _is_device(cfg.uri)
        self._cap: cv2.VideoCapture | None = None

    def _open(self) -> bool:
        uri = self.cfg.uri
        if self.is_device:
            target: int | str = int(uri) if uri.isdigit() else uri
            cap = cv2.VideoCapture(target, cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.height)
            cap.set(cv2.CAP_PROP_FPS, self.cfg.fps)
            # Мінімальний буфер: обробляємо найсвіжіший кадр, а не чергу.
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            cap = cv2.VideoCapture(uri)
        if not cap.isOpened():
            cap.release()
            return False
        self._cap = cap
        return True

    def frames(self) -> Iterator[Frame]:
        """Генерує кадри. Для пристроїв і потоків перепідключається після втрати,
        для файлу — завершується в кінці."""
        index = 0
        start = time.monotonic()
        while True:
            if self._cap is None and not self._open():
                if not self.is_device and "://" not in self.cfg.uri:
                    raise FileNotFoundError(f"Не вдалося відкрити джерело: {self.cfg.uri}")
                log.warning("Джерело %s недоступне, повтор через %.1f с",
                            self.cfg.uri, self.cfg.reconnect_delay)
                time.sleep(self.cfg.reconnect_delay)
                continue

            assert self._cap is not None
            ok, image = self._cap.read()
            if not ok or image is None:
                self.release()
                if not self.is_device and "://" not in self.cfg.uri:
                    return  # кінець файлу
                log.warning("Втрачено кадри з %s, перепідключення", self.cfg.uri)
                time.sleep(self.cfg.reconnect_delay)
                continue

            if self.is_device or "://" in self.cfg.uri:
                ts = time.monotonic() - start
            else:
                fps = self._cap.get(cv2.CAP_PROP_FPS) or self.cfg.fps
                ts = index / fps
                if self.cfg.realtime:
                    delay = start + ts - time.monotonic()
                    if delay > 0:
                        time.sleep(delay)
            yield Frame(image=image, index=index, timestamp=ts)
            index += 1

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
