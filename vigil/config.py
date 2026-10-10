"""Конфігурація системи. Усі параметри мають розумні значення за замовчуванням,
YAML-файл перевизначає лише те, що в ньому вказано."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SourceConfig:
    # Індекс пристрою (0 -> /dev/video0), шлях до /dev/videoN, файл або URL.
    uri: str = "0"
    width: int = 720
    height: int = 576
    fps: float = 25.0
    # Пауза між спробами перепідключення, с.
    reconnect_delay: float = 2.0
    # Для файлів: відтворювати в реальному темпі (False — так швидко, як можна).
    realtime: bool = False


@dataclass
class PreprocessConfig:
    # Аналогове відео черезрядкове: беремо одне поле і масштабуємо назад,
    # щоб прибрати «гребінку» на рухомих об'єктах.
    deinterlace: bool = True
    # Ширина кадру для аналізу (менше — швидше, але гірше видно дрібні об'єкти).
    process_width: int = 480
    # Розмір ядра розмиття Гауса проти шуму аналогового сигналу (непарний, 0 — вимк.).
    blur_kernel: int = 5


@dataclass
class MotionConfig:
    history: int = 300
    var_threshold: float = 32.0
    # Скільки кадрів лише навчати фон без детекції після старту/скидання.
    warmup_frames: int = 30
    # Мінімальна площа об'єкта у відсотках від площі кадру.
    min_area_pct: float = 0.05
    # Якщо змінилось більше цієї частки кадру — це не об'єкт, а зміна сцени
    # (освітлення, завада, зсув камери). Фон скидається.
    scene_change_pct: float = 40.0
    morph_kernel: int = 3
    dilate_iterations: int = 2


@dataclass
class TrackerConfig:
    # Мінімальний IoU для зіставлення рамки з треком.
    iou_threshold: float = 0.2
    # Якщо IoU малий — зіставлення за відстанню центрів (у частках діагоналі кадру).
    max_center_dist: float = 0.08
    # Скільки кадрів поспіль об'єкт має бути видимим, щоб трек підтвердився.
    min_hits: int = 5
    # Скільки кадрів трек живе без нових спостережень.
    max_missed: int = 15


@dataclass
class SignalConfig:
    # Кадр з дуже малою дисперсією яскравості — «немає сигналу» (синій/чорний екран).
    min_stddev: float = 4.0
    # Скільки кадрів поспіль без сигналу до події signal_lost.
    lost_frames: int = 10


@dataclass
class EventsConfig:
    output_dir: str = "output"
    save_snapshots: bool = True
    # Не створювати подій для об'єктів, що зникли раніше, ніж за цей час, с.
    min_duration: float = 0.5


@dataclass
class Config:
    source: SourceConfig = field(default_factory=SourceConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    events: EventsConfig = field(default_factory=EventsConfig)


def _merge(obj: Any, data: dict[str, Any], path: str = "") -> None:
    known = {f.name: f for f in fields(obj)}
    for key, value in data.items():
        if key not in known:
            raise ValueError(f"Невідомий параметр конфігурації: {path}{key}")
        current = getattr(obj, key)
        if is_dataclass(current):
            if not isinstance(value, dict):
                raise ValueError(f"{path}{key} має бути секцією")
            _merge(current, value, f"{path}{key}.")
        else:
            if key == "uri":
                value = str(value)
            elif isinstance(current, bool):
                if not isinstance(value, bool):
                    raise ValueError(f"{path}{key} має бути true/false")
            elif isinstance(current, (int, float)):
                value = type(current)(value)
            setattr(obj, key, value)


def load_config(path: str | Path | None = None) -> Config:
    config = Config()
    if path is not None:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _merge(config, data)
    return config
