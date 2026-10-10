import numpy as np

from synth import H, W, Mover, frames
from vigil.config import Config
from vigil.pipeline import (STATUS_NO_SIGNAL, STATUS_OK, STATUS_SCENE_CHANGE,
                            STATUS_WARMUP, Detector)
from vigil.source import Frame
from vigil.tracker import iou


def run(detector, gen):
    states = []
    for i, (img, truth) in enumerate(gen):
        states.append((detector.process(Frame(img, i, i / 25)), truth))
    return states


def test_static_noisy_scene_has_no_detections():
    states = run(Detector(Config()), frames(150, []))
    assert states[0][0].status == STATUS_WARMUP
    assert all(not s.objects for s, _ in states)
    assert all(s.status == STATUS_OK for s, _ in states[40:])


def test_moving_object_is_detected_and_tracked():
    mover = Mover(start=60, end=160, x0=50, y0=250, vx=5, vy=0)
    states = run(Detector(Config()), frames(180, [mover]))

    new_ids = [i for s, _ in states for i in s.new_ids]
    assert len(new_ids) == 1, "один об'єкт — одна поява, без дроблення треку"

    hits = 0
    for s, truth in states[70:160]:
        if s.objects:
            assert len(s.objects) == 1
            assert iou(s.objects[0].box, truth[0]) > 0.4
            hits += 1
    assert hits >= 80


def test_object_disappears_after_leaving():
    mover = Mover(start=40, end=90, x0=100, y0=100, vx=4, vy=2)
    states = run(Detector(Config()), frames(140, [mover]))
    assert any(s.objects for s, _ in states[60:90])
    assert all(not s.objects for s, _ in states[110:])


def test_ignore_zone_suppresses_motion():
    cfg = Config()
    cfg.motion.ignore_zones = [[[0, 0], [1, 0], [1, 0.5], [0, 0.5]]]  # верхня половина
    mover = Mover(start=40, end=140, x0=50, y0=60, vx=5, vy=0)
    states = run(Detector(cfg), frames(150, [mover]))
    assert all(not s.objects for s, _ in states)


def test_no_signal_detected_on_flat_frame():
    cfg = Config()
    det = Detector(cfg)
    blue = np.zeros((H, W, 3), np.uint8)
    blue[:] = (200, 0, 0)
    statuses = [det.process(Frame(blue, i, i / 25)).status for i in range(20)]
    assert statuses[cfg.signal.lost_frames - 2] == STATUS_OK
    assert statuses[-1] == STATUS_NO_SIGNAL


def test_brightness_jump_resets_background():
    gen = frames(120, [], brightness={60: 70})
    states = run(Detector(Config()), gen)
    assert any(s.status == STATUS_SCENE_CHANGE for s, _ in states[60:63])
    assert all(not s.objects for s, _ in states)


def test_field_source_is_handled():
    """Декодер може віддавати поля 720x288 — детекція має працювати так само."""
    mover = Mover(start=60, end=160, x0=50, y0=250, vx=5, vy=0)
    det = Detector(Config())
    found = 0
    for i, (img, truth) in enumerate(frames(160, [mover])):
        field = img[::2]
        state = det.process(Frame(field, i, i / 25))
        if i >= 70 and state.objects:
            x, y, w, h = truth[0]
            assert iou(state.objects[0].box, (x, y // 2, w, h // 2)) > 0.4
            found += 1
    assert found >= 70
