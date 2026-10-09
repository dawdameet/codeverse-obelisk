"""Shared helpers for the OBELISK test-suite."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


def _find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "obelisk" / "__init__.py").exists():
            return parent
    raise RuntimeError("cannot locate the OBELISK repository root")


ROOT = _find_root()
SRC = Path(os.environ.get("OBELISK_SRC") or ROOT / "src")
DATA = ROOT / "data"
LAUNCHER = ROOT / "obelisk.py"

sys.path.insert(0, str(SRC))
if SRC != ROOT / "src":  # running against a copy of the sources elsewhere
    os.environ.setdefault("OBELISK_DATA_DIR", str(DATA))

from obelisk.cli import main  # noqa: E402


def run(*argv: str) -> tuple[int, str, str]:
    """Run the CLI in-process. Returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


def indexed_ids() -> set[str]:
    """Document IDs present in the current state's index."""
    path = Path(os.environ["OBELISK_HOME"]) / "index.json"
    return set(json.loads(path.read_text(encoding="utf-8"))["doc_ids"])


def run_json(*argv: str) -> dict:
    code, out, err = run(*argv, "--json")
    if code != 0:
        raise AssertionError(f"exit {code}: {err}")
    return json.loads(out)


class StateTestCase(unittest.TestCase):
    """Each test gets a fresh, empty OBELISK state directory."""

    ingest = True
    cache_size = None

    def setUp(self) -> None:
        self._home = tempfile.mkdtemp(prefix="obelisk-test-")
        self._saved = {k: os.environ.get(k) for k in ("OBELISK_HOME", "OBELISK_CACHE_SIZE")}
        os.environ["OBELISK_HOME"] = self._home
        if self.cache_size:
            os.environ["OBELISK_CACHE_SIZE"] = str(self.cache_size)
        else:
            os.environ.pop("OBELISK_CACHE_SIZE", None)
        if self.ingest:
            code, _, err = run("ingest", str(DATA))
            assert code == 0, err

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self._home, ignore_errors=True)
