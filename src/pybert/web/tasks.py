"""One service-wide numerical slot, including observer-only normalization."""

import copy
import json
import multiprocessing
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from pybert.web.worker import run_worker
from pybert.web.resources import Resources
from pybert.web.config import input_hash, parse_yaml


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

    def start(self, operation, request, task_id=None):
        with self.lock:
            if self.active is not None:
                raise BusyError("The native engine slot is busy; normalization is pending until the worker exits.")
            request = copy.deepcopy(request)
            task_id = task_id or str(uuid.uuid4())
            if operation == "run":
                rows = self.resources.for_run(request["config"], request.get("resource_bindings", {}))
                request["frozen_resources"] = rows
                request["resource_hash"] = input_hash([{k: row[k] for k in ("field", "index", "sha256")} for row in rows])
                if request["config"]["enable_com"]:
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
            receive, send = self.context.Pipe(duplex=False)
            process = self.context.Process(
                target=self.worker, args=(task_id, operation, request, str(directory), cancel, send)
            )
            task = {
                "task_id": task_id,
                "operation": operation,
                "state": "validating",
                "phase": "validating",
                "cancel_requested": False,
                "cancel_observed": False,
                "worker_exited": False,
                "logs": [],
                "created_at": time.time(),
                "request_hash": request.get("input_hash"),
                "parent_run_id": request.get("parent_run_id"),
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
                        if not task["cancel_requested"] and task["operation"] in ("run", "com"):
                            task["state"] = "running"
                    elif message["kind"] == "log":
                        task["logs"].append(message["text"])
                        task["logs"] = task["logs"][-1000:]
                    elif message["kind"] == "cancel_observed":
                        task["cancel_observed"] = True
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
            task.update(
                state=terminal["status"],
                phase=terminal["status"],
                worker_exited=True,
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
                    manifest["logs"] = list(task["logs"])
                    manifest["cancellation"] = {
                        k: task[k] for k in ("cancel_requested", "cancel_observed", "worker_exited")
                    }
                    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    self.runs.append(task_id)
                    while len(self.runs) > 2:
                        old = self.runs.pop(0)
                        self._remove_directory(self.tasks[old]["directory"])
            self.active = None
            entry["done"].set()
            p.close()
            if task["state"] == "succeeded" and task["operation"] == "com":
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
                           task_id=plan["com_id"])
            # Keep the current task and both successful results, plus bounded recent logs.
            for old in list(self.tasks):
                if len(self.tasks) <= 32:
                    break
                if old not in self.runs and old not in self.coms and old != self.current and self.tasks[old]["done"].is_set():
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
                entry["data"].update(cancel_requested=True, state="cancel_requested")
            return copy.deepcopy(entry["data"])

    def get(self, task_id):
        with self.lock:
            return copy.deepcopy(self.tasks[task_id]["data"])

    def normalize(self, request):
        # A cached constructor snapshot is plain immutable metadata, not an observer operation.
        with self.lock:
            if request.get("mode") == "defaults" and self.defaults is not None:
                return copy.deepcopy(self.defaults)
        request = copy.deepcopy(request)
        if request.get("base_directory"):
            config = parse_yaml(request["yaml"]) if "yaml" in request else request["config"]
            request["resource_bindings"] = self.resources.bind_base(config, request["base_directory"])
        task = self.start("normalize", request)
        self.tasks[task["task_id"]]["done"].wait()
        result = self.get(task["task_id"])
        if result["state"] != "succeeded":
            raise ValueError(result.get("error", result["state"]))
        if request.get("mode") == "defaults":
            with self.lock:
                self.defaults = copy.deepcopy(result["result"])
        return result["result"]

    def directory(self, run_id):
        with self.lock:
            if run_id not in self.runs:
                raise KeyError("Run unavailable (temporary cache or service restarted).")
            return self.tasks[run_id]["directory"]

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
            }
