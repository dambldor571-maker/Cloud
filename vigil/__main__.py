"""Запуск: python -m vigil [-c config.yaml] [--source ...] [--display ...]"""

from __future__ import annotations

import argparse
import logging
import sys

from .app import App, install_signal_handlers
from .config import load_config, validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vigil", description=__doc__)
    parser.add_argument("-c", "--config", help="YAML-файл конфігурації")
    parser.add_argument("--source", help="перевизначити source.uri (0, /dev/video0, файл)")
    parser.add_argument("--standard", choices=["pal", "ntsc"], help="перевизначити source.standard")
    parser.add_argument("--display", choices=["fb", "window", "file", "none"],
                        help="перевизначити display.backend")
    parser.add_argument("--out", help="файл для --display file")
    parser.add_argument("--realtime", action="store_true",
                        help="відтворювати файл у реальному темпі (потоковий режим)")
    parser.add_argument("--virtual-gpio", action="store_true",
                        help="не чіпати GPIO (робота на ПК)")
    parser.add_argument("--max-frames", type=int, help="зупинитись після N кадрів")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = load_config(args.config)
    if args.source is not None:
        cfg.source.uri = args.source
    if args.standard:
        cfg.source.standard = args.standard
    if args.display:
        cfg.display.backend = args.display
    if args.out:
        cfg.display.file_path = args.out
    if args.realtime:
        cfg.source.realtime = True
    validate(cfg)

    app = App(cfg, virtual_gpio=args.virtual_gpio)
    install_signal_handlers(app)
    stats = app.run(max_frames=args.max_frames)
    logging.info(
        "Показано кадрів: %d (%.1f/с), оброблено детектором: %d (до %.0f/с)",
        stats.displayed, stats.display_fps, stats.detected, stats.detector_fps,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
