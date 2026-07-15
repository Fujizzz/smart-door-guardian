"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_dotenv(path: Path) -> None:
    """Load a small, dependency-free subset of the dotenv format."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Secret fields are excluded from repr output."""

    project_root: Path = PROJECT_ROOT
    demo_mode: bool = True
    initial_access_code: str = field(default="123456", repr=False)
    camera_index: int = 0
    face_confidence_threshold: float = 65.0
    face_required_matches: int = 5
    face_max_frames: int = 300
    weather_latitude: float = 29.5630
    weather_longitude: float = 106.5516
    weather_timezone: str = "Asia/Shanghai"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = field(default="", repr=False)
    smtp_password: str = field(default="", repr=False)
    smtp_sender: str = ""
    smtp_recipient: str = ""
    smtp_use_ssl: bool = True

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def faces_dir(self) -> Path:
        return self.data_dir / "faces"

    @property
    def model_dir(self) -> Path:
        return self.project_root / "models"

    @property
    def model_path(self) -> Path:
        return self.model_dir / "lbph_model.yml"

    @property
    def labels_path(self) -> Path:
        return self.model_dir / "labels.json"

    @property
    def access_code_path(self) -> Path:
        return self.data_dir / "access_code.json"

    @property
    def audit_log_path(self) -> Path:
        return self.data_dir / "events.jsonl"

    def ensure_runtime_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.faces_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)


def get_settings(project_root: Path | None = None) -> Settings:
    """Build settings after loading ``.env`` from the project root."""
    root = (project_root or PROJECT_ROOT).resolve()
    load_dotenv(root / ".env")

    settings = Settings(
        project_root=root,
        demo_mode=_as_bool(os.getenv("DOOR_DEMO_MODE"), True),
        initial_access_code=os.getenv("DOOR_ACCESS_CODE", "123456"),
        camera_index=int(os.getenv("DOOR_CAMERA_INDEX", "0")),
        face_confidence_threshold=float(os.getenv("DOOR_FACE_THRESHOLD", "65")),
        face_required_matches=int(os.getenv("DOOR_REQUIRED_MATCHES", "5")),
        face_max_frames=int(os.getenv("DOOR_MAX_FRAMES", "300")),
        weather_latitude=float(os.getenv("WEATHER_LATITUDE", "29.5630")),
        weather_longitude=float(os.getenv("WEATHER_LONGITUDE", "106.5516")),
        weather_timezone=os.getenv("WEATHER_TIMEZONE", "Asia/Shanghai"),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_sender=os.getenv("SMTP_SENDER", ""),
        smtp_recipient=os.getenv("SMTP_RECIPIENT", ""),
        smtp_use_ssl=_as_bool(os.getenv("SMTP_USE_SSL"), True),
    )
    settings.ensure_runtime_dirs()
    return settings

