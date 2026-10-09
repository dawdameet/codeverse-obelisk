"""Run the public test-suite: ``python scripts/run_tests.py [-v]``."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    verbosity = 2 if "-v" in sys.argv else 1
    suite = unittest.defaultTestLoader.discover(str(ROOT / "public_tests"), top_level_dir=str(ROOT / "public_tests"))
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
