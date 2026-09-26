"""One-click test runner (bonus B3): chay toan bo pytest suite + coverage gate 80%.

    python script/run_tests.py            # tat ca test + bao cao coverage
    python script/run_tests.py -k quality # chuyen tiep tham so cho pytest
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    args = [
        str(ROOT / "tests"),
        "--cov",
        "--cov-report=term",
        f"--cov-report=html:{ROOT / 'htmlcov'}",
        "--cov-fail-under=80",
        *sys.argv[1:],
    ]
    return pytest.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
