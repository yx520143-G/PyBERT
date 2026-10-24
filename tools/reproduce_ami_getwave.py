"""One frozen direct native call; preserve the native failure without repairing it."""

import json
import time
import traceback
from pathlib import Path

import numpy as np

from pybert.models import bert
from pybert.pybert import PyBERT
from pybert.web.archive import json_bytes, sha256
from pybert.web.data import source_identity

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "docs/webui/issue10/evidence/native-getwave-v1"
    out.mkdir(parents=True, exist_ok=False)
    request = ROOT / "docs/webui/issue10/fixtures/v1/A-NRZ-Native-GetWave.yaml"
    (out / "before.json").write_bytes(json_bytes({"source": source_identity(), "request_sha256": sha256(request.read_bytes()), "main_calls_planned": 1}))
    arrays, calls = {}, []
    original = bert.run_ami_model

    def capture(*args, **kwargs):
        row = {"dll": args[0], "GetWave": args[2], "ui_s": args[3], "ts_s": args[4], "parameters": args[1].input_ami_params}
        calls.append(row)
        for name, value in (("input_h", args[5]), ("input_x", args[6])):
            arrays[name] = np.asarray(value).copy()
        result = original(*args, **kwargs)
        for name, value in zip(("y", "clocks", "h", "out_h"), result[:4]):
            arrays[name] = np.asarray(value).copy()
        row.update(message=result[4], params_out=result[5], returned=True)
        return result

    bert.run_ami_model = capture
    p = PyBERT(run_simulation=False, gui=False)
    started = time.time()
    report = {"main_calls": 0, "fixture": str(request), "calls": calls}
    try:
        p.load_configuration(request)
        p.rx_use_clocks = True
        report["main_calls"] = 1
        bert.my_run_simulation(p, initial_run=True, update_plots=False, observations={})
        report.update(status=p.status)
    except Exception as error:
        report.update(status="failed", error=str(error), error_type=type(error).__name__, traceback=traceback.format_exc())
    finally:
        report.update(elapsed_s=time.time() - started, console=p.console_log)
        np.savez_compressed(out / "arrays.npz", **arrays)
        (out / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({k: v for k, v in report.items() if k not in ("calls", "console", "traceback")}))


if __name__ == "__main__":
    main()
