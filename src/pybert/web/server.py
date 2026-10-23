"""Thin localhost HTTP boundary; no shared PyBERT instance in the server."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from plotly.offline import get_plotlyjs

from pybert import __version__
from pybert.web import NATIVE_SHA, PROTOTYPE_SHA, SCHEMA_VERSION
from pybert.web.data import adapter_sha, plot_payload
from pybert.web.tasks import BusyError, Tasks


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

    @app.get("/api/version")
    def version():
        return {
            "schema_version": SCHEMA_VERSION,
            "version": __version__,
            "adapter_sha": adapter_sha(),
            "native_sha": NATIVE_SHA,
            "prototype_sha": PROTOTYPE_SHA,
            "fork": "yx520143-G/PyBERT",
        }

    @app.post("/api/normalize")
    def normalize(request: dict):
        return manager.normalize(request)

    @app.post("/api/runs", status_code=202)
    def start_run(request: dict):
        if not all(key in request for key in ("config", "input_hash")):
            raise HTTPException(422, "Complete normalized config and input_hash are required.")
        return manager.start("run", request)

    @app.get("/api/state")
    def state():
        return manager.index()

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str):
        return manager.get(task_id)

    @app.post("/api/tasks/{task_id}/cancel")
    def cancel(task_id: str):
        return manager.cancel(task_id)

    @app.get("/api/runs/{run_id}")
    def manifest(run_id: str):
        return json.loads((manager.directory(run_id) / "manifest.json").read_text(encoding="utf-8"))

    @app.get("/api/runs/{run_id}/plots/{plot_id}")
    def plot(run_id: str, plot_id: str):
        return plot_payload(manager.directory(run_id), plot_id)

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
