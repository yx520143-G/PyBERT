"""AMI boundary tests: resource identity and parser semantics, no numerical invocation."""

import copy
from pathlib import Path

import pytest
from pyibisami.ami.parser import AMIParamConfigurator

from pybert.web.ami import parameter_rows, bundle_file, schema, configure
from pybert.web.config import extensions, normalize, validate
from pybert.web.resources import Resources


def echo_frozen_models(task_id, operation, request, directory, cancel, pipe):
    pipe.send({"task_id": task_id, "kind": "terminal", "status": "succeeded",
               "result": {"fields": [r["field"] for r in request.get("frozen_resources", [])]}})
    pipe.close()


@pytest.mark.parametrize("mode", [{"mode": "load"}, {}])
def test_yaml_model_bindings_freeze_before_spawn_without_parsing_models(tmp_path, mode):
    import json
    from pybert.web.tasks import Tasks

    manager = Tasks(tmp_path, worker=echo_frozen_models)
    bundle = manager.resources.model_bundle([("model.ibs", b"inert test bytes")], {})
    extra = {"resource_bindings": {"rx_model_bundle": bundle["resource_id"]}}
    result = manager.normalize({**mode, "yaml": "# pybert-web-runtime-v1: " + json.dumps(extra) + "\n"})
    assert result["fields"] == ["rx_model_bundle"]


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
    mode = next(r for r in rows if r["path"][-1] == "ctle_mode")
    assert mode["values"] == [0, 1] and mode["list_tips"] == ["Off", "Manual"]
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


def test_native_reset_preserves_inactive_ami_side_initial_values():
    from pybert.web.config import new_engine
    from pybert.web.optimization import optimizer_action

    p = new_engine()
    p.trait_setq(rx_use_ami=True)
    runtime = {"version": 1, "values": {"ami_opt_trials": 4, "optimizer_values": {"tx": [0.] * 6, "ffe": [.25] * 100}}}
    result, _ = optimizer_action(p, runtime, "reset_eq")
    assert result["values"]["optimizer_values"]["ffe"] == [.25] * 100
    assert result["values"]["ami_opt_trials"] == 4


def test_tune_runtime_key_order_does_not_change_identity(monkeypatch):
    from pybert.web import optimization
    from pybert.web.config import new_engine, snapshot, input_hash

    config = snapshot(new_engine()) | {"rx_sel": "ibis"}
    runtime = {"version": 1, "values": {"rlm": .95, "ami_models": {}}}

    def reorder(_p, _config, values, _resources, **kwargs):
        values["version"] = values.pop("version")
        return {}

    monkeypatch.setattr(optimization, "configure", reorder)
    request = {"config": config, "input_hash": input_hash(config), "runtime_extensions": runtime, "resource_bindings": {}}
    request["input_identity_hash"] = input_hash({key: request[key] for key in ("config", "runtime_extensions", "resource_bindings")})
    optimization.prepare(request)


def test_ami_configure_endpoint_uses_single_slot_manager():
    from fastapi.testclient import TestClient
    from pybert.web.server import create_app

    class Manager:
        def normalize(self, request):
            return {"seen": request["mode"]}

    client = TestClient(create_app(Manager()))
    assert client.post("/api/normalize", json={"mode": "ami_configure"}).json() == {"seen": "ami_configure"}
    assert client.post("/api/normalize", json={"mode": "use_eq"}).status_code == 422


def test_replay_resource_models_and_channel_order_are_verified():
    from pybert.web.records import verify_replay_resources

    channel = {"field": "ch_files", "index": 0, "sha256": "a" * 64}
    model = {"field": "rx_model_bundle", "index": None, "sha256": "b" * 64}
    verify_replay_resources({"resources": [channel, model]}, [model, channel])
    with pytest.raises(ValueError, match="changed/missing"):
        verify_replay_resources({"resources": [channel, model]}, [channel])
    with pytest.raises(ValueError, match="changed/missing"):
        verify_replay_resources({"resources": [channel, model]}, [model, channel | {"index": 1}])


@pytest.fixture
def electrical_model(tmp_path, monkeypatch):
    from pybert.web import ami
    from pybert.web.config import new_engine, snapshot, load_config

    def setup(*, eq="Native", ts4=False, source=None, include_ts4=False, include_binary=True):
        files = [("example_rx.ibs", Path("models/ibisami/example_rx.ibs").read_bytes()),
                 ("example_rx.ami", source if isinstance(source, bytes) else
                  (source or Path("models/ibisami/example_rx.ami").read_text(encoding="utf-8")).encode())]
        if include_binary:
            files += [("example_rx" + suffix, b"inert library test bytes")
                      for suffix in ("_x86.dll", "_x86_amd64.dll", "_x86.so", "_x86_amd64.so")]
        if include_ts4:
            files.append(("ondie.s4p", b"inert dependency, no S-parameter computation"))
        resources = Resources(tmp_path)
        row = resources.model_bundle(files, {})
        bundle = resources.for_models({}, {"rx_model_bundle": row["resource_id"]})
        p = new_engine()
        config = snapshot(p) | {"rx_sel": "ibis", "rx_eq_sel": eq, "rx_use_ami": eq == "IBIS-AMI",
                                "rx_use_ts4": ts4, "rx_ibis_file": "example_rx.ibs"}
        load_config(p, config)
        return p, config, {"version": 1, "values": {}}, bundle

    def unavailable(_path):
        raise OSError("test-only missing optional DLL dependency")

    monkeypatch.setattr(ami, "AMIModel", unavailable)
    return setup


