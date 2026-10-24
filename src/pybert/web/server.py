"""Thin localhost HTTP boundary; no shared PyBERT instance in the server."""

import json
import base64
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from plotly.offline import get_plotlyjs

from pybert import __version__
from pybert.web import NATIVE_SHA, NATIVE_IMPORTER_SHA, PROTOTYPE_SHA, SCHEMA_VERSION
from pybert.web.data import adapter_sha, plot_payload
from pybert.web.tasks import BusyError, Tasks
from pybert.web.archive import MAX_FILE_BYTES, save_archive, read_json
from pybert.web.legacy_results import legacy_report, export_legacy
from pybert.web.optimization import save_optimization


def create_app(tasks=None):
    manager = tasks or Tasks()
    app = FastAPI(title="PyBERT local signal-chain workbench", version=__version__)
    app.state.tasks = manager

    @app.exception_handler(BusyError)
    async def busy(_request, err):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=409, content={"detail": str(err)})

    @app.exception_handler(ValueError)
    async def invalid(_request, err):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content={"detail": str(err)})

    @app.exception_handler(KeyError)
    async def unavailable(_request, err):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"detail": str(err)})

    @app.exception_handler(OSError)
    async def resource_access_failed(_request, err):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content={"detail": f"Resource/file access failed: {err}"})

    @app.get("/api/version")
    def version():
        return {
            "schema_version": SCHEMA_VERSION,
            "version": __version__,
            "adapter_sha": adapter_sha(),
            "native_sha": NATIVE_SHA,
            "native_importer_sha": NATIVE_IMPORTER_SHA,
            "prototype_sha": PROTOTYPE_SHA,
            "fork": "yx520143-G/PyBERT",
        }

    @app.post("/api/normalize")
    def normalize(request: dict):
        if request.get("mode", "load") not in ("defaults", "load", "patch"):
            raise ValueError("Optimizer actions require their dedicated endpoint and a registered record ID.")
        return manager.normalize(request)

    @app.post("/api/runs", status_code=202)
    def start_run(request: dict):
        if not all(key in request for key in ("config", "input_hash")):
            raise HTTPException(422, "Complete normalized config and input_hash are required.")
        return manager.start("run", request)

    @app.get("/api/state")
    def state():
        return manager.index()

    @app.post("/api/optimizations", status_code=202)
    def optimize(request: dict):
        if not all(key in request for key in ("config", "input_hash", "input_identity_hash", "runtime_extensions")):
            raise ValueError("Complete normalized Native input, identity hash and explicit optimization runtime are required.")
        return manager.start("optimization", request)

    @app.get("/api/optimizations/{opt_id}")
    def optimization(opt_id: str):
        return manager.optimization(opt_id)

    @app.post("/api/optimizer-actions/{action}")
    def optimizer_action(action: str, request: dict):
        if action not in ("optimizer_plan", "use_eq", "reset_eq"):
            raise ValueError("Unknown optimizer action.")
        body = {**request, "mode": action}
        if action == "use_eq":
            record = manager.optimization(request["record_id"])
            body["optimization"] = {**record, "current_config": request["config"]}
        return manager.normalize(body)

    @app.get("/api/optimizations/{opt_id}/archive")
    def optimization_archive(opt_id: str):
        with manager.lock:
            directory = manager.optimization_directory(opt_id)
            target = directory / "export.pybert_opt"
            save_optimization(directory, target)
        return FileResponse(target, filename=f"{opt_id}.pybert_opt")

    @app.post("/api/optimization-references", status_code=201)
    async def optimization_open(request: Request):
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_FILE_BYTES:
                raise ValueError("Optimization archive exceeds 256 MiB.")
        return manager.open_optimization(bytes(content))

    @app.get("/api/optimizations/{opt_id}/pulse")
    def optimization_pulse(opt_id: str, candidate: str = ""):
        import numpy as np

        record = manager.optimization(opt_id)
        if record["status"] != "succeeded":
            raise ValueError("Incomplete/failed optimization pulse cannot be published as success.")
        with np.load(manager.optimization_directory(opt_id) / "arrays.npz", allow_pickle=False) as arrays:
            rows = record["candidates"]
            row = next((row for row in rows if row["candidate_id"] == (candidate or record["selected_candidate_id"])), None)
            if not row or row["availability"] != "available":
                raise ValueError("Candidate unavailable.")
            pulse = arrays[row["arrays_prefix"] + "_pulse"]
            # Each candidate can have a different producer length. Native sampling interval, no resampling.
            axis = arrays[row["arrays_prefix"] + "_t_ns"]
            return {"opt_id": record["opt_id"], "candidate": row, "selected": row["candidate_id"] == record["selected_candidate_id"],
                    "x_ns": axis.tolist(), "pulse": pulse.tolist(), "channel_x_ns": arrays["channel_t_ns"].tolist(),
                    "channel_pulse": arrays["p_chnl"].tolist(),
                    "cursor_ns": arrays["curs_ix"].tolist() if row["candidate_id"] == record["selected_candidate_id"] else [],
                    "cursor_V": arrays["curs_amp"].tolist() if row["candidate_id"] == record["selected_candidate_id"] else [],
                    "clocks": arrays["clocks_tune"].tolist() if row["candidate_id"] == record["selected_candidate_id"] else [],
                    "nspui": record["requested_input"]["nspui"], "unit": "native pulse V; MMSE cursor-normalized", "clock_basis": "optimization sampling marks, not recovered CDR"}

    @app.post("/api/resources")
    def upload_resource(request: dict):
        content = base64.b64decode(request["content_base64"], validate=True)
        with manager.lock:
            return manager.resources.add(request["name"], content, {"kind": "browser_upload"})

    @app.post("/api/resources/local")
    def local_resource(request: dict):
        with manager.lock:
            return manager.resources.local(request["path"])

    @app.post("/api/com", status_code=202)
    def compute_com(request: dict):
        if set(request) - {"thru_resource_id", "config_resource_id", "parameter_source", "parent_run_id", "thru_reference", "config_reference"}:
            raise ValueError("COM accepts its own THRU/config/default selection only; current time-domain EQ/noise/bitrate fields are not COM inputs.")
        if request.get("parent_run_id"):
            manager.directory(request["parent_run_id"])
        return manager.start("com", request)

    @app.get("/api/com/{com_id}")
    def com_result(com_id: str):
        task = manager.get(com_id)
        if task["operation"] != "com":
            raise KeyError("Not a COM task")
        def saved(name):
            if not task["worker_exited"]:
                return None, "waiting_for_exit"
            path = manager.tasks[com_id]["directory"] / name
            if not path.exists():
                return None, "not_produced"
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None, "unreadable"
            if not isinstance(record, dict) or record.get("com_id") != com_id:
                return None, "identity_mismatch"
            return record, "available"

        source, source_status = saved("com-input.json")
        result, result_status = saved("com.json")
        # Preserve the successful result's existing top-level fields for API callers.
        payload = dict(result if task["state"] == "succeeded" and result else task)
        payload.update(task=task, saved_input=source, saved_detail_status={"input": source_status, "result": result_status})
        return payload

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str):
        return manager.get(task_id)

    @app.post("/api/tasks/{task_id}/cancel")
    def cancel(task_id: str):
        return manager.cancel(task_id)

    @app.get("/api/runs/{run_id}")
    def manifest(run_id: str):
        return manager.manifest(run_id)

    @app.post("/api/references", status_code=201)
    async def open_reference(request: Request, name: str, trusted: bool = False):
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_FILE_BYTES:
                raise ValueError("Result file exceeds 256 MiB; existing state retained.")
        with manager.lock:
            return manager.references.add(bytes(content), name, trusted)

    @app.post("/api/references/{record_id}/remove")
    def remove_reference(record_id: str):
        with manager.lock:
            manager.references.remove(record_id)
        return {"removed": record_id}

    @app.get("/api/runs/{run_id}/replay-input")
    def replay_input(run_id: str):
        run = manager.manifest(run_id)
        if run.get("legacy"):
            raise ValueError("Legacy results contain no complete original inputs/axes; cannot restore a runnable draft.")
        return {"config": run["requested_input"], "runtime_extensions": run.get("runtime_extensions", {}),
                "resource_bindings": run.get("resource_bindings", {}), "source_record_id": run_id,
                "replay_guard": {"version": 1, "source_run_id": run["run_id"], "resource_hash": run.get("resource_hash"),
                                 "resources": [{key: row.get(key) for key in ("field", "index", "sha256")} for row in run.get("resources", [])]},
                "expected_resources": [{key: row.get(key) for key in ("field", "index", "sha256", "original_name")} for row in run.get("resources", [])]}

    def subfunction_snapshot(run_id, directory):
        saved = directory / "archive.json"
        if saved.exists():
            return read_json(saved.read_bytes()).get("subfunctions", {})
        run = manager.manifest(run_id)
        plan = run.get("execution_strategy", {}).get("deferred_com")
        linked = [key for key, entry in manager.tasks.items() if entry["data"].get("parent_run_id") == run["run_id"]]
        if plan and plan["com_id"] not in linked:
            linked.append(plan["com_id"])
        records = {}
        for key in linked:
            if key not in manager.tasks:
                records[key] = {"availability": "not available in this session", "planned_id": key}
                continue
            task = manager.get(key)
            files = {}
            for name in ("com-input.json", "com.json", "terminal.json"):
                path = manager.tasks[key]["directory"] / name
                if not task["worker_exited"]:
                    files[name] = {"availability": "waiting_for_exit"}
                elif not path.exists():
                    files[name] = {"availability": "not_produced"}
                else:
                    try:
                        record = read_json(path.read_bytes())
                        if name != "terminal.json" and record.get("com_id") != key:
                            raise ValueError("identity mismatch")
                        files[name] = {"availability": "available", "record": record}
                    except (ValueError, OSError) as err:
                        files[name] = {"availability": "unreadable", "reason": str(err)}
            records[key] = {"availability": "captured", "task": task, "files": files}
        return {"captured_at": time.time(), "linked_tasks": records, "policy": "snapshot at save; no calculation, no parent mutation"}

    @app.get("/api/runs/{run_id}/archive")
    def archive(run_id: str):
        with manager.lock:
            directory = manager.directory(run_id)
            target = directory / "export.pybert_run"
            save_archive(directory, target, subfunction_snapshot(run_id, directory))
        return FileResponse(target, filename=f"{run_id}.pybert_run")

    @app.get("/api/runs/{run_id}/legacy-report")
    def legacy_status(run_id: str):
        return legacy_report(manager.directory(run_id))

    @app.get("/api/runs/{run_id}/legacy")
    def legacy_save(run_id: str):
        with manager.lock:
            directory = manager.directory(run_id)
            target = directory / "export.pybert_data"
            export_legacy(directory, target)
        return FileResponse(target, filename=f"{run_id}.pybert_data")

    @app.get("/api/runs/{run_id}/plots/{plot_id}")
    def plot(run_id: str, plot_id: str):
        return {**plot_payload(manager.directory(run_id), plot_id), "record_id": run_id}

    @app.get("/api/runs/{run_id}/raw")
    def raw(run_id: str):
        return FileResponse(manager.directory(run_id) / "arrays.npz", filename=f"{run_id}.npz")

    @app.get("/plotly.js")
    def plotly():
        from fastapi.responses import Response

        return Response(
            get_plotlyjs(), media_type="application/javascript", headers={"Cache-Control": "public, max-age=3600"}
        )

    app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="workbench")
    return app
