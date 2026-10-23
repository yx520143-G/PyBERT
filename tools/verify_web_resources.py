"""Serial fixed-original engine vs resource worker, plus independent saved-data checks."""

import copy
import importlib.util
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from pybert.web.config import input_hash, load_config, snapshot
from pybert.web.data import collect
from pybert.web.tasks import Tasks
from pybert.utility import safe_log10
from freeze_web_resource_execution import ROOT, FIX, OUT, sha
from verify_web_numerics import compare
from verify_web_analysis import verify as independent_analysis
from pybert.web.resource_data import annotate_interference


def load_original(name, filename, output):
    path = output / filename
    path.write_bytes((OUT / ("native-" + name.replace("/", "_") + ".txt")).read_bytes())
    qualified = "pybert.models.issue4_reference_bert" if "models/bert" in name else "pybert.issue4_reference_pybert"
    spec = importlib.util.spec_from_file_location(qualified, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reference(config, output, bert, model):
    p = model.PyBERT(run_simulation=False, gui=False)
    load_config(p, config, snapshot(p))
    assert input_hash(snapshot(p)) == input_hash(config)
    observations, channel, contributions = {}, {}, {}
    points = iter(("chnl", "tx", "ctle", "dfe"))

    def profile(frame, event, result):
        if event != "return" or frame.f_back is None:
            return
        caller = frame.f_back
        if frame.f_code.co_name == "trim_impulse" and caller.f_code.co_name == "calc_chnl_h" and "fext_ntwk" in caller.f_locals:
            i = len(p.fext_h)
            channel.update({f"fext_{i}_h": result[0], f"fext_{i}_start_ix": result[1], f"fext_{i}_H": caller.f_locals["fext_H"]})
        if frame.f_code.co_name == "convolve" and caller.f_code.co_name == "my_run_simulation" and "h_fext" in caller.f_locals:
            contributions[f"fext_{len(contributions)}_voltage"] = result[:len(caller.f_locals["x"])]
        if frame.f_code.co_name == "calc_jitter" and caller.f_code.co_name == "my_run_simulation":
            local = caller.f_locals
            observations["source"] = {k: local[k] for k in (
                "x", "ideal_signal", "ideal_xings", "ideal_xings_jit", "xing_mask", "ui", "nspui", "nui", "eye_uis",
                "pattern_len", "rel_thresh", "decision_scaler", "mod_type", "xing_min_t")}
            observations["source"].update(noise_total=local["noise"], fext_count=len(p.fext_h), **channel, **contributions)
            observations[next(points)] = {"ofst": local["ofst"], "actual_xings": local["actual_xings"],
                "actual_xings_jit": local["actual_xings_jit"], "t_jitter": result[1], "bin_centers": result[15],
                "spectrum_freqs": result[12], "tie": result[0], "tie_ind": result[8], "valid": True}
    sys.setprofile(profile)
    try:
        bert.my_run_simulation(p, initial_run=True, update_plots=False)
    finally:
        sys.setprofile(None)
    assert p.status == "Ready.", p.status
    identity = {"run_id": "fixed-original-reference", "requested_input": config, "effective_input": snapshot(p) | {"decision_scaler": config["decision_scaler"]},
                "input_hash": input_hash(config)}
    # Use the input snapshot, not the trained AGC state, as the reference input identity.
    identity["effective_input"] = copy.deepcopy(config)
    return collect(p, observations, output, identity)


def saved_checks(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with np.load(directory / "arrays.npz") as stored:
        arrays = {key: stored[key].copy() for key in stored.files}
    expected_windows = {}
    fields = ["noise", "context.source.x", "context.source.noise_total"]
    t, indices = arrays["t"], arrays["waveform_indices"]
    for field in fields:
        expected_windows[field] = dict(scope="full_record", source_field=field, time_axis="t", start_index=0, stop_index=len(t),
            sample_count=len(t), ignore_samps=0, ignore_until_s=float(t[0]), start_s=float(t[0]), stop_s_exclusive=float(t[-1]+t[1]-t[0]))
        name="noise_base" if field=="noise" else field.rsplit(".",1)[-1]
        for suffix in ("x","y"):
            expected_windows[f"display.wave.{name}.{suffix}"] = dict(scope="display_projection",source_field=field,time_axis="t",
                start_index=int(indices[0]),stop_index=int(indices[-1])+1,sample_count=len(indices),projection_index_field="waveform_indices",
                start_s=float(t[indices[0]]),stop_s_inclusive=float(t[indices[-1]]))
    independent = independent_analysis(arrays, manifest, expected_windows=expected_windows)
    raw,display = independent["raw_checks"],independent["display_checks"]
    checks = []
    def check(name, actual, expected, rtol=1e-10, atol=1e-10):
        a, b = np.asarray(actual), np.asarray(expected)
        good = a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all() and np.allclose(a,b,rtol=rtol,atol=atol)
        checks.append({"check": name, "passed": bool(good), "rtol":rtol, "atol":atol})
    for point in ("chnl", "tx", "tx_out", "ctle", "ctle_out", "ffe", "ffe_out", "dfe", "dfe_out"):
        for suffix in ("h", "s", "p", "H"):
            key = point + "_" + suffix
            expected = 20*safe_log10(abs(arrays[key][1:])) if suffix == "H" else arrays[key]
            x = arrays["f"][1:] / 1e9 if suffix == "H" else arrays["t_ns_chnl"] if point == "chnl" or point.endswith("out") else arrays["t"][:len(expected)]*1e9
            check(key+" display values", arrays[f"display.{key}.y"], expected)
            check(key+" display axis", arrays[f"display.{key}.x"], x)
    indices = arrays["waveform_indices"]
    check("actual source x projection", arrays["display.wave.x.y"], arrays["context.source.x"][indices])
    check("base noise projection", arrays["display.wave.noise_base.y"], arrays["noise"][indices])
    check("total interference projection", arrays["display.wave.noise_total.y"], arrays["context.source.noise_total"][indices])
    check("no FEXT: total equals self.noise", arrays["context.source.noise_total"], arrays["noise"],0,0)
    return {"analysis_raw":raw, "analysis_display":display, "additional_display":checks,
            "passed": all(row["passed"] for row in (*raw,*display,*checks))}


def main():
    if len(sys.argv)>1 and sys.argv[1]=="--saved-report":
        return recheck_saved(Path(sys.argv[2]))
    frozen = json.loads((FIX / "frozen-manifest.json").read_text(encoding="utf-8"))
    assert all(sha(FIX/k)==v for k,v in frozen["files"].items())
    out = OUT / time.strftime("numeric-%Y%m%d-%H%M%S")
    out.mkdir()
    report = {"frozen_manifest_sha256":sha(FIX/"frozen-manifest.json"), "execution_freeze_sha256":sha(OUT/"execution-freeze-v1.json"),
              "actual_sources": {str(p.relative_to(ROOT)):sha(p) for p in [*sorted((ROOT/"src/pybert").rglob("*.py")),Path(__file__)]},
              "cases":[], "excluded_with_evidence": {"F4-L0-OFF/ON,F4-L1-OFF/ON":"native-port-boundary-v2.json; pending PM native blocker disposition",
                                                     "F4-COM-DEFAULT":"BLOCKED_BUDGET / NOT_EXECUTED"}}
    (out/"execution-snapshot.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    original_bert=load_original("src/pybert/models/bert.py","original_bert.py",out)
    original_model=load_original("src/pybert/pybert.py","original_pybert.py",out)
    names = sys.argv[1:] or ["F4-SINGLE-NRZ","F4-SINGLE-PAM4","F4-CASCADE-AB","F4-CASCADE-BA","F4-PACKAGE","F4-DUO"]
    for name in names:
        config=json.loads((FIX/f"{name}.json").read_text(encoding="utf-8"))
        entry={"case":name,"passed":False,"requested_input_hash":input_hash(config)}
        directory=out/name;directory.mkdir()
        direct=directory/"direct";direct.mkdir()
        try:
            print(name,"fixed original engine",flush=True)
            started=time.perf_counter()
            a=reference(config,direct,original_bert,original_model)
            entry["direct_elapsed_s"]=time.perf_counter()-started
            manager=Tasks(directory/"worker")
            bindings={}
            for field in ("ch_file","ch_files"):
                if config["inter_sel"]==("single" if field=="ch_file" else "multiple"):
                    refs=config[field] if field=="ch_files" else [config[field]]
                    ids=[manager.resources.local(ref)["resource_id"] for ref in refs]
                    bindings[field]=ids if field=="ch_files" else ids[0]
            print(name,"fresh spawn adapter",flush=True)
            task=manager.start("run",{"config":config,"input_hash":input_hash(config),"resource_bindings":bindings})
            manager.tasks[task["task_id"]]["done"].wait()
            final=manager.get(task["task_id"]);entry["task"]=final
            if final["state"]!="succeeded":
                raise RuntimeError(final.get("error",final["state"]))
            worker=manager.directory(task["task_id"])
            entry["worker_directory"]=str(worker)
            entry["raw_comparison"]=compare(direct,worker,float(np.load(worker/"arrays.npz")["context.source.ui"]))
            # Apply the same frozen threshold separately to real and imaginary components.
            with np.load(direct/"arrays.npz") as x,np.load(worker/"arrays.npz") as y:
                entry["complex_components"]=[{"field":key,"component":part,"passed":bool(np.allclose(getattr(x[key],part),getattr(y[key],part),rtol=1e-10,atol=1e-12))}
                    for key in x.files if np.iscomplexobj(x[key]) for part in ("real","imag")]
            b=json.loads((worker/"manifest.json").read_text(encoding="utf-8"))
            entry["window_equal"]=a["window"]==b["window"]
            entry["summary_equal"]={k:a["summary"][k]==v for k,v in b["summary"].items() if k!="performance_Msamples_per_min"}
            entry["independent_saved_data"]=saved_checks(worker)
            entry["passed"]=all(r["passed"] for r in entry["raw_comparison"]+entry["complex_components"]) and entry["window_equal"] and all(entry["summary_equal"].values()) and entry["independent_saved_data"]["passed"]
            entry["raw_files"]=[{"path":str(p),"sha256":sha(p),"bytes":p.stat().st_size} for p in (direct/"arrays.npz",worker/"arrays.npz")]
        except Exception as err:
            entry.update(error=str(err),traceback=traceback.format_exc())
        report["cases"].append(entry)
        (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(name,"passed",entry["passed"],entry.get("error",""),flush=True)
    print("report",out/"report.json",flush=True)
    if not all(row["passed"] for row in report["cases"]):
        raise SystemExit(1)


def recheck_saved(path):
    """Retain original failure/raw; metadata-only rebuild never reruns an engine."""
    old=json.loads(path.read_text(encoding="utf-8"))
    dest=OUT/time.strftime("saved-resource-check-%Y%m%d-%H%M%S");dest.mkdir()
    report={"source_report":str(path),"source_report_sha256":sha(path),"main_simulation_performed":False,
            "method":"same saved raw bytes; annotate interference identity/windows and run independent expectations",
            "actual_sources":{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/"src/pybert/web/resource_data.py",ROOT/"tools/verify_web_analysis.py")},"cases":[]}
    for previous in old["cases"]:
        entry={"case":previous["case"],"passed":False}
        try:
            for side,source in (("direct",path.parent/previous["case"]/"direct"),("worker",Path(previous["worker_directory"]))):
                target=dest/previous["case"]/side;target.mkdir(parents=True)
                shutil.copyfile(source/"arrays.npz",target/"arrays.npz")
                manifest=json.loads((source/"manifest.json").read_text(encoding="utf-8"))
                with np.load(target/"arrays.npz") as values:
                    arrays={key:values[key] for key in values.files}
                    annotate_interference(arrays,manifest)
                (target/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
                entry[side+"_raw_unchanged"]=sha(source/"arrays.npz")==sha(target/"arrays.npz")
            worker=dest/previous["case"]/"worker"
            entry["independent_saved_data"]=saved_checks(worker)
            entry["original_raw_comparison_passed"]=all(row["passed"] for row in previous["raw_comparison"]+previous["complex_components"])
            entry["original_nonperformance_summary_equal"]=all(previous["summary_equal"].values())
            entry["passed"]=entry["independent_saved_data"]["passed"] and entry["original_raw_comparison_passed"] and entry["original_nonperformance_summary_equal"] and entry["direct_raw_unchanged"] and entry["worker_raw_unchanged"]
        except Exception as err:
            entry.update(error=str(err),traceback=traceback.format_exc())
        report["cases"].append(entry)
    (dest/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"report":str(dest/"report.json"),"cases":[{"case":c["case"],"passed":c["passed"],"error":c.get("error")} for c in report["cases"]]}))
    if not all(row["passed"] for row in report["cases"]):
        raise SystemExit(1)


if __name__=="__main__":
    main()
