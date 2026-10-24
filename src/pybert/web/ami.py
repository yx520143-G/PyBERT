"""Private worker IBIS/AMI configuration and read-only execution evidence."""

import contextlib
import copy
import hashlib
import json
import platform
import struct
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
from pyibisami.ami.model import AMIModel
from pyibisami.ami.parameter import AMIParameter, FIXED_FORMATS
from pyibisami.ami.parser import AMIParamConfigurator
from pyibisami.ibis.file import IBISModel

from pybert.utility.ibisami import PYBERT_TX_MODEL_TYPES, PYBERT_RX_MODEL_TYPES, resolve_ami_files


class AMICancelled(RuntimeError):
    """Only a checkpoint which actually observes this task's request raises this."""


def parameter_rows(cfg, branch=None, prefix=()):
    rows = []
    for name, parameter in (cfg.ami_param_defs if branch is None else branch).items():
        path = [*prefix, name]
        if isinstance(parameter, dict):
            rows.extend(parameter_rows(cfg, parameter, path))
        elif isinstance(parameter, AMIParameter):
            editable = path[0] == "Model_Specific" and parameter.pusage in ("In", "InOut") and parameter.pformat not in FIXED_FORMATS
            rows.append({"path": path, "value": cfg.fetch_param_val(list(path)), "editable": editable,
                         "type": parameter.ptype, "usage": parameter.pusage, "format": parameter.pformat,
                         "min": parameter.pmin, "max": parameter.pmax,
                         "values": parameter.pvalue if parameter.pformat == "List" else parameter.pvalues,
                         "list_tips": parameter.plist_tip, "corners": parameter.pcorners, "labels": parameter.plabels,
                         "description": getattr(parameter, "pdescription", None),
                         "unit": "UI" if parameter.ptype == "UI" else "not declared; see original description"})
    return rows


def schema(value):
    if not isinstance(value, dict) or set(value) - {"tx", "rx"}:
        raise ValueError("ami_models: tx/rx objects required.")
    for side, model in value.items():
        if not isinstance(model, dict) or set(model) - {"model_hash", "parameter_model_hash", "selection", "parameters", "search", "sim_corner", "rebind"}:
            raise ValueError(f"{side}: unknown AMI model configuration field.")
        if not isinstance(model.get("model_hash"), str) or len(model["model_hash"]) != 64:
            raise ValueError(f"{side}: explicit model content hash required.")
        if not isinstance(model.get("selection"), dict) or set(model["selection"]) != {"comp", "pin", "mod", "ibis_path"}:
            raise ValueError(f"{side}: complete IBIS selection required.")
        for key in ("parameters", "search"):
            if not isinstance(model.get(key, []), list):
                raise ValueError(f"{side}.{key}: hierarchical rows required.")
            paths = []
            for row in model.get(key, []):
                path = row.get("path") if isinstance(row, dict) else None
                if not isinstance(path, list) or not path or not all(isinstance(p, str) for p in path) or path in paths:
                    raise ValueError(f"{side}.{key}: unique complete hierarchical paths required.")
                paths.append(path)
    json.dumps(value, allow_nan=False)
    return value


def bundle_file(bundle, relative):
    relative = relative.replace("\\", "/")
    row = next((r for r in bundle["files"] if r["relative_path"] == relative), None)
    if not row:
        raise ValueError(f"Missing model dependency: {relative}")
    path = Path(bundle["worker_path"], relative)
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        raise ValueError(f"Model dependency modified: {relative}")
    return path


def ibis_selections(ibis):
    """Ask the native selection observers for the actual dependent option tree."""
    selected = (ibis.comp, ibis.pin, ibis.mod)
    options = {}
    for component in list(ibis.comps):
        ibis.comp = component
        options[component] = {}
        for pin in list(ibis.pins):
            ibis.pin = pin
            options[component][pin] = list(ibis.models)
    ibis.comp, ibis.pin, ibis.mod = selected
    return options


