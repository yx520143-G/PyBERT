"""Bounded real-view acceptance helpers; server requests still come from the browser."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LOCAL = OUT / "local"
DEPENDENCIES = Path(r"C:\Users\yx\.codex\worktrees\pybert-webui-design\serial-bus-simulator")
BASE = "16ee4f406146a2d92fd1190b65913e24a8730b8b"
PORT = 8798
sys.path[:0] = [str(ROOT / "src"), str(DEPENDENCIES / "PyAMI/src"), str(DEPENDENCIES / "PyChOpMarg/src")]
sys.dont_write_bytecode = True
os.environ["ETS_TOOLKIT"] = "null"
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(directory, *args):
    return subprocess.check_output(["git", "-C", str(directory), *args], text=True).strip()


def provenance():
    import pybert
    import pyibisami
    import pychopmarg
    import pybert.web.worker

    modules = {}
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] in ("pybert", "pyibisami", "pychopmarg"):
            file = getattr(module, "__file__", None)
            if file and Path(file).is_file():
                modules[name] = {"path": str(Path(file).resolve()), "sha256": digest(file)}
    assert Path(pybert.__file__).resolve().is_relative_to(ROOT / "src")
    assert Path(pyibisami.__file__).resolve().is_relative_to(DEPENDENCIES / "PyAMI/src")
    assert Path(pychopmarg.__file__).resolve().is_relative_to(DEPENDENCIES / "PyChOpMarg/src")
    dependencies = {}
    for name in ("PyAMI", "PyChOpMarg"):
        actual = git(DEPENDENCIES / name, "rev-parse", "HEAD")
        assert actual == git(ROOT, "rev-parse", f"{BASE}:{name}")
        assert not git(DEPENDENCIES / name, "status", "--porcelain")
        dependencies[name] = actual
    return {"pid": os.getpid(), "python": sys.executable, "head": git(ROOT, "rev-parse", "HEAD"),
            "dependencies": dependencies, "modules": modules,
            "packages": {name: importlib.metadata.version(name) for name in
                         ("numpy", "scipy", "traits", "pyibis-ami", "pychopmarg", "fastapi", "uvicorn", "plotly")}}


def verify_sources():
    frozen = json.loads((OUT / "freeze.json").read_text(encoding="utf-8"))
    for file, expected in frozen["source_hashes"].items():
        assert digest(file) == expected, file


def audited_worker(task_id, operation, request, directory, cancel_event, connection):
    from pybert.web.worker import run_worker

    verify_sources()
    write(Path(directory) / "loaded-modules.json", provenance())
    if operation == "run":
        config = request["config"]
        assert not any(config[k] for k in ("enable_com", "rx_use_viterbi", "tx_use_ami", "rx_use_ami"))
        assert config["inter_sel"] == "native" and config["seed"] == 1
        assert config["nbits"] == 15000 and config["nspui"] == 32
    run_worker(task_id, operation, request, directory, cancel_event, connection)


def freeze():
    assert git(ROOT, "rev-parse", "HEAD") == BASE
    assert not (OUT / "freeze.json").exists()
    source_hashes = {}
    for directory in (ROOT / "src/pybert", DEPENDENCIES / "PyAMI/src", DEPENDENCIES / "PyChOpMarg/src"):
        for file in sorted(directory.rglob("*")):
            if file.is_file() and file.suffix in (".py", ".js", ".html", ".css"):
                source_hashes[str(file)] = digest(file)
    fixtures = ROOT / "docs/webui/issue2/fixtures"
    for name in ("F-NRZ-01", "F-PAM4-01"):
        for suffix in (".yaml", ".json"):
            file = fixtures / (name + suffix)
            source_hashes[str(file)] = digest(file)
    source_hashes[str(Path(__file__).resolve())] = digest(__file__)
    write(OUT / "freeze.json", {"base": BASE, "source_hashes": source_hashes, "provenance": provenance(),
          "plan": {"web_Main": 3, "direct_Main": 2, "COM": 0, "optimization": 0, "real_AMI": 0,
                   "A": "F-NRZ-01 browser Run", "B": "A with only peak_mag changed from 1.7 to 4.0",
                   "C": "F-PAM4-01 browser Run", "direct": ["A", "C"]}})
    print("Frozen", len(source_hashes), "sources/inputs", flush=True)


def serve():
    import uvicorn
    from pybert.web.server import create_app
    from pybert.web.tasks import Tasks

    verify_sources()
    write(OUT / "server-provenance.json", provenance())
    uvicorn.run(create_app(Tasks(LOCAL / "server", worker=audited_worker)), host="127.0.0.1", port=PORT)


def capture(name):
    def get(route):
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/{route}", timeout=30) as response:
            return response.read()

    state = json.loads(get("state"))
    assert not state["active_task_id"] and state["runs"]
    task_id = state["runs"][-1]["run_id"]
    task = json.loads(get(f"tasks/{task_id}"))
    assert task["state"] == "succeeded" and task["worker_exited"] and task["exitcode"] == 0
    directory = LOCAL / name
    directory.mkdir(parents=True, exist_ok=False)
    record = get(f"runs/{task_id}")
    (directory / "manifest.json").write_bytes(record)
    (directory / "arrays.npz").write_bytes(get(f"runs/{task_id}/raw"))
    (directory / "result.pybert_run").write_bytes(get(f"runs/{task_id}/archive"))
    (directory / "replay-input.json").write_bytes(get(f"runs/{task_id}/replay-input"))
    write(directory / "task.json", task)
    for filename in ("loaded-modules.json", "terminal.json", "request.json"):
        source = LOCAL / "server" / task_id / filename
        if source.exists():
            (directory / filename).write_bytes(source.read_bytes())
    manifest = json.loads(record)
    write(OUT / f"{name}-capture.json", {"task_id": task_id, "input_hash": manifest["input_hash"],
          "input_identity_hash": manifest["input_identity_hash"], "plot_count": len(manifest["plots"]),
          "files": {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)} for p in directory.iterdir() if p.is_file()}})
    print(name, task_id, "captured", flush=True)


def direct(name):
    import numpy as np
    from pybert.pybert import PyBERT
    from pybert.models.bert import my_run_simulation
    from pybert.web.config import snapshot, input_hash
    from pybert.web.data import collect

    verify_sources()
    assert name in ("A", "C")
    directory = LOCAL / f"direct-{name}"
    directory.mkdir(parents=True, exist_ok=False)
    saved = LOCAL / name
    web_manifest = json.loads((saved / "manifest.json").read_text(encoding="utf-8"))
    fixture = "F-NRZ-01" if name == "A" else "F-PAM4-01"
    report = {"case": name, "main_attempts": 0, "passed": False, "provenance": provenance()}
    start = time.perf_counter()
    try:
        p = PyBERT(run_simulation=False, gui=False)
        p.load_configuration(ROOT / f"docs/webui/issue2/fixtures/{fixture}.yaml")
        effective = snapshot(p)
        assert input_hash(effective) == web_manifest["input_hash"]
        observations, decoding = {}, {}
        report["main_attempts"] = 1
        my_run_simulation(p, initial_run=True, update_plots=True, observations=observations, decoding=decoding)
        assert p.status == "Ready."
        collect(p, observations, directory, {"run_id": f"direct-{name}", "input_hash": input_hash(effective),
                "requested_input": effective, "effective_input": effective, "draft_revision": 0}, decoding=decoding)
        with np.load(directory / "arrays.npz", allow_pickle=False) as a, np.load(saved / "arrays.npz", allow_pickle=False) as b:
            assert set(a.files) == set(b.files)
            report["arrays"] = [{"field": key, "dtype": str(a[key].dtype), "shape": list(a[key].shape),
                "exact": a[key].dtype == b[key].dtype and a[key].shape == b[key].shape and a[key].tobytes() == b[key].tobytes()}
                for key in a.files]
        native_manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        a, b = dict(native_manifest["summary"]), dict(web_manifest["summary"])
        a.pop("performance_Msamples_per_min", None)
        b.pop("performance_Msamples_per_min", None)
        report["summary_exact_excluding_performance"] = a == b
        report["window_exact"] = native_manifest["window"] == web_manifest["window"]
        report["passed"] = all(row["exact"] for row in report["arrays"]) and a == b and report["window_exact"]
        assert report["passed"], "Numerical difference; stop and retain evidence"
    except BaseException as error:
        report.update(error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        raise
    finally:
        report["elapsed_seconds"] = time.perf_counter() - start
        write(OUT / f"{name}-direct-comparison.json", report)
    print(name, "exact arrays", len(report["arrays"]), flush=True)


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "freeze":
        freeze()
    elif action == "serve":
        serve()
    elif action == "capture":
        capture(sys.argv[2])
    elif action == "direct":
        direct(sys.argv[2])
    else:
        raise SystemExit("freeze, serve, capture CASE or direct CASE required")
