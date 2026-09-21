#!/usr/bin/env python3
"""Thin wrapper that runs the pilot smoke stage from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tk_pilot.run import main


if __name__ == "__main__":
    argv = list(sys.argv[1:])
    if "--stage" not in argv:
        argv = ["--stage", "smoke", *argv]
    raise SystemExit(main(argv))
