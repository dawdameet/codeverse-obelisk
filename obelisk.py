"""Cross-platform launcher: ``python obelisk.py <command>``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from obelisk.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
