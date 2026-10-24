"""AMI boundary tests: resource identity and parser semantics, no numerical invocation."""

import copy
from pathlib import Path

import pytest
from pyibisami.ami.parser import AMIParamConfigurator

from pybert.web.ami import parameter_rows, bundle_file, schema
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
