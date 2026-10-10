import time

import cv2
import numpy as np
import pytest

from synth import H, W, Mover, write_video
from vigil.app import App
from vigil.config import BuzzerConfig, Config, RelayConfig, load_config
from vigil.display import Display, FramebufferDisplay
from vigil.gpio import BypassRelay, Buzzer, VirtualPin


class RecordingDisplay(Display):
    def __init__(self):
        self.frames = []

    def show(self, image):
        self.frames.append(image)


def make_cfg(video, **source):
    cfg = Config()
    cfg.source.uri = str(video)
    for k, v in source.items():
        setattr(cfg.source, k, v)
    return cfg


def red_pixels(img):
    b, g, r = cv2.split(img)
    return int(np.count_nonzero((r > 230) & (g < 30) & (b < 30)))


def test_sequential_run_draws_boxes_and_beeps_once(tmp_path):
    video = tmp_path / "in.avi"
    write_video(video, 160, [Mover(start=60, end=150, x0=50, y0=250, vx=5, vy=0)])
    display = RecordingDisplay()
    app = App(make_cfg(video), display=display, virtual_gpio=True)
    stats = app.run()

    assert stats.displayed == 160
    assert app.buzzer.beeps == 1
    # Рамка (червона) є лише на кадрах з об'єктом.
    assert red_pixels(display.frames[30]) == 0
    assert red_pixels(display.frames[100]) > 100
    assert app.relay.pin.rising_edges >= 1
    assert not app.relay.pin.state, "після зупинки реле відпущене"


def test_continuous_mode_beeps_repeatedly(tmp_path):
    video = tmp_path / "in.avi"
    write_video(video, 200, [Mover(start=40, end=200, x0=50, y0=250, vx=3, vy=0)])
    cfg = make_cfg(video)
    cfg.buzzer.mode = "continuous"
    cfg.buzzer.cooldown = 1.0  # 25 кадрів
    app = App(cfg, display=RecordingDisplay(), virtual_gpio=True)
    app.run()
    assert app.buzzer.beeps >= 4


def test_threaded_realtime_run(tmp_path):
    video = tmp_path / "in.avi"
    write_video(video, 75, [Mover(start=30, end=75, x0=50, y0=250, vx=5, vy=0)])
    display = RecordingDisplay()
    app = App(make_cfg(video, realtime=True), display=display, virtual_gpio=True)
    assert app.threaded
    stats = app.run()
    assert stats.displayed >= 70
    assert 2.5 < stats.wall_time < 6, "файл 3 с відтворюється в реальному темпі"


def test_relay_releases_when_frames_stall():
    pin = VirtualPin("relay")
    relay = BypassRelay(RelayConfig(stall_timeout=0.2), pin)
    try:
        time.sleep(0.1)
        assert not relay.engaged, "без кадрів — пряма картинка"
        for _ in range(5):
            relay.feed()
            time.sleep(0.05)
        assert relay.engaged and pin.state
        time.sleep(0.4)
        assert not relay.engaged and not pin.state
    finally:
        relay.close()


def test_relay_pulse_mode_toggles():
    pin = VirtualPin("relay")
    relay = BypassRelay(RelayConfig(mode="pulse", pulse_hz=50, stall_timeout=1), pin)
    try:
        relay.feed()
        time.sleep(0.2)
        assert pin.rising_edges >= 5
    finally:
        relay.close()


def test_buzzer_cooldown():
    pin = VirtualPin("buzzer")
    buzzer = Buzzer(BuzzerConfig(cooldown=2.0, beep_seconds=0.01), pin)
    buzzer.update(1, 1, now=0.0)
    buzzer.update(1, 2, now=1.0)  # в межах паузи — мовчимо
    buzzer.update(0, 2, now=5.0)  # нових немає — мовчимо
    buzzer.update(1, 3, now=5.0)
    assert buzzer.beeps == 2
    time.sleep(0.05)
    assert not pin.state, "сигнал вимикається сам"
    buzzer.close()


@pytest.mark.parametrize("bpp", [16, 32])
def test_framebuffer_display(tmp_path, bpp):
    fw, fh = 720, 576
    stride = fw * bpp // 8 + 64  # рядок може бути довшим за видиму ширину
    sysfs = tmp_path / "sys"
    (sysfs / "fb0").mkdir(parents=True)
    (sysfs / "fb0" / "virtual_size").write_text(f"{fw},{fh}\n")
    (sysfs / "fb0" / "bits_per_pixel").write_text(f"{bpp}\n")
    (sysfs / "fb0" / "stride").write_text(f"{stride}\n")
    dev = tmp_path / "fb0"
    dev.write_bytes(bytes(stride * fh))

    fb = FramebufferDisplay(str(dev), sysfs_root=str(sysfs))
    img = np.zeros((H // 2, W // 2, 3), np.uint8)  # інший розмір — масштабується
    img[:, :] = (0, 0, 255)
    fb.show(img)
    del fb

    raw = np.frombuffer(dev.read_bytes(), np.uint8).reshape(fh, stride)
    px = raw[100, : bpp // 8]
    if bpp == 16:
        assert int(px[0]) | int(px[1]) << 8 == 0xF800  # чистий червоний у RGB565
    else:
        assert list(px[:3]) == [0, 0, 255]
    assert not raw[:, fw * bpp // 8:].any(), "хвіст рядка не зачеплено"


def test_config_rejects_unknown_and_bad_values(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("motion:\n  min_aera_pct: 1\n")
    with pytest.raises(ValueError, match="min_aera_pct"):
        load_config(bad)
    bad.write_text("source:\n  standard: secam\n")
    with pytest.raises(ValueError, match="standard"):
        load_config(bad)
    ok = tmp_path / "ok.yaml"
    ok.write_text("source:\n  uri: 1\n  standard: NTSC\nbuzzer:\n  cooldown: 3\n")
    cfg = load_config(ok)
    assert cfg.source.uri == "1" and cfg.source.standard == "ntsc"
    assert cfg.buzzer.cooldown == 3.0
