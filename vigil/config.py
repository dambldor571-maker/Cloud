"""Конфігурація системи. Усі параметри мають розумні значення за замовчуванням,
YAML-файл перевизначає лише те, що в ньому вказано."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml


# Параметри аналогових стандартів: (ширина, висота, кадрів/с).
STANDARDS = {
    "pal": (720, 576, 25.0),
    "ntsc": (720, 480, 29.97),
}


@dataclass
class SourceConfig:
    # Індекс пристрою (0 -> /dev/video0), шлях до /dev/videoN, файл або URL.
    uri: str = "0"
    # pal або ntsc — має збігатися з камерою і монітором.
    standard: str = "pal"
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
    # Зони, де рух ігнорується (дерева, трава, дорога за периметром):
    # список багатокутників у частках кадру, напр. [[[0, 0], [0.3, 0], [0.3, 0.2]]].
    ignore_zones: list = field(default_factory=list)
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
class DisplayConfig:
    # fb — кадровий буфер Linux (композитний вихід Pi без робочого столу),
    # window — вікно на ПК для розробки, file — запис у відеофайл, none — без виводу.
    backend: str = "fb"
    device: str = "/dev/fb0"
    file_path: str = "output/display.avi"
    box_color: list = field(default_factory=lambda: [0, 0, 255])  # BGR
    box_thickness: int = 2
    show_clock: bool = True
    show_count: bool = True
    show_status: bool = True  # NO SIGNAL / REBUILDING BG / прогрів
    # Масштаб шрифту написів (композитний монітор має низьку чіткість).
    font_scale: float = 0.7


@dataclass
class BuzzerConfig:
    enabled: bool = True
    gpio: int = 17
    # on_new — короткий сигнал на кожен новий об'єкт;
    # continuous — переривчастий сигнал, поки в кадрі є хоч один об'єкт.
    mode: str = "on_new"
    beep_seconds: float = 0.15
    # Мінімальна пауза між сигналами в режимі on_new, с.
    cooldown: float = 2.0


@dataclass
class RelayConfig:
    enabled: bool = True
    gpio: int = 27
    # level — постійний рівень, поки програма працює;
    # pulse — меандр на вхід зовнішнього апаратного сторожа (надійніше: при
    # зависанні ОС імпульси зникають, і реле відпускається, навіть якщо GPIO «завис» у 1).
    mode: str = "level"
    active_high: bool = True
    pulse_hz: float = 10.0
    # Якщо цикл виводу не оновлював кадр довше — повертаємо пряму картинку.
    stall_timeout: float = 1.0


@dataclass
class EventsConfig:
    enabled: bool = False
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
    display: DisplayConfig = field(default_factory=DisplayConfig)
    buzzer: BuzzerConfig = field(default_factory=BuzzerConfig)
    relay: RelayConfig = field(default_factory=RelayConfig)
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
            elif isinstance(current, str):
                value = str(value).lower() if key in ("standard", "backend", "mode") else str(value)
            elif isinstance(current, bool):
                if not isinstance(value, bool):
                    raise ValueError(f"{path}{key} має бути true/false")
            elif isinstance(current, (int, float)):
                value = type(current)(value)
            setattr(obj, key, value)


_CHOICES = {
    ("source", "standard"): STANDARDS.keys(),
    ("display", "backend"): ("fb", "window", "file", "none"),
    ("buzzer", "mode"): ("on_new", "continuous"),
    ("relay", "mode"): ("level", "pulse"),
}


def validate(config: Config) -> None:
    for (section, key), allowed in _CHOICES.items():
        value = getattr(getattr(config, section), key)
        if value not in allowed:
            raise ValueError(f"{section}.{key}={value!r}, допустимо: {', '.join(allowed)}")


def load_config(path: str | Path | None = None) -> Config:
    config = Config()
    if path is not None:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _merge(config, data)
    validate(config)
    return config
