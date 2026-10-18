"""Точка входу: python -m explorer [шлях] [--theme retro|modern]."""
from __future__ import annotations

import argparse
import sys

from .app import ExplorerApp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="explorer", description="Mini File Explorer — клавіатурний TUI-провідник")
    parser.add_argument("path", nargs="?", default=".", help="стартова папка (за замовчуванням — поточна)")
    parser.add_argument("--theme", choices=("retro", "modern"), default="retro", help="кольорова тема")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ExplorerApp(args.path, theme=args.theme).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
