"""Виведення кадрів: кадровий буфер Linux (композитний вихід Pi), вікно, файл."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from .config import DisplayConfig

log = logging.getLogger(__name__)


class Display:
    def show(self, image: np.ndarray) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class NullDisplay(Display):
    def show(self, image: np.ndarray) -> None:
        pass


class FramebufferDisplay(Display):
    """Пише кадри напряму в /dev/fbN. Не потребує робочого столу.

    На Pi 4 з композитним виходом (див. docs/raspberry_pi_setup.md) fb0 має
    роздільність 720x576 (PAL) або 720x480 (NTSC)."""

    def __init__(self, device: str, sysfs_root: str = "/sys/class/graphics"):
        name = Path(device).name
        info = Path(sysfs_root) / name
        w, h = (int(v) for v in (info / "virtual_size").read_text().strip().split(","))
        self.bpp = int((info / "bits_per_pixel").read_text())
        stride_file = info / "stride"
        bytes_pp = self.bpp // 8
        self.stride = int(stride_file.read_text()) if stride_file.exists() else w * bytes_pp
        # virtual_size може включати подвійну буферизацію — виводимо у видиму частину.
        self.width, self.height = w, h
        if self.bpp not in (16, 24, 32):
            raise ValueError(f"Непідтримуваний формат кадрового буфера: {self.bpp} біт")
        self._mem = np.memmap(device, dtype=np.uint8, mode="r+",
                              shape=(h, self.stride))
        self._view = self._mem[:, : w * bytes_pp].reshape(h, w, bytes_pp)
        log.info("Кадровий буфер %s: %dx%d, %d біт", device, w, h, self.bpp)

    def show(self, image: np.ndarray) -> None:
        if image.shape[1] != self.width or image.shape[0] != self.height:
            image = cv2.resize(image, (self.width, self.height),
                               interpolation=cv2.INTER_LINEAR)
        if self.bpp == 16:
            pixels = cv2.cvtColor(image, cv2.COLOR_BGR2BGR565)
        elif self.bpp == 32:
            pixels = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        else:
            pixels = image
        self._view[:] = pixels.reshape(self._view.shape)

    def close(self) -> None:
        self._view[:] = 0
        self._mem.flush()


class WindowDisplay(Display):
    """Вікно на ПК для розробки. Потребує opencv-python (не headless)."""

    def __init__(self, title: str = "vigil"):
        self.title = title
        try:
            cv2.namedWindow(title, cv2.WINDOW_NORMAL)
        except cv2.error as e:
            raise RuntimeError(
                "Ця збірка OpenCV не вміє показувати вікна. "
                "Встановіть opencv-python замість opencv-python-headless") from e

    def show(self, image: np.ndarray) -> None:
        cv2.imshow(self.title, image)
        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
            raise KeyboardInterrupt

    def close(self) -> None:
        cv2.destroyWindow(self.title)


class FileDisplay(Display):
    """Записує те, що було б на моніторі, у відеофайл (для перевірки й налаштування)."""

    def __init__(self, path: str, fps: float):
        self.path = path
        self.fps = fps
        self._writer: cv2.VideoWriter | None = None

    def show(self, image: np.ndarray) -> None:
        if self._writer is None:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            h, w = image.shape[:2]
            self._writer = cv2.VideoWriter(
                self.path, cv2.VideoWriter_fourcc(*"MJPG"), self.fps, (w, h))
        self._writer.write(image)

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()


def create_display(cfg: DisplayConfig, fps: float) -> Display:
    if cfg.backend == "fb":
        return FramebufferDisplay(cfg.device)
    if cfg.backend == "window":
        return WindowDisplay()
    if cfg.backend == "file":
        return FileDisplay(cfg.file_path, fps)
    return NullDisplay()
