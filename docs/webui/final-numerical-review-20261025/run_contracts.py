"""Use the existing runtime with the reviewed checkout; no environment installation."""
import os
from pathlib import Path
import sys

ROOT = Path(r"C:\Users\yx\.codex\worktrees\pybert-final-parity\serial-bus-simulator")
DEPS = Path(r"E:\serial-bus-simulator-dependencies\pybert-issue28-rng-pin")
sys.path[:0] = [str(ROOT / "src"), str(DEPS / "PyAMI/src"), str(DEPS / "PyChOpMarg/src")]
sys.dont_write_bytecode = True
os.environ["ETS_TOOLKIT"] = "null"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", *sys.argv[1:]]))
