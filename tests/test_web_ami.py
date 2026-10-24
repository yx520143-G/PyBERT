"""AMI boundary tests: resource identity and parser semantics, no numerical invocation."""

import copy
from pathlib import Path

import pytest
from pyibisami.ami.parser import AMIParamConfigurator

from pybert.web.ami import parameter_rows, bundle_file, schema, configure
from pybert.web.config import extensions, normalize, validate
from pybert.web.resources import Resources


def test_hierarchical_parser_metadata_and_setter():
    cfg = AMIParamConfigurator(Path("models/ibisami/example_rx.ami").read_text(encoding="utf-8"))
    rows = parameter_rows(cfg)
    assert len(rows) == 20
    debug = next(r for r in rows if r["path"] == ["Model_Specific", "debug", "dbg_enable"])
    assert debug["editable"] and debug["type"] == "Boolean" and debug["value"] is False
    info = next(r for r in rows if r["path"][-1] == "Init_Returns_Impulse")
    assert not info["editable"] and info["usage"] == "Info"
    cfg.set_param_val(["Model_Specific", "ctle_mode"], 1)
    assert cfg.fetch_param_val(["Model_Specific", "ctle_mode"]) == 1
    with pytest.raises(Exception):
        cfg.set_param_val(["Model_Specific", "ctle_mag"], 13)


@pytest.mark.parametrize("path", ["../escape.dll", "C:/model.dll", "/model.dll", "a//b", "a/./b"])
def test_bundle_rejects_unsafe_relative_paths(tmp_path, path):
    with pytest.raises(ValueError):
        Resources(tmp_path).model_bundle([(path, b"data")], {})


def test_bundle_directory_and_dependency_hash(tmp_path):
    resources = Resources(tmp_path)
    row = resources.model_bundle([("sub/example.ami", b"model"), ("sub/example.dll", b"binary")], {})
    bindings = {"rx_model_bundle": row["resource_id"]}
    bundle = resources.for_models({}, bindings)[0]
    assert bundle_file(bundle, "sub/example.ami").read_bytes() == b"model"
    bundle_file(bundle, "sub/example.dll").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        resources.for_models({}, bindings)


def test_unbound_active_never_runs(tmp_path):
    with pytest.raises(ValueError, match="unbound"):
        Resources(tmp_path).for_run({"rx_sel": "ibis"}, {})


def test_native_vs_getwave_disabled_ctle_file():
    defaults = normalize({"mode": "defaults"})["config"]
    c = copy.deepcopy(defaults)
    c.update(ctle_enable=False, ctle_sel="File", use_ctle_file=True)
    validate(c, defaults, execution=True)
    c.update(tx_eq_sel="IBIS-AMI", tx_sel="ibis", tx_use_ami=True, tx_use_getwave=True)
    with pytest.raises(ValueError, match="File"):
        validate(c, defaults, execution=True)
    c.update(rx_eq_sel="IBIS-AMI", rx_sel="ibis", rx_use_ami=True)
    validate(c, defaults, execution=True)


def test_dynamic_schema_and_fec_boundary():
    with pytest.raises(ValueError, match="hash"):
        schema({"rx": {"model_hash": "no"}})
    with pytest.raises(ValueError, match="unsupported_native_fec"):
        extensions({"version": 1, "values": {"rx_viterbi_fec": False}})


def test_changed_ibis_reference_cannot_execute_old_selection(tmp_path):
    from pybert.web.config import new_engine, snapshot

    resources = Resources(tmp_path)
    row = resources.model_bundle([("a.ibs", b"old"), ("b.ibs", b"new")], {})
    bundle = resources.for_models({}, {"rx_model_bundle": row["resource_id"]})
    p = new_engine()
    c = snapshot(p) | {"rx_ibis_file": "b.ibs", "rx_sel": "ibis"}
    runtime = {"version": 1, "values": {"ami_models": {"rx": {"model_hash": row["sha256"],
               "selection": {"comp": "c", "pin": "p", "mod": "m", "ibis_path": "a.ibs"}}}}}
    with pytest.raises(ValueError, match="conflicts"):
        configure(p, c, runtime, bundle, discover=True)


@pytest.mark.parametrize("field,value", [("nspui", 256), ("f_step", 1e-6)])
def test_ami_grid_budget_rejected_before_allocation(field, value):
    from pybert.web.config import new_engine
    from pybert.web.optimization import ami_plan

    p = new_engine()
    if field == "nspui":
        p.bit_rate = 250.0  # Native-valid rate/sample grid; no frequency vector is allocated.
    setattr(p, field, value)
    with pytest.raises(ValueError, match="grid budget"):
        ami_plan(p)


def test_missing_models_restore_input_but_cannot_run(tmp_path):
    from pybert.web.config import new_engine, snapshot

    p = new_engine()
    c = snapshot(p) | {"rx_sel": "ibis", "rx_eq_sel": "IBIS-AMI", "rx_use_ami": True, "rx_ibis_file": "missing.ibs"}
    runtime = {"version": 1, "values": {}}
    reports = configure(p, c, runtime, [], discover=True, allow_unbound=True)
    assert reports["rx"]["stage"] == "resource rebind required"
    with pytest.raises(ValueError, match="unbound"):
        configure(p, c, runtime, [])


def test_rx_ami_non_mmse_record_accepts_actual_rx_weight_shape():
    import json
    import numpy as np
    from pybert.web.config import input_hash
    from pybert.web.optimization import validate_record

    path = Path("docs/webui/issue10/evidence/numerics-20261024-155041/OPT-FIXED/worker")
    record = json.loads((path / "optimization.json").read_text(encoding="utf-8"))
    # Rx AMI uses cursor/ISI scoring with either request value, never the native MMSE branch.
    assert record["requested_input"]["rx_use_ami"]
    record["requested_input"]["use_mmse"] = False
    record["effective_input"]["use_mmse"] = False
    record["input_hash"] = input_hash(record["requested_input"])
    record["input_identity_hash"] = input_hash({"config": record["requested_input"], "runtime_extensions": record["runtime_extensions"],
                                                "resource_bindings": record["resource_bindings"]})
    with np.load(path / "arrays.npz", allow_pickle=False) as saved:
        validate_record(record, {key: saved[key] for key in saved.files})