def test_electrical_native_does_not_require_optional_dll(electrical_model):
    p, config, runtime, bundle = electrical_model()
    report = configure(p, config, runtime, bundle, discover=True)
    assert p.rx_ibis_valid and not p.rx_use_ami and not p.rx_dll_valid
    assert report["rx"]["binary_load"] == "not requested"
    assert report["rx"]["parameters"] and runtime["values"]["ami_models"]["rx"]["parameter_model_hash"]


def test_requested_ami_still_requires_binary(electrical_model):
    inputs = electrical_model(eq="IBIS-AMI")
    with pytest.raises(OSError, match="test-only missing") as error:
        configure(*inputs, discover=True)
    assert inputs[1]["rx_eq_sel"] == "IBIS-AMI"
    assert error.value.ami_report["rx"]["stage"] == "binary load"


@pytest.mark.parametrize("eq,ts4", [("IBIS-AMI", False), ("Native", True)])
def test_required_ami_parser_failure_remains_fatal(electrical_model, eq, ts4):
    with pytest.raises(Exception) as error:
        configure(*electrical_model(eq=eq, ts4=ts4, source="invalid AMI source"), discover=True)
    assert error.value.ami_report["rx"]["stage"] == "AMI parser"


@pytest.mark.parametrize("source", ["invalid AMI source", b"\xff"])
def test_electrical_optional_parser_failure_is_reported(electrical_model, source):
    p, config, runtime, bundle = electrical_model(source=source)
    report = configure(p, config, runtime, bundle, discover=True)
    assert p.rx_ibis_valid and not p.rx_use_ami
    assert report["rx"]["ami_capability"]["status"] == "invalid"


def test_ts4_native_requires_parser_and_dependency_but_not_binary(electrical_model):
    source = Path("models/ibisami/example_rx.ami").read_text(encoding="utf-8").replace(
        "(Reserved_Parameters", '(Reserved_Parameters\n (Ts4file (Usage Info) (Type String) (Value "ondie.s4p"))')
    with pytest.raises(ValueError, match="Missing model dependency"):
        configure(*electrical_model(ts4=True, source=source), discover=True)
    p, config, runtime, bundle = electrical_model(ts4=True, source=source, include_ts4=True)
    report = configure(p, config, runtime, bundle, discover=True)
    assert p.rx_has_ts4 and p.rx_ami_valid and not p.rx_dll_valid
    assert report["rx"]["binary_load"] == "not requested"


@pytest.mark.parametrize("change", ["bundle_hash", "parameter_hash", "unknown_path", "invalid_value"])
def test_electrical_optional_ami_keeps_identity_and_parameter_validation(electrical_model, change):
    from traits.api import TraitError

    p, config, runtime, bundle = electrical_model()
    configure(p, config, runtime, bundle, discover=True)
    model = runtime["values"]["ami_models"]["rx"]
    if change == "bundle_hash":
        model["model_hash"] = "0" * 64
    elif change == "parameter_hash":
        model["parameter_model_hash"] = "0" * 64
    elif change == "unknown_path":
        model["parameters"][0]["path"] = ["Model_Specific", "unknown"]
    else:
        next(row for row in model["parameters"] if row["path"][-1] == "ctle_mag")["value"] = 13
    with pytest.raises(TraitError if change == "invalid_value" else ValueError):
        configure(p, config, runtime, bundle, discover=True)


def test_optional_invalid_ami_rebind_is_consumed_and_stable(electrical_model):
    p, config, runtime, bundle = electrical_model(source="invalid AMI source")
    configure(p, config, runtime, bundle, discover=True)
    runtime["values"]["ami_models"]["rx"]["rebind"] = True
    configure(p, config, runtime, bundle, discover=True)
    assert not runtime["values"]["ami_models"]["rx"].get("rebind")
    frozen = copy.deepcopy(runtime)
    configure(p, config, runtime, bundle)
    assert runtime == frozen


@pytest.mark.parametrize("ts4", [False, True])
def test_native_parser_and_ts4_do_not_require_executable_file(electrical_model, ts4):
    source = Path("models/ibisami/example_rx.ami").read_text(encoding="utf-8").replace(
        "(Reserved_Parameters", '(Reserved_Parameters\n (Ts4file (Usage Info) (Type String) (Value "ondie.s4p"))')
    p, config, runtime, bundle = electrical_model(ts4=ts4, source=source, include_ts4=True, include_binary=False)
    report = configure(p, config, runtime, bundle, discover=True)
    assert p.rx_ibis_valid and p.rx_ami_valid and not p.rx_dll_valid
    assert report["rx"]["binary_path"] is None and report["rx"]["binary_load"] == "not requested"
    frozen = copy.deepcopy(runtime)
    configure(p, config, runtime, bundle)
    assert runtime == frozen
