"""Bounded, explicitly removable references, separate from live task history."""

import copy
import os
import shutil
import tempfile
import threading
import uuid
from pathlib import Path

from pybert.web.archive import MAX_FILE_BYTES, load_archive, read_json, sha256
from pybert.web.legacy_results import load_legacy

MAX_REFERENCES = 4
MAX_REFERENCE_BYTES = 1024**3


class References:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.items = {}
        self.lock = threading.RLock()

    def add(self, content, name, trusted=False):
        if len(content) > MAX_FILE_BYTES:
            raise ValueError("Result file exceeds 256 MiB.")
        with self.lock:
            if len(self.items) >= MAX_REFERENCES:
                raise ValueError("Reference budget: 4 records. Remove a loaded reference, then retry; none evicted.")
            with tempfile.TemporaryDirectory(prefix=".loading-", dir=self.root) as staging:
                if name.lower().endswith(".pybert_data"):
                    run, size = load_legacy(content, staging, trusted)
                    kind = "legacy"
                else:
                    run, size = load_archive(content, staging)
                    kind = "archive"
                if size + sum(row["array_bytes"] for row in self.items.values()) > MAX_REFERENCE_BYTES:
                    raise ValueError("Reference byte budget: 1 GiB. Remove a loaded reference, then retry; none evicted.")
                record_id = f"ref-{uuid.uuid4()}"
                directory = self.root / record_id
                os.replace(staging, directory)
            self.items[record_id] = {"record_id": record_id, "run_id": run["run_id"], "kind": kind,
                                     "name": Path(name.replace("\\", "/")).name, "source_sha256": sha256(content),
                                     "array_bytes": size, "file_bytes": len(content)}
            return self.manifest(record_id)

    def directory(self, record_id):
        with self.lock:
            if record_id not in self.items:
                raise KeyError("Loaded reference unavailable; reopen its saved file.")
            return self.root / record_id

    def manifest(self, record_id):
        with self.lock:
            row = copy.deepcopy(self.items[record_id])
            directory = self.directory(record_id)
            saved = read_json((directory / "archive.json").read_bytes()) if (directory / "archive.json").exists() else {}
            return {**read_json((directory / "manifest.json").read_bytes()), **row,
                    "saved_subfunctions": saved.get("subfunctions", {}), "archive_saved_at": saved.get("saved_at")}

    def remove(self, record_id):
        with self.lock:
            directory = self.directory(record_id).resolve()
            if directory.parent != self.root.resolve():
                raise ValueError("Reference outside managed root.")
            shutil.rmtree(directory)
            del self.items[record_id]

    def index(self):
        with self.lock:
            return copy.deepcopy(list(self.items.values()))


def verify_replay_resources(run, rows):
    expected = [{key: row.get(key) for key in ("field", "index", "sha256")} for row in run.get("resources", [])]
    actual = [{key: row.get(key) for key in ("field", "index", "sha256")} for row in rows if row["field"] in ("ch_file", "ch_files")]
    if expected != actual:
        raise ValueError(f"Saved run resource content changed/missing; rebind matching field/index/hash. Expected {expected}; supplied {actual}.")
