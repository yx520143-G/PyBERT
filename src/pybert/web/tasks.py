"""One service-wide numerical slot, including observer-only normalization."""

import copy
import json
import multiprocessing
import shutil
import tempfile
import threading
import time
import uuid
import math
from pathlib import Path

import numpy as np

from pybert.web.worker import run_worker
from pybert.web.resources import Resources
from pybert.web.config import input_hash, yaml_text, unresolved_references
from pybert.web.records import References, verify_replay_resources
from pybert.web.archive import MAX_ARRAY_BYTES
from pybert.web.optimization import load_optimization


class BusyError(RuntimeError):
    pass


class Tasks:
    def __init__(self, directory=None, worker=run_worker):
        self.root = Path(directory or tempfile.mkdtemp(prefix="pybert-web-"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.worker = worker
        self.context = multiprocessing.get_context("spawn")
        self.lock = threading.RLock()
        self.active = None
        self.current = None
        self.tasks = {}
        self.runs = []
        self.defaults = None
        self.resources = Resources(self.root / "resources")
        self.coms = []
        self.optimizations = []
        self.optimization_references = {}
        self.references = References(self.root / "references")

    def start(self, operation, request, task_id=None, cancel_requested=False):
        with self.lock:
            if self.active is not None:
                raise BusyError("The native engine slot is busy; normalization is pending until the worker exits.")
            if operation == "optimization" and len(self.optimizations) >= 16:
                raise ValueError("Optimization record budget (16) reached; save records and restart the service before another optimization. Existing records retained.")
            if operation == "optimization" and self.optimization_bytes() > 1024**3 - MAX_ARRAY_BYTES:
                raise ValueError("Optimization storage budget reserves at most 768 MiB for the next job within 1 GiB; existing records retained.")
            request = copy.deepcopy(request)
            if "rx_viterbi_fec" in request or "rx_viterbi_fec" in request.get("config", {}):
                raise ValueError("unsupported_native_fec: API-only FEC is unsupported.")
            if operation == "run" and request["config"].get("rx_use_viterbi"):
                from pybert.web.viterbi import plan

                plan(request["config"], execution=True)
            task_id = task_id or str(uuid.uuid4())
            if operation in ("run", "optimization"):
                rows = self.resources.for_run(request["config"], request.get("resource_bindings", {}))
                source = request.get("replay_guard")
                if source is not None and (not isinstance(source, dict) or source.get("version") != 1 or not isinstance(source.get("resources"), list)):
                    raise ValueError("Unknown or incomplete replay resource guard; no defaults substituted.")
                if source is None and request.get("source_record_id"):
                    source = self.manifest(request["source_record_id"])
                    if source.get("legacy"):
                        raise ValueError("Legacy has no complete input/resource evidence; cannot rerun it.")
                if source is not None:
                    verify_replay_resources(source, rows)
                request["frozen_resources"] = rows
                request["resource_hash"] = input_hash([{k: row[k] for k in ("field", "index", "sha256")} for row in rows])
                if source and source.get("resource_hash") and source["resource_hash"] != request["resource_hash"]:
                    raise ValueError("Saved run resource identity changed, including its COM configuration; bind original content before Run.")
                if operation == "run" and request["config"]["enable_com"]:
                    request["deferred_com"] = {"com_id": str(uuid.uuid4()), "parent_run_id": task_id}
            elif operation == "com" and "frozen_resources" not in request:
                request["frozen_resources"] = [self.resources.freeze(request.get("thru_resource_id"), "com_thru", request.get("thru_reference", ""))]
                if request.get("config_resource_id"):
                    request["frozen_resources"].append(self.resources.freeze(request["config_resource_id"], "com_cfg_file", request.get("config_reference", "")))
            request_text = json.dumps(request, indent=2, allow_nan=False)
            directory = self.root / task_id
            directory.mkdir()
            (directory / "request.json").write_text(request_text, encoding="utf-8")
            cancel = self.context.Event()
            if cancel_requested:
                cancel.set()
            receive, send = self.context.Pipe(duplex=False)
            process = self.context.Process(
                target=self.worker, args=(task_id, operation, request, str(directory), cancel, send)
            )
            task = {
                "task_id": task_id,
                "operation": operation,
                "state": "cancel_requested" if cancel_requested else "validating",
                "phase": "validating",
                "cancel_requested": cancel_requested,
                "cancel_requested_at": time.time() if cancel_requested else None,
                "cancel_observed_at": None,
                "cancel_observed": False,
                "worker_exited": False,
                "logs": [],
                "created_at": time.time(),
                "request_hash": request.get("input_hash"),
                "parent_run_id": request.get("parent_run_id"),
                "resource_inputs": copy.deepcopy(request.get("frozen_resources", [])),
                "parameter_source": request.get("parameter_source"),
            }
            event = threading.Event()
            self.tasks[task_id] = {
                "data": task,
                "process": process,
                "cancel": cancel,
                "done": event,
                "directory": directory,
                "request": request,
            }
            self.active = self.current = task_id
            process.start()
            send.close()
            threading.Thread(target=self._watch, args=(task_id, receive), daemon=True).start()
            return copy.deepcopy(task)

    def _watch(self, task_id, receive):
        entry = self.tasks[task_id]
        p, task = entry["process"], entry["data"]
        terminal = None
        open_pipe = True
        while p.is_alive() or open_pipe:
            try:
                readable = open_pipe and receive.poll(0.05)
            except (OSError, EOFError):
                open_pipe = False
                readable = False
            if readable:
                try:
                    message = receive.recv()
                except (EOFError, OSError):
                    open_pipe = False
                    continue
                if message.get("task_id") != task_id:
                    continue
                with self.lock:
                    if message["kind"] == "terminal":
                        terminal = message
                        task["phase"] = "worker finishing; waiting for exit"
                    elif message["kind"] == "phase":
                        task["phase"] = message["phase"]
                        if not task["cancel_requested"] and task["operation"] in ("run", "com", "optimization"):
                            task["state"] = "running"
                    elif message["kind"] == "log":
                        task["logs"].append(message["text"])
                        task["logs"] = task["logs"][-1000:]
                    elif message["kind"] == "cancel_observed":
                        task["cancel_observed"] = True
                        task["cancel_observed_at"] = message.get("observed_at", time.time())
            elif not p.is_alive():
                # The child has exited; drain messages already flushed to the pipe.
                if not open_pipe:
                    break
            elif not open_pipe:
                p.join(0.05)
        p.join()
        receive.close()
        with self.lock:
            if p.exitcode != 0 or terminal is None:
                terminal = {
                    "status": "failed",
                    "error": f"Worker exited {p.exitcode} without a valid terminal envelope.",
                    "cancel_observed": task["cancel_observed"],
                }
            if terminal["status"] == "cancelled" and not terminal.get("cancel_observed"):
                terminal = {"status": "failed", "error": "Cancellation terminal lacked an observed native checkpoint acknowledgement.",
                            "cancel_observed": False}
            task.update(
                state=terminal["status"],
                phase=terminal["status"],
                worker_exited=True,
                worker_exit_confirmed_at=time.time(),
                exitcode=p.exitcode,
                finished_at=time.time(),
                cancel_observed=terminal.get("cancel_observed", False),
            )
            for key in ("error", "error_type", "traceback", "result"):
                if key in terminal:
                    task[key] = terminal[key]
            if task["state"] == "succeeded" and task["operation"] == "run":
                path = entry["directory"] / "manifest.json"
                if not path.exists():
                    task.update(state="failed", phase="failed", error="Missing result manifest.")
                else:
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    size = sum(math.prod(row["shape"]) * np.dtype(row["dtype"]).itemsize for row in manifest.get("datasets", {}).values())
                    if size > MAX_ARRAY_BYTES:
                        task.update(state="failed", phase="failed", error="Completed arrays exceed the 768 MiB per-record cache budget; previous successes retained.")
                    manifest["logs"] = list(task["logs"])
                    manifest["lifecycle"] = {key: task[key] for key in ("created_at", "finished_at", "state", "exitcode", "worker_exited")}
                    manifest["cancellation"] = {
                        k: task[k] for k in ("cancel_requested", "cancel_observed", "worker_exited", "cancel_requested_at", "cancel_observed_at", "worker_exit_confirmed_at")
                    }
                    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    if task["state"] == "succeeded":
                        self.runs.append(task_id)
                    while len(self.runs) > 2:
                        old = self.runs.pop(0)
                        self._remove_directory(self.tasks[old]["directory"])
            self.active = None
            if task["operation"] == "optimization":
                path = entry["directory"] / "optimization.json"
                if not path.exists() and task["state"] != "succeeded":
                    request = entry["request"]
                    record = {"schema_version": 1, "opt_id": task_id, "status": task["state"],
                              "requested_input": request["config"], "runtime_extensions": request.get("runtime_extensions", {}),
                              "resource_bindings": request.get("resource_bindings", {}), "input_hash": request["input_hash"],
                              "input_identity_hash": request.get("input_identity_hash"), "resource_hash": request.get("resource_hash"),
                              "resources": request.get("frozen_resources", []), "arrays": {}, "candidates": [],
                              "error": task.get("error", "Worker did not produce a complete record.")}
                    np.savez_compressed(entry["directory"] / "arrays.npz")
                    path.write_text(json.dumps(record, indent=2, allow_nan=False), encoding="utf-8")
                if path.exists():
                    record = json.loads(path.read_text(encoding="utf-8"))
                    record["status"] = task["state"]
                    record["task"] = copy.deepcopy(task)
                    path.write_text(json.dumps(record, indent=2, allow_nan=False), encoding="utf-8")
                    self.optimizations.append(task_id)
                elif task["state"] == "succeeded":
                    task.update(state="failed", phase="failed", error="Missing optimization record.")
            entry["done"].set()
            p.close()
            if task["state"] == "succeeded" and task["operation"] == "com":
                path = entry["directory"] / "com.json"
                if not path.exists():
                    task.update(state="failed", phase="failed", error="Missing COM result manifest.")
                else:
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    manifest["logs"] = list(task["logs"])
                    manifest["cancellation"] = {key: task[key] for key in ("cancel_requested", "cancel_observed", "worker_exited", "cancel_requested_at", "cancel_observed_at", "worker_exit_confirmed_at")}
                    manifest["exitcode"] = task["exitcode"]
                    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    self.coms.append(task_id)
            plan = entry["request"].get("deferred_com")
            if task["state"] == "succeeded" and task["operation"] == "run" and plan:
                rows = copy.deepcopy(entry["request"]["frozen_resources"])
                for row in rows:
                    if row["field"] == "ch_file":
                        row["field"] = "com_thru"
                # Parent process is already joined/closed, core manifest published once.
                self.start("com", {"parent_run_id": task_id, "frozen_resources": rows,
                                   "parameter_source": "spreadsheet" if any(r["field"] == "com_cfg_file" for r in rows) else "IEEE_8023dj defaults"},
                           task_id=plan["com_id"], cancel_requested=task["cancel_requested"])
            # Keep the current task and both successful results, plus bounded recent logs.
            for old in list(self.tasks):
                if len(self.tasks) <= 32:
                    break
                if old not in self.runs and old not in self.coms and old not in self.optimizations and old != self.current and self.tasks[old]["done"].is_set():
                    retired = self.tasks.pop(old)
                    if retired["directory"].exists():
                        self._remove_directory(retired["directory"])

    def _remove_directory(self, directory):
        target = directory.resolve()
        root = self.root.resolve()
        if target == root or not target.is_relative_to(root):
            raise ValueError("Task directory is outside the managed temporary result root.")
        shutil.rmtree(target)

    def cancel(self, task_id):
        with self.lock:
            entry = self.tasks[task_id]
            if self.active == task_id:
                entry["cancel"].set()
                if not entry["data"]["cancel_requested"]:
                    entry["data"]["cancel_requested_at"] = time.time()
                entry["data"].update(cancel_requested=True, state="cancel_requested")
            return copy.deepcopy(entry["data"])

    def get(self, task_id):
        with self.lock:
            return copy.deepcopy(self.tasks[task_id]["data"])

    def normalize(self, request):
        if "rx_viterbi_fec" in request or "rx_viterbi_fec" in request.get("config", {}):
            raise ValueError("unsupported_native_fec: API-only FEC is unsupported.")
        # A cached constructor snapshot is plain immutable metadata, not an observer operation.
        with self.lock:
            if request.get("mode") == "defaults" and self.defaults is not None:
                return copy.deepcopy(self.defaults)
        request = copy.deepcopy(request)
        task = self.start("normalize", request)
        self.tasks[task["task_id"]]["done"].wait()
        result = self.get(task["task_id"])
        if result["state"] != "succeeded":
            raise ValueError(result.get("error", result["state"]))
        if request.get("mode") == "defaults":
            with self.lock:
                self.defaults = copy.deepcopy(result["result"])
        normalized = result["result"]
        if request.get("base_directory"):
            with self.lock:
                normalized["resource_bindings"] = self.resources.bind_base(normalized["config"], request["base_directory"])
            normalized["unresolved_references"] = unresolved_references(normalized["config"], normalized["resource_bindings"])
            normalized["input_identity_hash"] = input_hash({"config": normalized["config"], "runtime_extensions": normalized["runtime_extensions"], "resource_bindings": normalized["resource_bindings"]})
            normalized["yaml"] = yaml_text(normalized["config"], normalized["runtime_extensions"], normalized["resource_bindings"])
        return normalized

    def directory(self, run_id):
        with self.lock:
            if run_id in self.references.items:
                return self.references.directory(run_id)
            if run_id not in self.runs:
                raise KeyError("Run unavailable (temporary cache or service restarted).")
            return self.tasks[run_id]["directory"]

    def optimization_directory(self, opt_id):
        with self.lock:
            if opt_id in self.optimization_references:
                return self.optimization_references[opt_id]
            if opt_id not in self.optimizations:
                raise KeyError("Optimization record unavailable; reopen a saved .pybert_opt archive.")
            return self.tasks[opt_id]["directory"]

    def optimization(self, opt_id):
        return {**json.loads((self.optimization_directory(opt_id) / "optimization.json").read_text(encoding="utf-8")), "record_id": opt_id}

    def open_optimization(self, content):
        with self.lock:
            if self.active is not None and self.tasks[self.active]["data"]["operation"] == "optimization":
                raise BusyError("Optimization archive loading waits until the active worker exits; its storage reservation remains in force.")
            if len(self.optimization_references) >= 4:
                raise ValueError("Four optimization archive references already loaded; restart/save before adding more.")
            record_id = "opt-ref-" + str(uuid.uuid4())
            directory = self.root / record_id
            directory.mkdir()
            try:
                record = load_optimization(content, directory)
                size = sum(row["nbytes"] for row in record["arrays"].values())
                if self.optimization_bytes() + size > 1024**3:
                    raise ValueError("Optimization records exceed the shared 1 GiB raw-array budget; existing records retained.")
            except Exception:
                self._remove_directory(directory)
                raise
            self.optimization_references[record_id] = directory
            return {"record_id": record_id, "opt_id": record["opt_id"], "status": record["status"]}

    def optimization_bytes(self):
        return sum(row["nbytes"] for rid in [*self.optimizations, *self.optimization_references]
                   for row in self.optimization(rid)["arrays"].values())

    def manifest(self, record_id):
        with self.lock:
            if record_id in self.references.items:
                return self.references.manifest(record_id)
            return {**json.loads((self.directory(record_id) / "manifest.json").read_text(encoding="utf-8")), "record_id": record_id, "kind": "temporary"}

    def index(self):
        with self.lock:
            rows = [json.loads((self.directory(r) / "manifest.json").read_text(encoding="utf-8")) for r in self.runs]
            return {
                "active_task_id": self.active,
                "current_task_id": self.current,
                "runs": [
                    {key: row[key] for key in ("run_id", "input_hash", "effective_input", "summary", "resource_hash")} for row in rows
                ],
                "com_tasks": [copy.deepcopy(entry["data"]) for entry in self.tasks.values() if entry["data"]["operation"] == "com"],
                "resources": list(copy.deepcopy(self.resources.items).values()),
                "references": self.references.index(),
                "optimizations": [{"record_id": rid, **{key: record.get(key) for key in ("opt_id", "status", "score_mode", "fom", "selected_candidate_id")}}
                                  for rid in [*self.optimizations, *self.optimization_references] for record in [self.optimization(rid)]],
                "result_budget": {"temporary_runs": 2, "temporary_policy": "oldest temporary success evicted; save archive to retain",
                                  "temporary_array_bytes_per_record": MAX_ARRAY_BYTES,
                                  "reference_records": 4, "reference_array_bytes": 1024**3,
                                  "reference_used_bytes": sum(row["array_bytes"] for row in self.references.index()),
                                  "temporary_file_bytes": sum((self.directory(r) / "arrays.npz").stat().st_size for r in self.runs)},
            }
