"""Serve the real #9 workbench, retaining every task and pre-execution source byte."""

import shutil
import sys
from pathlib import Path

import uvicorn

from pybert.web.archive import json_bytes
from pybert.web.data import source_identity
from pybert.web.server import create_app
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 1
assert VERSION in (1, 2, 3)
OUT = ROOT / f"docs/webui/issue9/evidence/chrome-v{VERSION}"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    identities = source_identity()
    for relative in identities:
        target = OUT / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / relative, target)
    (OUT / "before-execution.json").write_bytes(json_bytes({"source_identity": identities, "mode": "real workbench / no worker overrides"}))
    shutil.copyfile(__file__, OUT / "serve_web_viterbi.py")
    manager = Tasks(OUT / "local/service")
    # Preserve evidence from every success; the product still keeps exactly two cache entries.
    def preserve(directory):
        assert directory.resolve().is_relative_to((OUT / "local/service").resolve())
        # The cache index drops its entry; keep its original bytes in this evidence service.
    manager._remove_directory = preserve
    uvicorn.run(create_app(manager), host="127.0.0.1", port=8775 + VERSION)
