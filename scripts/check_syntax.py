"""Parse every project Python file without importing optional dependencies."""

from __future__ import annotations

import ast
from pathlib import Path


root = Path(__file__).resolve().parents[1]
files = sorted(root.rglob("*.py"))
errors: list[tuple[Path, Exception]] = []

for path in files:
    try:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as exc:
        errors.append((path, exc))

print(f"Parsed {len(files)} Python files; errors: {len(errors)}")
for path, error in errors:
    print(f"{path}: {error}")

raise SystemExit(1 if errors else 0)

