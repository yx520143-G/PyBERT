"""Freeze #10 fixtures without loading a binary or invoking an AMI function."""

import contextlib
import importlib.metadata
import io
import json
import os
import platform
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pybert
import pychopmarg
import pyibisami
from pyibisami.ami.config import mk_model
from pyibisami.ami.parser import AMIParamConfigurator
from pyibisami.ami.parameter import AMIParameter
from pyibisami.ibis.file import IBISModel

from pybert.utility.ibisami import resolve_ami_files
from pybert.web.archive import json_bytes, sha256
from pybert.web.config import input_hash, load_config, new_engine, snapshot, yaml_text
from pybert.web.data import source_identity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue10/fixtures/v1"


def tree(cfg, branch=None):
    branch = branch or cfg.ami_param_defs
    result = {}
    for name, value in branch.items():
        if isinstance(value, AMIParameter):
            result[name] = {key: getattr(value, key, None) for key in
                            ("pname", "ptype", "pusage", "pformat", "pvalue", "pmin", "pmax", "pvalues", "pdescription")}
        elif isinstance(value, dict):
            result[name] = tree(cfg, value)
        else:
            result[name] = value
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    tx = OUT / "tx-generated"
    tx.mkdir()
    source = ROOT / "PyAMI/tests/examples"
    shutil.copyfile(source / "example_tx.cpp.em", tx / "example_tx.cpp.em")
    cfg = runpy.run_path(str(source / "example_tx.py"))
    mk_model(cfg["ibis_params"], cfg["ami_params"], cfg["kFileBaseName"], cfg["kDescription"], str(tx))
    # Keep the original licensed binary in the ignored execution archive; no new binary in the PR.
    binary = ROOT / ".pybert-web/issue10-models/tx"
    binary.mkdir(parents=True)
    for file in tx.iterdir():
        shutil.copyfile(file, binary / file.name)
    shutil.copyfile(source / "example_tx_x86_amd64.dll", binary / "example_tx_x86_amd64.dll")
    models = {}
    for side, path in (("tx", binary / "example_tx.ibs"), ("rx", ROOT / "models/ibisami/example_rx.ibs")):
        ibis = IBISModel(str(path))
        dll, ami = resolve_ami_files(ibis, side == "tx")
        param = AMIParamConfigurator(Path(ami).read_text(encoding="utf-8"))
        models[side] = {"ibis": str(path), "selection": {k: getattr(ibis, k) for k in ("comp", "pin", "mod")},
                        "files": [{"path": str(p), "sha256": sha256(p.read_bytes()), "bytes": p.stat().st_size}
                                  for p in map(Path, (str(path), dll, ami))],
                        "tree": tree(param), "input_ami_params": param.input_ami_params,
                        "parser_warnings": param.ami_parsing_errors,
                        "Init_Returns_Impulse": param.fetch_param_val(["Reserved_Parameters", "Init_Returns_Impulse"]),
                        "GetWave_Exists": param.fetch_param_val(["Reserved_Parameters", "GetWave_Exists"])}
    cases = {}
    modes = [(tx, rx, "NRZ") for tx in ("Native", "Init", "GetWave") for rx in ("Native", "Init", "GetWave")]
    modes += [("Native", rx, "PAM4") for rx in ("Init", "GetWave")]
    for txmode, rxmode, modulation in modes:
        inherited = ROOT / f"docs/webui/issue2/fixtures/F-{modulation}-01.json"
        c = json.loads(inherited.read_text(encoding="utf-8"))
        c.update(rx_use_viterbi=False, enable_com=False)
        c = snapshot(load_config(new_engine(), c))
        runtime = {"version": 1, "values": {"rx_use_clocks": True, "ami_opt_trials": 4, "rlm": 1.0}}
        for side, mode in (("tx", txmode), ("rx", rxmode)):
            if mode == "Native":
                continue
            c.update({f"{side}_sel": "ibis", f"{side}_eq_sel": "IBIS-AMI", f"{side}_use_ami": True,
                      f"{side}_use_getwave": mode == "GetWave", f"{side}_ibis_file": models[side]["ibis"],
                      f"{side}_dll_file": models[side]["files"][1]["path"], f"{side}_ami_file": models[side]["files"][2]["path"]})
            if side == "rx":
                for field in ("dfe_tap_tuners", "ffe_tap_tuners"):
                    c[field] = [[False, *row[1:]] for row in c[field]]
        name = f"A-{modulation}-{txmode}-{rxmode}"
        request = {"config": c, "runtime_extensions": runtime, "resource_bindings": {}, "draft_revision": 0,
                   "input_hash": input_hash(c)}
        request["input_identity_hash"] = input_hash({k: request[k] for k in ("config", "runtime_extensions", "resource_bindings")})
        (OUT / f"{name}.json").write_bytes(json_bytes(request))
        (OUT / f"{name}.yaml").write_text(yaml_text(c, runtime), encoding="utf-8")
        cases[name] = {"request_sha256": sha256(json_bytes(request)), "tx_mode": txmode, "rx_mode": rxmode,
                       "source": str(inherited.relative_to(ROOT)), "source_sha256": sha256(inherited.read_bytes()),
                       "expected_clocks": "observe actual; do not infer validity from request", "bits_per_call": 0,
                       "response_probe_bits_per_call": 40, "window": "all raw arrays; native ignore/eye window, no retrospective selection"}
    manifest = {"version": 1, "before_first_numeric_call": True, "library_loads": 0, "Init_calls": 0, "GetWave_calls": 0,
                "base": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "models": models, "cases": cases,
                "legal_sources": {"rx": "repository models/ibisami (BSD-3-Clause root LICENSE; IBS copyright/disclaimer retained)",
                                  "tx": "pinned PyAMI tests/examples binary plus generated original model configuration/templates (PyAMI LICENSE retained)",
                                  "provenance": "public tracked educational example models; not vendor hardware qualification; no unknown vendor binary"},
                "environment": {"python": sys.executable, "version": sys.version, "platform": platform.platform(),
                                "modules": {m.__name__: m.__file__ for m in (pybert, pyibisami, pychopmarg)},
                                "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                                "PYTHONPATH": os.environ.get("PYTHONPATH")},
                "preimplementation_source_sha256": source_identity(),
                "tolerances": {"counts_indices_shapes_masks": "exact", "real_and_complex_raw": {"rtol": 1e-10, "atol": 1e-12},
                               "seconds_axes": {"rtol": 0, "atol": 1e-18}, "metadata": "exact except process/time/provenance paths; compare separately"},
                "budget": {"main_calls": 22, "direct": 11, "worker": 11, "chrome_extra_main_calls_max": 4,
                           "optimization_cases": ["no free dimensions: 1 evaluation", "rx ctle_mag Range 0..12 step6: 4 trials"],
                           "optuna_seed": 12345, "optuna_version": importlib.metadata.version("optuna"), "wall_per_task_s": 180,
                           "peak_rss_budget_bytes": 2 * 1024**3, "tools_parser_calls": "separate from library/Init/GetWave/probe/trial accounting"},
                "blocked_without_fixture": ["non-Windows platform", "GetWave-only model", "Ts4file model", "model with proven valid PAM4 returned clocks"],
                "faults": ["invalid/wrong-side/missing library", "model hash/path/value mismatch", "GetWave-only optimizer refused",
                           "ordinary RuntimeError failed", "cooperative and late cancel, exit/join, old success retained"],
                "policy": "Save actual source bytes and hashes before each batch. Preserve failures and costs. Native GetWave parser failure is a blocker, not permission to repair the engine."}
    (OUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"manifest": str(OUT / "manifest.json"), "sha256": sha256((OUT / "manifest.json").read_bytes()), "numeric_calls": 0}))


if __name__ == "__main__":
    main()