def configure(p, config, runtime, resources, *, discover=False, allow_unbound=False, check=lambda: False, emit=lambda *a, **k: None):
    """Reuse native parser/setters/observers, verify postconditions, never default an active model."""
    values = runtime.get("values", {})
    definitions = values.get("ami_models", {})
    reports = {}
    for side in ("tx", "rx"):
        bundle = next((r for r in resources if r["field"] == side + "_model_bundle"), None)
        ami_required = config[side + "_eq_sel"] == "IBIS-AMI"
        ts4_required = config[side + "_use_ts4"]
        active = config[side + "_sel"] == "ibis" or config[side + "_eq_sel"] == "IBIS-AMI"
        if not active and not discover:
            continue
        if not bundle:
            if active:
                if allow_unbound:
                    reports[side] = {"side": side, "status": "unavailable on this host", "stage": "resource rebind required",
                                     "reason": "Saved input retained; original model content must be explicitly rebound before execution."}
                    continue
                raise ValueError(f"{side}: model resources unbound.")
            continue
        model = copy.deepcopy(definitions.get(side, {}))
        if model.get("rebind"):
            if not discover:
                raise ValueError(f"{side}: explicit rebind must be validated before execution.")
            model = {"model_hash": model["model_hash"], "selection": model["selection"], "rebind": True}
        if model and model["model_hash"] != bundle["sha256"]:
            raise ValueError(f"{side}: model content changed; explicitly rebind and review parameters.")
        report = {"status": "invalid", "stage": "resource", "model_hash": bundle["sha256"], "side": side,
                  "host": {"OS": platform.system(), "architecture": platform.machine(), "bits": struct.calcsize("P") * 8},
                  "files": bundle["files"]}
        reports[side] = report
        try:
            for file in bundle["files"]:
                bundle_file(bundle, file["relative_path"])
            selection = model.get("selection", {})
            relative = selection.get("ibis_path", config[side + "_ibis_file"].replace("\\", "/"))
            reference = config[side + "_ibis_file"].replace("\\", "/")
            if selection and reference != relative and not reference.endswith("/" + relative):
                raise ValueError(f"{side}: requested IBIS path conflicts with frozen model selection; explicitly rebind.")
            if relative not in [f["relative_path"] for f in bundle["files"]]:
                candidates = [f["relative_path"] for f in bundle["files"] if Path(f["relative_path"]).name == Path(relative).name]
                if not discover or len(candidates) != 1:
                    raise ValueError(f"{side}: select an explicit IBIS path within this bundle.")
                relative = candidates[0]
            path = bundle_file(bundle, relative)
            report["stage"] = "IBIS selection"
            ibis = IBISModel(str(path), model_types=PYBERT_TX_MODEL_TYPES if side == "tx" else PYBERT_RX_MODEL_TYPES)
            for key in ("comp", "pin", "mod"):
                if key in selection:
                    setattr(ibis, key, selection[key])
                    if getattr(ibis, key) != selection[key]:
                        raise ValueError(f"{side}: IBIS selection not retained: {key}")
            selection = {key: getattr(ibis, key) for key in ("comp", "pin", "mod")} | {"ibis_path": relative}
            report.update(selection=selection, components=ibis.comps, pins=ibis.pins, models=ibis.models,
                          selection_map=ibis_selections(ibis),
                          ibis_warnings=ibis.ibis_parsing_errors, model_type=ibis.model.model_type,
                          view={"IBIS_source": path.read_text(encoding="utf-8"), "zout": ibis.model.zout,
                                "zin": ibis.model.zin, "ccomp": ibis.model.ccomp})
            setattr(p, "_" + side + "_ibis", ibis)
            p.trait_setq(**{side + "_ibis_valid": True})
            dll, ami = resolve_ami_files(ibis, side == "tx")
            if dll and not ami_required and not Path(dll).is_file():
                dll = ""
            if not ami and not ami_required:
                # Native electrical/TS4 needs the parameter file, not a host executable.
                _, ami_name = ibis.model.get_ami_files(side == "tx")
                ami_path = ibis.resolve_file(ami_name)
                ami = str(ami_path) if ami_path else ""
            cfg = None
            if ami:
                report["stage"] = "AMI parser"
                for file in (ami, *([dll] if dll else [])):
                    bundle_file(bundle, Path(file).relative_to(bundle["worker_path"]).as_posix())
                ami_source = Path(ami).read_bytes()
                parameter_model_hash = hashlib.sha256(json.dumps({"bundle": bundle["sha256"], "selection": selection,
                    "ami_sha256": hashlib.sha256(ami_source).hexdigest(),
                    "binary_sha256": hashlib.sha256(Path(dll).read_bytes()).hexdigest() if dll else None}, sort_keys=True).encode()).hexdigest()
                if model.get("parameter_model_hash", parameter_model_hash) != parameter_model_hash:
                    raise ValueError(f"{side}: selected model changed; parameters require explicit rebind and difference review.")
                try:
                    report["view"]["AMI_source"] = ami_source.decode("utf-8")
                    cfg = AMIParamConfigurator(report["view"]["AMI_source"])
                except Exception as error:
                    if ami_required or ts4_required:
                        raise
                    report.update(status="ready", stage="electrical IBIS only; optional AMI invalid", binary_load="not requested",
                                  ami_capability={"status": "invalid", "stage": "AMI parser", "error": str(error)})
                    definitions[side] = model if model and not model.get("rebind") else {
                        "model_hash": bundle["sha256"], "parameter_model_hash": parameter_model_hash,
                        "selection": selection, "parameters": [], "sim_corner": "typ", "search": []}
                    continue
                cfg.sim_corner = model.get("sim_corner", "typ")
                rows = parameter_rows(cfg)
                supplied = model.get("parameters", [])
                if model and not model.get("rebind") and {tuple(r["path"]) for r in supplied} != {tuple(r["path"]) for r in rows}:
                    raise ValueError(f"{side}: complete dynamic parameter tree required; no omitted defaults.")
                for row in supplied:
                    original = next(r for r in rows if r["path"] == row["path"])
                    if original["editable"]:
                        cfg.set_param_val(list(row["path"]), row["value"])
                    if cfg.fetch_param_val(list(row["path"])) != row["value"]:
                        raise ValueError(f"{side}: parameter did not round-trip: {row['path']}")
                rows = parameter_rows(cfg)
                capabilities = {name: cfg.fetch_param_val(["Reserved_Parameters", name]) for name in
                                ("Init_Returns_Impulse", "GetWave_Exists", "Ts4file", "Ignore_Bits")}
                report.update(parameters=rows, parser_warnings=cfg.ami_parsing_errors, capabilities=capabilities,
                              ami_path=Path(ami).relative_to(bundle["worker_path"]).as_posix(),
                              binary_path=Path(dll).relative_to(bundle["worker_path"]).as_posix() if dll else None)
                ts4 = capabilities["Ts4file"]
                if ts4 and (ts4_required or ami_required):
                    bundle_file(bundle, (path.parent / ts4).relative_to(bundle["worker_path"]).as_posix())
                if config[side + "_use_ts4"] and not ts4:
                    raise ValueError(f"{side}: TS4 requested but model has no Ts4file.")
                if ami_required:
                    report["stage"] = "binary load"
                    if check():
                        raise AMICancelled("Cancelled before binary load")
                    emit("phase", phase=side + " AMI binary load (not execution qualification)")
                    library = AMIModel(dll)
                    report["ABI"] = {"loader": "ctypes.CDLL", "pointer_bits": struct.calcsize("P") * 8,
                                     "exports": {"AMI_Init": True, "AMI_Close": True, "AMI_GetWave": library.has_getwave}}
                    if capabilities["GetWave_Exists"] and not library.has_getwave:
                        raise ValueError(f"{side}: GetWave_Exists declared but AMI_GetWave export is missing.")
                    if check():
                        raise AMICancelled("Cancelled after binary load")
                    setattr(p, "_" + side + "_model", library)
                setattr(p, "_" + side + "_cfg", cfg)
                p.trait_setq(**{side + "_ami_valid": True, side + "_dll_valid": ami_required,
                               side + "_has_getwave": bool(capabilities["GetWave_Exists"]), side + "_has_ts4": bool(ts4),
                               side + "_dll_file": dll, side + "_ami_file": ami})
                setattr(p, side + "_ami_tap_tuners", cfg.mk_tap_tuners())
                if config[side + "_eq_sel"] == "IBIS-AMI":
                    capability = "GetWave_Exists" if config[side + "_use_getwave"] else "Init_Returns_Impulse"
                    if not capabilities[capability]:
                        raise ValueError(f"{side}: requested mode unsupported by model: {capability}")
            elif config[side + "_eq_sel"] == "IBIS-AMI":
                report["status"] = "unavailable on this host"
                raise ValueError(f"{side}: no executable for this host/direction.")
            elif config[side + "_use_ts4"]:
                raise ValueError(f"{side}: no parsed AMI Ts4file available.")
            if active:
                # Explicit notification preserves native Rx AMI observer side effects even on a preloaded snapshot.
                p.trait_setq(**{side + "_use_ami": False})
                setattr(p, side + "_eq_sel", config[side + "_eq_sel"])
                setattr(p, side + "_use_ami", config[side + "_eq_sel"] == "IBIS-AMI")
                if getattr(p, side + "_use_ami") != (config[side + "_eq_sel"] == "IBIS-AMI"):
                    raise ValueError(f"{side}: native mode observer did not activate requested mode.")
            search = model.get("search", [])
            for tuner in getattr(p, side + "_ami_tap_tuners"):
                row = next((r for r in search if r["path"] == list(tuner.branch_names)), None)
                if row:
                    for key in ("enabled", "min_val", "max_val", "step", "value"):
                        setattr(tuner, key, row[key])
            if {tuple(r["path"]) for r in search} - {tuple(t.branch_names) for t in getattr(p, side + "_ami_tap_tuners")}:
                raise ValueError(f"{side}: unknown/unsupported optimizer parameter path.")
            reports[side].update(status="ready", stage="preflight only; no execution", binary_load="loaded" if cfg and ami_required else "not requested")
            definitions[side] = {"model_hash": bundle["sha256"], "selection": selection, "parameters": report.get("parameters", []),
                                 **({"parameter_model_hash": parameter_model_hash} if cfg else {}),
                                 "sim_corner": cfg.sim_corner if cfg else "typ", "search": [
                                     {"path": list(t.branch_names), **{key: getattr(t, key) for key in ("enabled", "min_val", "max_val", "step", "value")}}
                                     for t in getattr(p, side + "_ami_tap_tuners")]}
        except Exception as error:
            if isinstance(error, OSError):
                report["status"] = "unavailable on this host"
            report["error"] = str(error)
            error.ami_report = reports
            raise
    if definitions:
        runtime.setdefault("version", 1)
        values = runtime.setdefault("values", {})
        values["ami_models"] = definitions
    for key in ("rx_use_clocks", "ami_opt_trials"):
        if key in values:
            setattr(p, key, values[key])
    # Traits list containers must not cross IPC: they retain private owner/trait references.
    return json.loads(json.dumps(reports))


