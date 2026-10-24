"""Serve the real #9 workbench, retaining every task and pre-execution source byte."""

import shutil
from pathlib import Path

import uvicorn

from pybert.web.archive import json_bytes
from pybert.web.data import source_identity
from pybert.web.server import create_app
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue9/evidence/chrome-v1"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    identities = source_identity()
    for relative in identities:
        target = OUT / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / relative, target)
    (OUT / "before-execution.json").write_bytes(json_bytes({"source_identity": identities, "mode": "real workbench / no worker overrides"}))
    manager = Tasks(OUT / "local/service")
    # Preserve evidence from every success; the product still keeps exactly two cache entries.
    def preserve(directory):
        target = OUT / "local/evicted" / directory.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(directory, target)
        shutil.rmtree(directory)
    manager._remove_directory = preserve
    uvicorn.run(create_app(manager), host="127.0.0.1", port=8776)
