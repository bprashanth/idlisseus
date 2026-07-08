#!/usr/bin/env python3
"""Shim → the canonical implementation now lives in connectors/invasive.py (so Hermes can invoke it,
and it works for ANY invasive species). This wrapper is kept for convenience.

  python invasive_map.py map --species "Lantana camara"     # build (EE, in container) + render
Outputs go to /opt/data/work/invasive/<species>/ (container) or ../runs (host).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "connectors"))
from invasive import _main  # noqa: E402

if __name__ == "__main__":
    _main()
