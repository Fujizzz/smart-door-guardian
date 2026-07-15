from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from door_guardian.access import AccessCodeError, AccessCodeStore  # noqa: E402


class AccessCodeStoreTests(unittest.TestCase):
    def test_hashes_and_verifies_access_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.json"
            store = AccessCodeStore(path, "123456")
            self.assertTrue(store.verify("123456"))
            self.assertFalse(store.verify("654321"))
            self.assertNotIn("123456", path.read_text(encoding="utf-8"))

    def test_change_requires_current_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = AccessCodeStore(Path(directory) / "access.json", "123456")
            with self.assertRaises(AccessCodeError):
                store.change("bad-code", "new-code")
            store.change("123456", "new-code")
            self.assertTrue(store.verify("new-code"))

    def test_rejects_short_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AccessCodeError):
                AccessCodeStore(Path(directory) / "access.json", "123")

    def test_rejects_tampered_hash_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.json"
            store = AccessCodeStore(path, "123456")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["algorithm"] = "unsupported"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(store.verify("123456"))


if __name__ == "__main__":
    unittest.main()
