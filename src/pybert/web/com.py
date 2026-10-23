"""The independent native COM tool; no time-domain EQ/configuration projection."""

import dataclasses
import hashlib
import itertools
import importlib.metadata
import json
import math
import os
from pathlib import Path

import numpy as np

from pybert.models.com import calc_com
from pybert.web.config import input_hash
from pybert.web.data import adapter_sha
from pybert.web.resources import digest

class ComCancelled(RuntimeError):
    pass


def plain(value):
    if dataclasses.is_dataclass(value):
        return plain(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def run_com(task_id, request, directory, cancelled, emit, errors=lambda: []):
    from skrf import Network
    from pychopmarg.config.ieee_8023dj import IEEE_8023dj
    from pychopmarg.excel import get_com_params
    from pychopmarg.utility.general import mk_combs

    rows = request["frozen_resources"]
    thru = next(row for row in rows if row["field"] == "com_thru")
    cfg = next((row for row in rows if row["field"] == "com_cfg_file"), None)
    for row in rows:
        if digest(Path(row["worker_path"])) != row["sha256"]:
            raise ValueError("COM resource hash mismatch.")
    if thru["format"] != ".s4p":
        raise ValueError("COM accepts exactly one actual .s4p THRU resource.")
    ntwk = Network(thru["worker_path"])
    if ntwk.nports != 4 or not np.isfinite(ntwk.s).all():
        raise ValueError("COM THRU content is not a finite 4-port network.")
    if cfg and cfg["format"] not in (".xls", ".xlsx"):
        raise ValueError("COM configuration requires .xls/.xlsx; no fallback to defaults.")
    if not cfg and request.get("parameter_source") != "IEEE_8023dj defaults":
        raise ValueError("Explicitly select IEEE_8023dj defaults or a real spreadsheet.")
    cp = get_com_params(Path(cfg["worker_path"])) if cfg else IEEE_8023dj
    grids = [mk_combs([trip]) for trip in zip(cp.tx_taps_min, cp.tx_taps_max, cp.tx_taps_step)]
    filtered = [np.array(row).ravel() for row in itertools.product(*grids)
                if 1 - abs(np.array(row).ravel()).sum() >= cp.c0_min]
    count = len(filtered)
    if not any(np.allclose(row, 0) for row in filtered):
        count += 1
    budget = count * len(cp.g_DC) * len(cp.g_DC2) * (len(cp.zp_cases) if cp.zp_cases else 1)
    params = plain(cp)
    source = {"kind": "spreadsheet" if cfg else "IEEE_8023dj defaults", "parameters": params,
              "parameters_sha256": input_hash(params), "full_search_fom_upper_bound": budget,
              "local_search": cp.local_search,
              "timing_search": cp.ts_srch_mode, "engine_processes": 1}
    manifest = {"com_id": task_id, "parent_run_id": request.get("parent_run_id"),
                "resources": rows, "parameter_source": source, "adapter_sha": adapter_sha(),
                "versions": {n: importlib.metadata.version(n) for n in ("pipbert", "pychopmarg", "numpy", "scipy")},
                "helper": "pybert.models.com.calc_com",
                "no_time_domain_settings_injected": True,
                "source_hashes": {str(Path(p)): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                                  (__file__, __import__("pybert.models.com", fromlist=["x"]).__file__,
                                   __import__("pychopmarg.com", fromlist=["x"]).__file__)}}
    Path(directory, "com-input.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if cancelled():
        raise ComCancelled("Cancelled before native COM call")
    emit("phase", phase="native COM helper (cancellation observed after return)")
    os.environ["PYCHOPMARG_PROCS"] = "1"
    value = calc_com(thru["worker_path"], cfg_file=cfg["worker_path"] if cfg else None)
    if errors():
        raise RuntimeError("Native COM ERROR output: " + "\n".join(errors()))
    if cancelled():
        raise ComCancelled("Cancelled after native COM returned; numerical value not published")
    if not isinstance(value, (int, float, np.number)) or not math.isfinite(value) or value == -999:
        raise ValueError(f"Native COM returned an invalid/sentinel value: {value}")
    manifest.update(state="succeeded", value_db=float(value), unit="dB")
    Path(directory, "com.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"com_id": task_id, "parent_run_id": request.get("parent_run_id"), "value_db": float(value)}
