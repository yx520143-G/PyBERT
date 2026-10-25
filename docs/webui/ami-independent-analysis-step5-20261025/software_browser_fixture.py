"""Serve four explicitly synthetic F6 archives for read-only browser QA. No model DLL is used."""

import argparse
import sys
from pathlib import Path

import pytest
import uvicorn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))

from test_ami_partial_main import collect_main
from pybert.web.archive import save_archive
from pybert.web.server import create_app
from pybert.web.tasks import Tasks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8769)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    manager = Tasks(args.directory / "service")
    for case in ("full", "ber_short", "fft_gap", "future"):
        directory = args.directory / case
        directory.mkdir()
        with pytest.MonkeyPatch.context() as patch:
            collect_main(patch, directory, case)
        saved = directory / ("SYNTHETIC-" + case + ".pybert_run")
        save_archive(directory, saved)
        manager.references.add(saved.read_bytes(), saved.name)
    uvicorn.run(create_app(manager), host="127.0.0.1", port=args.port, log_level="warning")
