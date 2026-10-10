"""Журнал подій: JSONL-файл + знімки кадрів."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import EventsConfig
from .tracker import Track


@dataclass
class Event:
    type: str  # object_start | object_end | signal_lost | signal_restored | scene_change
    ts: float
    wall_time: float = field(default_factory=time.time)
    track_id: int | None = None
    box: list[int] | None = None
    duration: float | None = None
    snapshot: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class EventLog:
    def __init__(self, cfg: EventsConfig):
        self.cfg = cfg
        self.dir = Path(cfg.output_dir)
        self.snap_dir = self.dir / "snapshots"
        self.snap_dir.mkdir(parents=True, exist_ok=True)
        self._file = open(self.dir / "events.jsonl", "a", encoding="utf-8")
        self.events: list[Event] = []

    def emit(self, event: Event) -> None:
        self.events.append(event)
        self._file.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        self._file.flush()

    def object_started(self, track: Track, ts: float, image: np.ndarray,
                       box: list[int]) -> None:
        snapshot = None
        if self.cfg.save_snapshots:
            annotated = image.copy()
            x, y, w, h = box
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)
            name = f"{int(time.time() * 1000)}_track{track.id}.jpg"
            cv2.imwrite(str(self.snap_dir / name), annotated)
            snapshot = f"snapshots/{name}"
        self.emit(Event("object_start", ts, track_id=track.id, box=box, snapshot=snapshot))

    def object_ended(self, track: Track) -> None:
        duration = track.last_seen - track.first_seen
        if duration < self.cfg.min_duration:
            return
        self.emit(Event("object_end", track.last_seen, track_id=track.id,
                        duration=round(duration, 3),
                        extra={"path_len": len(track.path)}))

    def close(self) -> None:
        self._file.close()
