#!/usr/bin/env python3
"""Convenience entry point using this project's installed Python environment."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
python = root / '.tools/arduino/python/bin/python'
if not python.is_file():
    raise SystemExit('First run: python3 scripts/robot.py setup')
os.execv(str(python), [str(python), str(root / 'scripts/arm.py'), *sys.argv[1:]])
