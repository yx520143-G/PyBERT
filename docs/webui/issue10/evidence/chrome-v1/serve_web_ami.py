"""Actual #10 Chrome service; keep evidence and never call a numerical entry on startup."""

import shutil
from pathlib import Path

import uvicorn

from pybert.web.archive import json_bytes
from pybert.web.data import source_identity
from pybert.web.server import create_app
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue10/evidence/chrome-v1"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    identities = source_identity()
    for relative in identities:
        target = OUT / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / relative, target)
    (OUT / "before.json").write_bytes(json_bytes({"source": identities, "numerical_calls_on_startup": 0,
                                                "fixture": "v2-executable Chrome presets"}))
    shutil.copyfile(__file__, OUT / "serve_web_ami.py")
    manager = Tasks(ROOT / ".pybert-web/issue10-chrome-v1")

    def preserve(directory):
        assert directory.resolve().is_relative_to(manager.root.resolve())

    manager._remove_directory = preserve
    uvicorn.run(create_app(manager), host="127.0.0.1", port=8785)
