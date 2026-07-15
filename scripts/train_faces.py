"""Convenience wrapper for LBPH model training."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from door_guardian.config import get_settings  # noqa: E402
from door_guardian.face import FaceService  # noqa: E402


users, samples = FaceService(get_settings()).train()
print(f"Trained {users} users from {samples} samples.")

