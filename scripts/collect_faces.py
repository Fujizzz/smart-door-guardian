"""Convenience wrapper for face collection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from door_guardian.config import get_settings  # noqa: E402
from door_guardian.face import FaceService  # noqa: E402


parser = argparse.ArgumentParser()
parser.add_argument("name")
parser.add_argument("--samples", type=int, default=80)
args = parser.parse_args()

count = FaceService(get_settings()).collect(args.name, args.samples)
print(f"Collected {count} samples.")

