"""OpenCV-based face collection, training, and recognition."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import Settings


class FaceServiceError(RuntimeError):
    """Raised when the camera or OpenCV face module is unavailable."""


@dataclass(frozen=True)
class RecognitionResult:
    granted: bool
    name: str | None = None
    confidence: float | None = None
    reason: str = ""


def _load_cv2():
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise FaceServiceError(
            "未安装 OpenCV。请运行 pip install -e .[vision]。"
        ) from exc
    if not hasattr(cv2, "face"):
        raise FaceServiceError(
            "当前 OpenCV 不包含 cv2.face；请安装 opencv-contrib-python。"
        )
    return cv2


def _safe_name(name: str) -> str:
    cleaned = "".join(char for char in name.strip() if char.isalnum() or char in "-_ ")
    cleaned = re.sub(r"\s+", "_", cleaned)
    if not cleaned:
        raise FaceServiceError("用户名不能为空。")
    return cleaned[:64]


class FaceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def ready(self) -> bool:
        return self.settings.model_path.exists() and self.settings.labels_path.exists()

    def _cascade(self, cv2):
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(str(cascade_path))
        if cascade.empty():
            raise FaceServiceError(f"无法加载人脸分类器：{cascade_path}")
        return cascade

    def _camera(self, cv2):
        camera = cv2.VideoCapture(self.settings.camera_index)
        if not camera.isOpened():
            camera.release()
            raise FaceServiceError(
                f"无法打开摄像头索引 {self.settings.camera_index}。"
            )
        return camera

    def collect(self, user_name: str, samples: int = 80) -> int:
        """Collect cropped grayscale face samples. Press Esc or Q to stop."""
        if samples < 10:
            raise FaceServiceError("建议至少采集 10 张人脸样本。")
        cv2 = _load_cv2()
        cascade = self._cascade(cv2)
        camera = self._camera(cv2)
        user_dir = self.settings.faces_dir / _safe_name(user_name)
        user_dir.mkdir(parents=True, exist_ok=True)
        count = 0

        try:
            while count < samples:
                ok, frame = camera.read()
                if not ok:
                    raise FaceServiceError("摄像头读取失败。")
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = cascade.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
                for x, y, width, height in faces:
                    count += 1
                    crop = gray[y : y + height, x : x + width]
                    cv2.imwrite(str(user_dir / f"{count:04d}.jpg"), crop)
                    cv2.rectangle(
                        frame, (x, y), (x + width, y + height), (40, 200, 80), 2
                    )
                    if count >= samples:
                        break
                cv2.putText(
                    frame,
                    f"Samples: {count}/{samples}  Esc/Q to stop",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )
                cv2.imshow("Smart Door Guardian - Collect Faces", frame)
                key = cv2.waitKey(30) & 0xFF
                if key in {27, ord("q")}:
                    break
        finally:
            camera.release()
            cv2.destroyAllWindows()
        return count

    def train(self) -> tuple[int, int]:
        """Train an LBPH model from ``data/faces/<name>/*.jpg``."""
        cv2 = _load_cv2()
        try:
            import numpy as np  # type: ignore
        except ImportError as exc:
            raise FaceServiceError("未安装 NumPy。") from exc

        user_directories = sorted(
            path for path in self.settings.faces_dir.iterdir() if path.is_dir()
        )
        if not user_directories:
            raise FaceServiceError("没有人脸样本，请先执行 collect。")

        samples = []
        labels: list[int] = []
        label_map: dict[str, str] = {}
        for user_directory in user_directories:
            user_samples = []
            for image_path in sorted(user_directory.glob("*.jpg")):
                image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                if image is None or image.size == 0:
                    continue
                user_samples.append(image)

            if not user_samples:
                continue

            label = len(label_map)
            label_map[str(label)] = user_directory.name
            samples.extend(user_samples)
            labels.extend([label] * len(user_samples))

        if not samples:
            raise FaceServiceError("未找到可用的 JPG 人脸样本。")

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(samples, np.asarray(labels, dtype=np.int32))
        recognizer.write(str(self.settings.model_path))
        self.settings.labels_path.write_text(
            json.dumps(label_map, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return len(label_map), len(samples)

    def recognize(self) -> RecognitionResult:
        """Recognize a registered face. Press Esc or Q to cancel."""
        if not self.ready:
            return RecognitionResult(False, reason="尚未训练人脸模型。")

        cv2 = _load_cv2()
        cascade = self._cascade(cv2)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(str(self.settings.model_path))
        labels = json.loads(self.settings.labels_path.read_text(encoding="utf-8"))
        camera = self._camera(cv2)
        consecutive_label: int | None = None
        consecutive_matches = 0

        try:
            for _ in range(self.settings.face_max_frames):
                ok, frame = camera.read()
                if not ok:
                    return RecognitionResult(False, reason="摄像头读取失败。")
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = cascade.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
                best_match: tuple[int, str, float, float] | None = None
                for x, y, width, height in faces:
                    label, distance = recognizer.predict(
                        gray[y : y + height, x : x + width]
                    )
                    registered_name = labels.get(str(label))
                    matched = (
                        registered_name is not None
                        and distance <= self.settings.face_confidence_threshold
                    )
                    name = registered_name if matched else "陌生人"
                    score = max(0.0, 100.0 - float(distance))
                    color = (40, 200, 80) if matched else (40, 40, 220)
                    cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)
                    cv2.putText(
                        frame,
                        f"{name} {score:.0f}%",
                        (x, max(25, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        color,
                        2,
                    )
                    if matched and (
                        best_match is None or float(distance) < best_match[3]
                    ):
                        best_match = (label, name, score, float(distance))

                if best_match is None:
                    consecutive_label = None
                    consecutive_matches = 0
                else:
                    label, name, score, _ = best_match
                    if label == consecutive_label:
                        consecutive_matches += 1
                    else:
                        consecutive_label = label
                        consecutive_matches = 1
                    if consecutive_matches >= self.settings.face_required_matches:
                        return RecognitionResult(True, name=name, confidence=score)

                cv2.imshow("Smart Door Guardian - Recognition", frame)
                key = cv2.waitKey(30) & 0xFF
                if key in {27, ord("q")}:
                    return RecognitionResult(False, reason="用户取消识别。")
        finally:
            camera.release()
            cv2.destroyAllWindows()

        return RecognitionResult(False, reason="在限定时间内未识别到授权用户。")
