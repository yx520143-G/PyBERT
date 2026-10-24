"""A fresh spawn process per native operation, with explicit cancellation observation."""

import contextlib
import json
import traceback
import time
import logging
from pathlib import Path

from pybert.models.bert import my_run_simulation
from pybert.web.config import input_hash, load_config, new_engine, normalize, snapshot, validate, warnings, extensions
from pybert.web.data import collect
from pybert.web.resources import inspect_channels, projection
from pybert.web.com import ComCancelled, run_com


class Stream:
    def __init__(self, emit):
        self.emit = emit

    def write(self, text):
        if text.strip():
            self.emit("log", text=text.rstrip())

    def flush(self):
        pass


def run_worker(task_id, operation, request, directory, cancel_event, connection):
    """Only the parent publishes terminal state, after this function exits and joins."""
    observed = False
    native_errors = []

    def emit(kind, **values):
        if kind == "log" and any(line.lstrip().startswith("ERROR:") for line in values["text"].splitlines()):
            native_errors.append(values["text"])
        connection.send(dict(task_id=task_id, kind=kind, **values))

    def cancelled():
        nonlocal observed
        if cancel_event.is_set():
            if not observed:
                observed = True
                emit("cancel_observed", observed_at=time.time())
            return True
        return False

    terminal = {}
    try:
        with contextlib.redirect_stdout(Stream(emit)), contextlib.redirect_stderr(Stream(emit)):
            if cancelled():
                if operation == "com":
                    raise ComCancelled("Cancelled before validation")
                raise RuntimeError("Cancelled before validation")
            if operation == "normalize":
                result = normalize(request)
                if cancelled():
                    raise RuntimeError("Cancelled after normalization")
                terminal = {"status": "succeeded", "result": result}
            elif operation == "com":
                handler = logging.StreamHandler(Stream(emit))
                handler.setLevel(logging.ERROR)
                handler.setFormatter(logging.Formatter("ERROR: %(message)s"))
                logging.getLogger().addHandler(handler)
                try:
                    terminal = {"status": "succeeded", "result": run_com(task_id, request, directory, cancelled, emit, lambda: native_errors)}
                finally:
                    logging.getLogger().removeHandler(handler)
                    handler.close()
            elif operation == "run":
                p = new_engine()
                p.observe(lambda e: emit("phase", phase=str(e.new)), "status")
                p.observe(lambda e: emit("log", text=e.new[len(e.old) :].rstrip()), "console_log")
                config = request["config"]
                if input_hash(config) != request["input_hash"]:
                    raise ValueError("Input hash does not match complete requested snapshot.")
                identity_hash = input_hash({"config": config, "runtime_extensions": request.get("runtime_extensions", {}),
                                            "resource_bindings": request.get("resource_bindings", {})})
                if request.get("input_identity_hash", identity_hash) != identity_hash:
                    raise ValueError("Full input identity hash mismatch.")
                load_config(p, config, snapshot(p))
                effective = snapshot(p)
                if input_hash(effective) != request["input_hash"]:
                    raise ValueError("Effective input differs from frozen snapshot; normalize before Run.")
                validate(effective, snapshot(new_engine()), execution=True)
                runtime = extensions(request.get("runtime_extensions", {}))
                resources = inspect_channels(config, request.get("frozen_resources", []))
                projected = projection(effective, request.get("frozen_resources", []))
                p.trait_setq(ch_file=projected["ch_file"], ch_files=projected["ch_files"], enable_com=False)
                if cancelled():
                    raise RuntimeError("Cancelled before simulation")
                emit("phase", phase="running")
                observations = {}
                my_run_simulation(
                    p, initial_run=True, update_plots=False, aborted_sim=cancelled, observations=observations
                )
                # Native early returns and partial producers cannot become successful runs.
                if p.status != "Ready." or set(observations) != {"source", "chnl", "tx", "ctle", "dfe"}:
                    raise RuntimeError(f"Native producer did not complete: {p.status}")
                if cancelled():
                    raise RuntimeError("Cancelled after simulation")
                emit("phase", phase="building native analyses")
                identity = {
                    "run_id": task_id,
                    "draft_revision": request.get("draft_revision", 0),
                    "input_hash_schema": "native-json-v1-integral-floats",
                    "requested_input": config,
                    "effective_input": effective,
                    "input_hash": request["input_hash"],
                    "input_identity_hash": identity_hash,
                    "resource_hash_schema": "ordered-field-content-v1",
                    "resource_hash": request.get("resource_hash", input_hash({})),
                    "resources": resources,
                    "resource_bindings": request.get("resource_bindings", {}),
                    "runtime_extensions": runtime,
                    "runtime_extension_status": {key: "inactive in Native Run; retained for #8/#10" for key in runtime.get("values", {})},
                    "execution_strategy": {"deferred_com": request.get("deferred_com"),
                                           "inactive_model_paths": "retained without loading observers",
                                           "worker_projection": projected},
                    "warnings": warnings(effective),
                }
                collect(p, observations, directory, identity, cancelled)
                if cancelled():
                    raise RuntimeError("Cancelled before publication")
                terminal = {"status": "succeeded", "result": {"run_id": task_id}}
            else:
                raise ValueError(f"Unknown worker operation {operation}")
    except ComCancelled as err:
        terminal = {"status": "cancelled", "error": str(err), "error_type": type(err).__name__}
    except Exception as err:
        terminal = {
            "status": "cancelled" if observed and operation != "com" else "failed",
            "error": str(err),
            "error_type": type(err).__name__,
            "traceback": traceback.format_exc(),
        }
    finally:
        terminal.update(cancel_observed=observed, cancel_requested=cancel_event.is_set())
        Path(directory, "terminal.json").write_text(json.dumps(terminal, indent=2), encoding="utf-8")
        emit("terminal", **terminal)
        connection.close()