class Execution:
    """Capture original helper input/output and every actual library call, including failures."""

    def __init__(self, check=lambda: False):
        self.check = check
        self.calls, self.arrays, self.library_calls, self.dll_calls = [], {}, [], []
        self.phases = []

    @contextlib.contextmanager
    def phase(self, name):
        """Record an actual caller stage separately from AMI API and numerical helper counts."""
        row = {"phase": name, "started_at": time.time(), "status": "running", "elapsed_s": None}
        self.phases.append(row)
        try:
            yield
        except BaseException as error:
            row.update(status="failed", error_type=type(error).__name__, error=str(error))
            raise
        else:
            row["status"] = "completed"
        finally:
            row["elapsed_s"] = time.time() - row["started_at"]

    def checkpoint(self):
        if self.check():
            raise AMICancelled("AMI checkpoint observed cancellation")

    @contextlib.contextmanager
    def capture(self):
        from pybert.models import bert
        from pybert.threads import optimization
        original = bert.run_ami_model
        constructor = AMIModel.__init__

        def load(model, filename):
            constructor(model, filename)
            for name, attribute in (("AMI_Init", "_amiInit"), ("AMI_GetWave", "_amiGetWave")):
                pointer = getattr(model, attribute)
                if pointer is None:
                    continue

                def invoke(*args, _pointer=pointer, _name=name):
                    self.checkpoint()
                    row = {"method": _name, "started_at": time.time(), "returned": False}
                    self.dll_calls.append(row)
                    try:
                        result = _pointer(*args)
                        row["returned"] = True
                        return result
                    finally:
                        row["elapsed_s"] = time.time() - row["started_at"]

                setattr(model, attribute, invoke)

        def helper(*args, **kwargs):
            self.checkpoint()
            index = len(self.calls)
            row = {"index": index, "binary": args[0], "mode": "GetWave" if args[2] else "Init", "ui_s": args[3], "ts_s": args[4],
                   "requested_parameters": copy.deepcopy(args[1].input_ami_params), "bits_per_call": kwargs.get("bits_per_call", 0),
                   "response_probe_bits_per_call": 40, "started_at": time.time(), "status": "execution failed"}
            self.calls.append(row)
            for key, value in (("input_h", args[5]), ("input_x", args[6])):
                self.arrays[f"ami.call{index}.{key}"] = np.asarray(value).copy()
                self.arrays[f"ami.call{index}.{key}_t_s"] = np.arange(len(value)) * args[4]
            try:
                result = original(*args, **kwargs)
                for key, value in zip(("y", "clocks", "h", "out_h"), result[:4]):
                    self.arrays[f"ami.call{index}.{key}"] = np.asarray(value).copy()
                    if key != "clocks":
                        self.arrays[f"ami.call{index}.{key}_t_s"] = np.arange(len(value)) * args[4]
                if not all(np.isfinite(self.arrays[f"ami.call{index}.{key}"]).all() and self.arrays[f"ami.call{index}.{key}"].size for key in ("y", "h", "out_h")):
                    raise ValueError("AMI helper returned missing/nonfinite response or output.")
                row.update(message=result[4], params_out=result[5], status="returned; engine postconditions pending")
                self.checkpoint()
                return result
            except Exception as error:
                row["error"] = str(error)
                raise
            finally:
                row["elapsed_s"] = time.time() - row["started_at"]

        def counted(name, function):
            def call(model, *args, **kwargs):
                self.checkpoint()
                row = {"method": name, "level": "Python wrapper; not individual DLL chunks", "started_at": time.time(), "returned": False}
                self.library_calls.append(row)
                try:
                    result = function(model, *args, **kwargs)
                    row["returned"] = True
                    return result
                finally:
                    row["elapsed_s"] = time.time() - row["started_at"]
            return call

        with patch.object(bert, "run_ami_model", helper), patch.object(optimization, "run_ami_model", helper), \
                patch.object(AMIModel, "__init__", load), \
                patch.object(AMIModel, "initialize", counted("AMI_Init", AMIModel.initialize)), \
                patch.object(AMIModel, "getWave", counted("AMI_GetWave", AMIModel.getWave)):
            yield self

    def write(self, directory, report=None):
        from pybert.web.archive import json_bytes

        Path(directory, "ami-execution.json").write_bytes(json_bytes({
            "calls": self.calls, "library_calls": self.library_calls, "dll_calls": self.dll_calls,
            "models": report or {}, "phases": self.phases,
            "clock_buffer_scope": "helper valid prefix only; full ABI buffers are separate B diagnostics"}))
        np.savez_compressed(Path(directory, "ami-execution.npz"), **self.arrays)


