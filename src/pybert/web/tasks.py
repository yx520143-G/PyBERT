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

    def start(self, operation, request):
        with self.lock:
            if self.active is not None:
                raise BusyError("The native engine slot is busy; normalization is pending until the worker exits.")
            task_id = str(uuid.uuid4())
            directory = self.root / task_id
            directory.mkdir()
            cancel = self.context.Event()
            receive, send = self.context.Pipe(duplex=False)
            process = self.context.Process(target=self.worker, args=(task_id, operation, request, str(directory), cancel, send))
            task = dict(task_id=task_id, operation=operation, state="validating", phase="validating",
                        cancel_requested=False, cancel_observed=False, worker_exited=False,
                        logs=[], created_at=time.time(), request_hash=request.get("input_hash"))
            event = threading.Event()
            self.tasks[task_id] = dict(data=task, process=process, cancel=cancel, done=event, directory=directory)
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
                readable = open_pipe and receive.poll(.05)
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
                        if not task["cancel_requested"] and task["operation"] == "run":
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
                p.join(.05)
        p.join()
        receive.close()
        with self.lock:
            if p.exitcode != 0 or terminal is None:
                terminal = dict(status="failed", error=f"Worker exited {p.exitcode} without a valid terminal envelope.",
                                cancel_observed=task["cancel_observed"])
            task.update(state=terminal["status"], phase=terminal["status"], worker_exited=True,
                        exitcode=p.exitcode, finished_at=time.time(), cancel_observed=terminal.get("cancel_observed", False))
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
                    manifest["cancellation"] = {k: task[k] for k in ("cancel_requested", "cancel_observed", "worker_exited")}
                    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    self.runs.append(task_id)
                    while len(self.runs) > 2:
                        old = self.runs.pop(0)
                        shutil.rmtree(self.tasks[old]["directory"])
            self.active = None
            entry["done"].set()

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
            return dict(active_task_id=self.active, current_task_id=self.current,
                        runs=[{key: row[key] for key in ("run_id", "input_hash", "effective_input", "summary")} for row in rows])
