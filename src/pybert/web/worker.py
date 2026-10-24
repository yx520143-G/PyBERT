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
from pybert.web.resources import inspect_resources, projection
from pybert.web.com import ComCancelled, run_com
from pybert.web.optimization import OptimizationCancelled, run_optimization
from pybert.web.ami import AMICancelled, Execution, configure


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
    execution = Execution(cancelled)
    model_report = {}
    main_invocations = 0

    def checkpoint():
        if cancelled():
            raise AMICancelled("Native task checkpoint observed cancellation")
        return False
    try:
        with contextlib.redirect_stdout(Stream(emit)), contextlib.redirect_stderr(Stream(emit)):
            if cancelled():
                if operation == "com":
                    raise ComCancelled("Cancelled before validation")
                if operation == "optimization":
                    raise OptimizationCancelled("Cancelled before optimization validation")
                raise AMICancelled("Cancelled before validation")
            if operation == "normalize":
                result = normalize(request, cancelled, emit)
                if cancelled():
                    raise AMICancelled("Cancelled after normalization")
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
            elif operation == "optimization":
                terminal = {"status": "succeeded", "result": run_optimization(task_id, request, directory, cancelled, emit)}
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
                runtime = extensions(request.get("runtime_extensions", {}))
                frozen_runtime = json.loads(json.dumps(runtime))
                model_report = configure(p, config, runtime, request.get("frozen_resources", []), check=cancelled, emit=emit)
                if runtime != frozen_runtime:
                    raise ValueError("Complete frozen AMI parameter tree required; validate before Run.")
                effective = snapshot(p)
                effective.update({key: config[key] for side in ("tx", "rx") for key in (side + "_dll_file", side + "_ami_file", side + "_ibis_file")})
                if input_hash(effective) != request["input_hash"]:
                    raise ValueError("Effective input differs from frozen snapshot; normalize before Run.")
                validate(effective, snapshot(new_engine()), execution=True)
                resources = inspect_resources(config, request.get("frozen_resources", []))
                projected = projection(effective, request.get("frozen_resources", []))
                p.trait_setq(ch_file=projected["ch_file"], ch_files=projected["ch_files"], enable_com=False)
                if cancelled():
                    raise AMICancelled("Cancelled before simulation")
                emit("phase", phase="running")
                observations = {}
                decoding = {}
                with execution.capture():
                    main_invocations += 1
                    my_run_simulation(
                        p, initial_run=True, update_plots=False, aborted_sim=checkpoint, observations=observations,
                        decoding=decoding,
                    )
                # Native early returns and partial producers cannot become successful runs.
                if p.status != "Ready." or set(observations) != {"source", "chnl", "tx", "ctle", "dfe"}:
                    raise RuntimeError(f"Native producer did not complete: {p.status}")
                if cancelled():
                    raise AMICancelled("Cancelled after simulation")
                emit("phase", phase="building native analyses")
                identity = {
                    "run_id": task_id,
                    "source_record_id": request.get("source_record_id"),
                    "replay_guard": request.get("replay_guard"),
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
                    "runtime_extension_status": {
                        key: ("active model selections/parameters applied; see ami.models and actual_branch"
                              if key == "ami_models" and any(config[side + "_use_ami"] for side in ("tx", "rx")) else
                              "native GetWave clock selection consumes this request; actual source/fallback in ami.actual_branch"
                              if key == "rx_use_clocks" and config["rx_use_ami"] and config["rx_use_getwave"] else
                              "Tune setting retained; ordinary Run does not consume" if key in ("rlm", "ami_opt_trials", "optimizer_values") else
                              "inactive for this Run branch; requested value retained")
                        for key in runtime.get("values", {})},
                    "execution_strategy": {"deferred_com": request.get("deferred_com"),
                                           "model_paths": "active IBIS parsed and AMI binary loaded in this worker only; inactive paths retained",
                                           "worker_projection": projected},
                    "warnings": warnings(effective),
                }
                collect(p, observations, directory, identity, checkpoint, decoding=decoding,
                        ami=(execution, model_report) if model_report else None)
                if cancelled():
                    raise AMICancelled("Cancelled before publication")
                terminal = {"status": "succeeded", "result": {"run_id": task_id}}
            else:
                raise ValueError(f"Unknown worker operation {operation}")
    except ComCancelled as err:
        terminal = {"status": "cancelled", "error": str(err), "error_type": type(err).__name__}
    except OptimizationCancelled as err:
        terminal = {"status": "cancelled", "error": str(err), "error_type": type(err).__name__}
    except AMICancelled as err:
        terminal = {"status": "cancelled", "error": str(err), "error_type": type(err).__name__}
    except Exception as err:
        model_report = getattr(err, "ami_report", model_report)
        terminal = {
            "status": "failed",
            "error": str(err),
            "error_type": type(err).__name__,
            "traceback": traceback.format_exc(),
        }
    finally:
        terminal["main_invocations"] = main_invocations
        if execution.calls or model_report:
            execution.write(directory, model_report)
        terminal.update(cancel_observed=observed, cancel_requested=cancel_event.is_set())
        Path(directory, "terminal.json").write_text(json.dumps(terminal, indent=2), encoding="utf-8")
        emit("terminal", **terminal)
        connection.close()
