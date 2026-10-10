"""Простий трекер: зіставляє рамки між кадрами, відсіює короткочасний шум."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .config import TrackerConfig
from .motion import Box

UNCONFIRMED_MAX_MISSED = 2


@dataclass
class Track:
    id: int
    box: Box
    first_seen: float
    last_seen: float
    hits: int = 1
    missed: int = 0
    confirmed: bool = False
    path: list[tuple[float, float]] = field(default_factory=list)

    @property
    def center(self) -> tuple[float, float]:
        x, y, w, h = self.box
        return x + w / 2, y + h / 2


def iou(a: Box, b: Box) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


class Tracker:
    def __init__(self, cfg: TrackerConfig):
        self.cfg = cfg
        self.tracks: list[Track] = []
        self._next_id = 1

    def reset(self) -> list[Track]:
        """Скидає всі треки, повертає ті, що були підтверджені (для закриття подій)."""
        ended = [t for t in self.tracks if t.confirmed]
        self.tracks = []
        return ended

    def update(self, boxes: list[Box], ts: float, frame_size: tuple[int, int]
               ) -> tuple[list[Track], list[Track]]:
        """Повертає (нові підтверджені треки, завершені підтверджені треки)."""
        diag = math.hypot(*frame_size)
        max_dist = self.cfg.max_center_dist * diag

        # Жадібне зіставлення за спаданням якості пари.
        pairs: list[tuple[float, int, int]] = []
        for ti, track in enumerate(self.tracks):
            tcx, tcy = track.center
            for bi, box in enumerate(boxes):
                score = iou(track.box, box)
                if score < self.cfg.iou_threshold:
                    bx, by, bw, bh = box
                    dist = math.hypot(bx + bw / 2 - tcx, by + bh / 2 - tcy)
                    if dist > max_dist:
                        continue
                    score = 0.5 * self.cfg.iou_threshold * (1 - dist / max_dist)
                pairs.append((score, ti, bi))
        pairs.sort(reverse=True)

        used_t: set[int] = set()
        used_b: set[int] = set()
        started: list[Track] = []
        for _, ti, bi in pairs:
            if ti in used_t or bi in used_b:
                continue
            used_t.add(ti)
            used_b.add(bi)
            track = self.tracks[ti]
            track.box = boxes[bi]
            track.last_seen = ts
            track.hits += 1
            track.missed = 0
            track.path.append(track.center)
            if not track.confirmed and track.hits >= self.cfg.min_hits:
                track.confirmed = True
                started.append(track)

        for ti, track in enumerate(self.tracks):
            if ti not in used_t:
                track.missed += 1

        for bi, box in enumerate(boxes):
            if bi not in used_b:
                track = Track(self._next_id, box, ts, ts)
                track.path.append(track.center)
                self._next_id += 1
                self.tracks.append(track)
                if self.cfg.min_hits <= 1:
                    track.confirmed = True
                    started.append(track)

        ended = [t for t in self.tracks if t.missed > self.cfg.max_missed and t.confirmed]
        # Непідтверджений трек, що зник більш ніж на пару кадрів, — шум.
        self.tracks = [
            t for t in self.tracks
            if t.missed <= (self.cfg.max_missed if t.confirmed else UNCONFIRMED_MAX_MISSED)
        ]
        return started, ended
