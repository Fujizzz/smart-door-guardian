from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from door_guardian.config import get_settings  # noqa: E402
from door_guardian.face import FaceService, FaceServiceError  # noqa: E402
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

    def test_training_skips_empty_user_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                settings = get_settings(Path(directory))
            (settings.faces_dir / "alice").mkdir()
            (settings.faces_dir / "alice" / "0001.jpg").write_bytes(b"sample")
            (settings.faces_dir / "empty-user").mkdir()

            image = SimpleNamespace(size=1)
            recognizer = MagicMock()
            fake_cv2 = MagicMock()
            fake_cv2.IMREAD_GRAYSCALE = 0
            fake_cv2.imread.return_value = image
            fake_cv2.face.LBPHFaceRecognizer_create.return_value = recognizer
            fake_numpy = SimpleNamespace(int32="int32", asarray=lambda values, dtype: values)

            with patch("door_guardian.face._load_cv2", return_value=fake_cv2), patch.dict(
                sys.modules, {"numpy": fake_numpy}
            ):
                users, samples = FaceService(settings).train()

            self.assertEqual((users, samples), (1, 1))
            self.assertEqual(
                json.loads(settings.labels_path.read_text(encoding="utf-8")),
                {"0": "alice"},
            )
            recognizer.train.assert_called_once()

    def test_training_rejects_only_empty_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                settings = get_settings(Path(directory))
            (settings.faces_dir / "empty-user").mkdir()
            fake_cv2 = MagicMock()
            fake_cv2.IMREAD_GRAYSCALE = 0
            with patch("door_guardian.face._load_cv2", return_value=fake_cv2), patch.dict(
                sys.modules,
                {"numpy": SimpleNamespace(int32="int32", asarray=lambda values, dtype: values)},
            ):
                with self.assertRaises(FaceServiceError):
                    FaceService(settings).train()


if __name__ == "__main__":
    unittest.main()
