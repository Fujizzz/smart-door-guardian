from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from door_guardian.config import get_settings  # noqa: E402
from door_guardian.face import FaceService  # noqa: E402
from door_guardian.notifier import EmailNotifier  # noqa: E402
from door_guardian.weather import WeatherService  # noqa: E402


class ServiceTests(unittest.TestCase):
    def test_face_service_reports_untrained_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                settings = get_settings(Path(directory))
            result = FaceService(settings).recognize()
            self.assertFalse(result.granted)
            self.assertIn("尚未训练", result.reason)

    def test_notifier_is_optional(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                settings = get_settings(Path(directory))
            notifier = EmailNotifier(settings)
            self.assertFalse(notifier.configured)
            self.assertFalse(notifier.send_intruder_alert())

    def test_weather_response_is_parsed(self) -> None:
        payload = {
            "current": {
                "temperature_2m": 26.5,
                "weather_code": 2,
                "wind_speed_10m": 8.4,
            }
        }
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                settings = get_settings(Path(directory))
            with patch("door_guardian.weather.urlopen", return_value=response):
                snapshot = WeatherService(settings).current()
        self.assertEqual(snapshot.description, "局部多云")
        self.assertIn("26.5", snapshot.sentence())


if __name__ == "__main__":
    unittest.main()