def annotate(p, execution, reports, arrays, manifest):
    """Describe actual native branches and preserve helper data without creating internal state."""
    tx_gw = p.tx_use_ami and p.tx_use_getwave
    info = getattr(p, "ami_clock_info", {})
    observed = bool(info.get("producer_contract_version") == 2 and info.get("invocation_id"))
    actual = info.get("actual_branch") if observed else None
    native_returned = actual == "native" and info.get("native_returned") is True
    model_clocks = actual == "ami"
    modes = {side: "GetWave" if getattr(p, side + "_use_getwave") else "Init" for side in ("tx", "rx") if getattr(p, side + "_use_ami")}
    branch = {"modes": modes, "requested_rx_use_clocks": p.rx_use_clocks,
               "clock_source": "AMI clocks" if model_clocks else "Native CDR" if native_returned else "unavailable",
               "clock_reason": info.get("reason") if observed else "No current versioned producer evidence",
               "actual_producer_branch": actual,
               "producer_invocation_id": info.get("invocation_id") if observed else None,
               "consumption_status": info.get("consumption_status") if observed else "unknown",
               "consumed_count": info.get("consumed_count") if observed else None,
               "producer_run_status": info.get("run_status") if observed else "unknown",
              "rx_ffe": "bypass: Rx AMI replaces Native Rx EQ" if p.rx_use_ami else "Native",
               "native_DFE_CDR_AGC": ("bypassed by actual AMI producer; adaptation readiness is not model lock"
                                      if model_clocks else
                                      "executed native run_dfe; tuner enabled prefix determines adaptation"
                                      if native_returned else "native execution not proven"),
              "rx_in": "diagnostic convolve(tx_out + noise, chnl_h); downstream uses other arrays; explicit noise not guaranteed downstream" if tx_gw else "actual noisy Rx input for Rx GetWave / Native; Rx Init has its own output-noise branch",
              "noise": "Tx GetWave known native limitation" if tx_gw else "Rx Init adds noise at ctle_out" if p.rx_use_ami and not p.rx_use_getwave else "rx_in",
              "model_state": "only raw params_out are model-returned; native zero/empty placeholders are not model taps/lock/UI estimates"}
    previous = manifest.get("ami", {})
    manifest["ami"] = {**previous, "schema_version": 1, "models": reports, "execution": execution.calls,
                       "library_calls": execution.library_calls, "dll_calls": execution.dll_calls,
                       "actual_branch": branch, "phases": copy.deepcopy(execution.phases),
                       "producer": {name: info.get(name) if observed else None for name in
                           ("producer_contract_version", "invocation_id", "epoch_basis", "requested", "mode", "role",
                            "main_origin", "format_status", "eligible", "actual_branch", "consumption_status",
                            "consumed_count", "run_status", "native_returned", "reason", "model_lock_status")}}
    for key, value in execution.arrays.items():
        arrays[key] = value
        field = key.rsplit(".", 1)[1]
        manifest["datasets"][key] = {"field": key, "producer": "original run_ami_model", "point": "model helper", "kind": "AMI raw",
                                    "dtype": str(value.dtype), "shape": list(value.shape), "unit": "s" if field == "clocks" or field.endswith("_t_s") else "V/sample" if field.endswith("h") else "V",
                                    "window": "entire original helper array", "clock_basis": branch["clock_source"], "availability": "available" if value.size else "unavailable: model returned none",
                                    "axis": key + "_t_s" if key + "_t_s" in execution.arrays else None, "display_noise": False}
    labels = {"rx_in": "Tx GetWave diagnostic Rx reference" if tx_gw else "Rx input (+Tx, noise)",
              "ctle_out": "Rx AMI output" if p.rx_use_ami else "Native CTLE output",
              "ffe_out": "Rx AMI output · Native Rx FFE bypass" if p.rx_use_ami else "Native Rx FFE output"}
    for key in ("ctle_h", "ctle_s", "ctle_p", "ctle_H", "ctle_out_h", "ctle_out_s", "ctle_out_p", "ctle_out_H", "ffe_out", "rx_in", "ctle_out"):
        manifest["datasets"][key]["execution_context"] = branch
        if p.rx_use_ami and key.startswith("ctle"):
            manifest["datasets"][key]["producer"] = "Rx AMI response/output via original engine; not Native CTLE"
    if p.rx_use_ami:
        for key, dataset in manifest["datasets"].items():
            if key.startswith(("ffe_", "context.ffe.", "jitter_ffe", "display.eye.ffe")):
                dataset["execution_context"] = branch
                dataset["meaning"] = "Rx AMI output / Native RxFFE bypass; helper observer is equivalent to Rx AMI output, not an additional FFE execution"
    if manifest.get("observations"):
        manifest["observations"]["tx"]["label"] = labels["rx_in"]
        manifest["observations"]["ctle"]["label"] = labels["ctle_out"]
        manifest["observations"]["ffe"]["label"] = labels["ffe_out"]
    for plot in manifest["plots"].values():
        plot.setdefault("metadata", {})["AMI"] = branch
        if p.rx_use_ami:
            plot["title"] = plot["title"].replace("CTLE", "Rx AMI").replace("Rx FFE", "Rx FFE bypass")
        for trace in plot.get("traces", []):
            for key, label in labels.items():
                if trace.get("name") in ("Native Rx input (+Tx, noise)", "CTLE output", "Rx FFE output") and key in str(trace.get("y", "")):
                    trace["name"] = label
    manifest["warnings"].append(branch["rx_in"])
