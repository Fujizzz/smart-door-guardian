"""Command-line entry point."""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import platform
import sys

from .access import AccessCodeStore
from .config import get_settings
from .face import FaceService, FaceServiceError
from .gui import run_gui
from .weather import WeatherService


def _diagnose() -> int:
    settings = get_settings()
    modules = {
        "tkinter": importlib.util.find_spec("tkinter") is not None,
        "cv2": importlib.util.find_spec("cv2") is not None,
        "numpy": importlib.util.find_spec("numpy") is not None,
        "pyttsx3": importlib.util.find_spec("pyttsx3") is not None,
    }
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"Project: {settings.project_root}")
    print(f"Demo mode: {settings.demo_mode}")
    print(f"Face model ready: {FaceService(settings).ready}")
    print(f"Email configured: {bool(settings.smtp_host and settings.smtp_recipient)}")
    for name, installed in modules.items():
        print(f"Dependency {name}: {'OK' if installed else 'missing (optional)'}")
    return 0 if modules["tkinter"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smart Door Guardian")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("gui", help="启动桌面界面")
    subparsers.add_parser("diagnose", help="检查运行环境")

    collect = subparsers.add_parser("collect", help="采集人脸样本")
    collect.add_argument("name", help="用户名称")
    collect.add_argument("--samples", type=int, default=80)
    subparsers.add_parser("train", help="训练 LBPH 人脸模型")
    subparsers.add_parser("recognize", help="执行一次人脸识别")
    subparsers.add_parser("weather", help="获取当前天气")

    set_code = subparsers.add_parser("set-code", help="设置本地访问码")
    set_code.add_argument(
        "code", nargs="?", help="至少 6 位；省略时使用不回显的安全输入"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    command = args.command or "gui"

    try:
        if command == "gui":
            run_gui(settings)
            return 0
        if command == "diagnose":
            return _diagnose()
        if command == "collect":
            count = FaceService(settings).collect(args.name, args.samples)
            print(f"Collected {count} samples.")
            return 0
        if command == "train":
            users, samples = FaceService(settings).train()
            print(f"Trained {users} users from {samples} samples.")
            return 0
        if command == "recognize":
            result = FaceService(settings).recognize()
            print(result)
            return 0 if result.granted else 2
        if command == "weather":
            print(WeatherService(settings).current().sentence())
            return 0
        if command == "set-code":
            code = args.code or getpass.getpass("New access code: ")
            AccessCodeStore(settings.access_code_path, code).set_code(code)
            print("Access code updated.")
            return 0
    except (FaceServiceError, OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1
