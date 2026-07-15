from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from door_guardian.config import get_settings  # noqa: E402
from door_guardian.cli import main  # noqa: E402


class SettingsTests(unittest.TestCase):
    def test_defaults_create_runtime_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                settings = get_settings(Path(directory))
            self.assertTrue(settings.demo_mode)
            self.assertTrue(settings.faces_dir.is_dir())
            self.assertTrue(settings.model_dir.is_dir())

    def test_environment_overrides_camera_and_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            values = {
                "DOOR_DEMO_MODE": "false",
                "DOOR_CAMERA_INDEX": "2",
                "WEATHER_LATITUDE": "30.0",
            }
            with patch.dict(os.environ, values, clear=True):
                settings = get_settings(Path(directory))
            self.assertFalse(settings.demo_mode)
            self.assertEqual(settings.camera_index, 2)
            self.assertEqual(settings.weather_latitude, 30.0)

    def test_cli_reports_invalid_configuration_without_traceback(self) -> None:
        values = {"DOOR_CAMERA_INDEX": "not-a-number"}
        with patch.dict(os.environ, values, clear=True), patch(
            "door_guardian.cli.get_settings",
            side_effect=ValueError("invalid camera index"),
        ):
            output = StringIO()
            with redirect_stderr(output):
                exit_code = main(["diagnose"])
        self.assertEqual(exit_code, 1)
        self.assertIn("invalid camera index", output.getvalue())


if __name__ == "__main__":
    unittest.main()
