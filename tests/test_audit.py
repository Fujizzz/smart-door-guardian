from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from door_guardian.audit import AuditLog  # noqa: E402


class AuditLogTests(unittest.TestCase):
    def test_records_and_reads_recent_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = AuditLog(Path(directory) / "events.jsonl")
            log.record("access_granted", method="code")
            log.record("departure")
            events = log.recent(1)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event"], "departure")


if __name__ == "__main__":
    unittest.main()

