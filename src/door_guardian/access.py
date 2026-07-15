"""Secure local access-code storage."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path


class AccessCodeError(ValueError):
    """Raised when an access code is invalid."""


class AccessCodeStore:
    """Persist a salted PBKDF2 hash instead of a plaintext access code."""

    iterations = 200_000

    def __init__(self, path: Path, initial_code: str) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.set_code(initial_code)

    @staticmethod
    def _validate(code: str) -> None:
        if len(code) < 6:
            raise AccessCodeError("访问码至少需要 6 位。")
        if len(code) > 128:
            raise AccessCodeError("访问码过长。")

    @classmethod
    def _derive(cls, code: str, salt: bytes, iterations: int | None = None) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", code.encode("utf-8"), salt, iterations or cls.iterations
        )

    def set_code(self, code: str) -> None:
        self._validate(code)
        salt = secrets.token_bytes(16)
        digest = self._derive(code, salt)
        payload = {
            "algorithm": "pbkdf2_sha256",
            "iterations": self.iterations,
            "salt": salt.hex(),
            "digest": digest.hex(),
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)

    def verify(self, code: str) -> bool:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload["algorithm"] != "pbkdf2_sha256":
                return False
            iterations = int(payload["iterations"])
            if not 100_000 <= iterations <= 5_000_000:
                return False
            salt = bytes.fromhex(payload["salt"])
            expected = bytes.fromhex(payload["digest"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            return False
        actual = self._derive(code, salt, iterations)
        return hmac.compare_digest(actual, expected)

    def change(self, current_code: str, new_code: str) -> None:
        if not self.verify(current_code):
            raise AccessCodeError("当前访问码不正确。")
        self.set_code(new_code)
