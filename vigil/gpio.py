"""Зумер і реле обходу на GPIO Raspberry Pi.

На Pi використовується gpiozero (входить у Raspberry Pi OS). Без нього
(ПК, тести) — віртуальні піни, які лише запам'ятовують стан."""

from __future__ import annotations

import logging
import threading
import time
from typing import Protocol

from .config import BuzzerConfig, RelayConfig

log = logging.getLogger(__name__)


class OutputPin(Protocol):
    def on(self) -> None: ...
    def off(self) -> None: ...
    def close(self) -> None: ...


class VirtualPin:
    def __init__(self, name: str):
        self.name = name
        self.state = False
        self.rising_edges = 0

    def on(self) -> None:
        if not self.state:
            self.rising_edges += 1
        self.state = True

    def off(self) -> None:
        self.state = False

    def close(self) -> None:
        self.state = False


def make_pin(gpio: int, name: str, active_high: bool = True,
             virtual: bool = False) -> OutputPin:
    if not virtual:
        try:
            from gpiozero import OutputDevice  # type: ignore[import-not-found]
            return OutputDevice(gpio, active_high=active_high, initial_value=False)
        except Exception as e:  # noqa: BLE001 — немає бібліотеки або не Pi
            log.warning("GPIO%d (%s) недоступний (%s) — використовую віртуальний пін",
                        gpio, name, e)
    return VirtualPin(name)


class Buzzer:
    """Неблокуючий зумер: beep() повертається одразу."""

    def __init__(self, cfg: BuzzerConfig, pin: OutputPin):
        self.cfg = cfg
        self.pin = pin
        self._last_beep = float("-inf")
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self.beeps = 0

    def beep(self) -> None:
        with self._lock:
            self.beeps += 1
            self.pin.on()
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.cfg.beep_seconds, self.pin.off)
            self._timer.daemon = True
            self._timer.start()

    def update(self, new_objects: int, present: int, now: float) -> None:
        """Викликається на кожен результат детекції."""
        if not self.cfg.enabled:
            return
        if self.cfg.mode == "on_new":
            trigger = new_objects > 0
        else:  # continuous: сигнал кожні cooldown секунд, поки є об'єкти
            trigger = present > 0
        if trigger and now - self._last_beep >= self.cfg.cooldown:
            self._last_beep = now
            self.beep()

    def close(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self.pin.off()
            self.pin.close()


class BypassRelay:
    """Реле обходу: у знеструмленому стані камера з'єднана з монітором напряму.

    Програма вмикає реле (картинка через Pi), лише поки виведення живе:
    feed() викликається на кожен показаний кадр. Якщо кадри перестали
    надходити довше за stall_timeout — реле відпускається."""

    def __init__(self, cfg: RelayConfig, pin: OutputPin):
        self.cfg = cfg
        self.pin = pin
        self._last_feed = float("-inf")
        self._stop = threading.Event()
        self.engaged = False
        self._thread = threading.Thread(target=self._run, name="relay", daemon=True)
        self._thread.start()

    def feed(self) -> None:
        self._last_feed = time.monotonic()

    def _set_engaged(self, value: bool) -> None:
        if value != self.engaged:
            self.engaged = value
            log.info("Реле: %s", "відео через Pi" if value else "пряма картинка з камери")
        if not value:
            self.pin.off()

    def _run(self) -> None:
        period = 1.0 / (2 * self.cfg.pulse_hz)
        level = False
        while not self._stop.is_set():
            alive = time.monotonic() - self._last_feed <= self.cfg.stall_timeout
            self._set_engaged(alive)
            if alive:
                if self.cfg.mode == "pulse":
                    level = not level
                    self.pin.on() if level else self.pin.off()
                else:
                    self.pin.on()
            self._stop.wait(period if self.cfg.mode == "pulse" else 0.05)

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._set_engaged(False)
        self.pin.close()
