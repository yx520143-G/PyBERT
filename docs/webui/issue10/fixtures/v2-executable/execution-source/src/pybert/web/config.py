"""Native configuration snapshots and ordered edits, used only inside a worker."""

import hashlib
import json
import math
import io
import pickle
import base64
import re
import tempfile
from pathlib import Path

import yaml

from pybert import __version__
from pybert.configuration import PyBertCfg
from pybert.pybert import PyBERT

TABLES = {
    "tx_taps": (6, ("enabled", "value", "min_val", "max_val")),
    "rx_taps": (100, ("enabled", "value", "min_val", "max_val")),
    "tx_tap_tuners": (6, ("enabled", "pos", "min_val", "max_val", "step")),
    "ffe_tap_tuners": (100, ("enabled", "pos", "min_val", "max_val", "step")),
    "dfe_tap_tuners": (20, ("enabled", "min_val", "max_val")),
}
RESOURCE_FIELDS = tuple(f"{side}_{kind}_file" for side in ("tx", "rx") for kind in ("ibis", "ami", "dll"))
POSITIVE = (
    "bit_rate",
    "vod",
    "nspui",
    "nbits",
    "eye_bits",
    "f_max",
    "f_step",
    "Z0",
    "v0",
    "w0",
    "rs",
    "rin",
    "rx_bw",
    "peak_freq",
    "decision_scaler",
    "n_ave",
    "n_lock_ave",
    "lock_sustain",
    "sum_bw",
)
NONNEGATIVE = (
    "seed",
    "rn",
    "pn_mag",
    "pn_freq",
    "cout",
    "cin",
    "l_ch",
    "Rdc",
    "R0",
    "Theta0",
    "gain",
    "delta_t_ui",
    "alpha",
    "rel_lock_tol",
    "thresh",
)
INTEGERS = (
    "nbits",
    "seed",
    "nspui",
    "eye_bits",
    "lane_sel",
    "rx_n_taps",
    "rx_n_pre",
    "rx_viterbi_symbols",
    "n_ave",
    "n_lock_ave",
    "lock_sustain",
)


def input_hash(config):
    """Hash the complete input, independently of YAML formatting and metadata dates."""

    def canonical(value):
        if isinstance(value, dict):
            return {key: canonical(v) for key, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [canonical(v) for v in value]
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    return hashlib.sha256(
        json.dumps(canonical(config), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def new_engine():
    return PyBERT(run_simulation=False, gui=False)


def snapshot(engine):
    cfg = vars(PyBertCfg(engine, "", __version__))
    return json.loads(json.dumps({k: v for k, v in cfg.items() if k not in ("date_created", "version")}))


def validate(config, defaults, complete=True, execution=False):
    """Reject unsupported active paths before any resource observer can load them."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object.")  # noqa: TRY004 - HTTP input validation contract
    if "rx_viterbi_fec" in config:
        raise ValueError("unsupported_native_fec: API-only FEC is not supported or persisted by PyBertCfg.")
    unknown = set(config) - set(defaults)
    if unknown:
        raise ValueError(f"Unsupported configuration fields/runtime extensions: {sorted(unknown)}")
    if complete and set(config) != set(defaults):
        raise ValueError(f"Complete snapshot required; missing {sorted(set(defaults) - set(config))}")
    c = defaults | config
    for key, value in config.items():
        expected = defaults[key]
        if key in TABLES:
            length, columns = TABLES[key]
            if not isinstance(value, list) or len(value) != length:
                raise ValueError(f"{key}: expected all {length} slots.")
            for row in value:
                if not isinstance(row, (tuple, list)) or len(row) != len(columns) or type(row[0]) is not bool:
                    raise ValueError(f"{key}: invalid native tap tuple.")
                if any(type(v) not in (int, float) or not math.isfinite(v) for v in row[1:]):
                    raise ValueError(f"{key}: finite numeric tap values required.")
                lo, hi = row[2:4] if "value" in columns or "pos" in columns else row[1:3]
                if lo > hi or ("step" in columns and row[-1] <= 0):
                    raise ValueError(f"{key}: invalid bounds/step.")
        elif isinstance(expected, bool):
            if type(value) is not bool:
                raise ValueError(f"{key}: boolean required.")
        elif isinstance(expected, (int, float)):
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{key}: finite number required.")
            if key in INTEGERS and (not float(value).is_integer() or type(value) is bool):
                raise ValueError(f"{key}: integer required.")
        elif isinstance(expected, str) and not isinstance(value, str):
            raise ValueError(f"{key}: string required.")
        elif isinstance(expected, list) and (
            not isinstance(value, list) or not all(isinstance(v, str) for v in value)
        ):
            raise ValueError(f"{key}: list of paths required.")
    for key in POSITIVE:
        if c[key] <= 0:
            raise ValueError(f"{key}: must be positive.")
    for key in NONNEGATIVE:
        if c[key] < 0:
            raise ValueError(f"{key}: must be nonnegative.")
    if not 0 <= c["rx_n_taps"] <= 100 or not 0 <= c["rx_n_pre"] <= max(0, c["rx_n_taps"] - 1):
        raise ValueError("Rx FFE requires 0..100 taps and Npre < Ntaps (Npre=0 for zero taps).")
    if c["eye_bits"] >= c["nbits"]:
        raise ValueError("EyeBits must be smaller than Nbits; native analysis needs a settling window.")
    if c["nspui"] < 2 or c["nspui"] % 2 or (c["mod_type"] == "PAM-4" and (c["nbits"] % 2 or c["eye_bits"] % 2)):
        raise ValueError("Even NspUI >= 2 and even PAM-4 bit counts are required.")
    if c["f_step"] * 1e6 > c["f_max"] * 1e9:
        raise ValueError("fStep exceeds fMax.")
    for key, values in {
        "mod_type": ("NRZ", "PAM-4", "Duo-binary"),
        "tx_sel": ("native", "ibis"),
        "rx_sel": ("native", "ibis"),
        "tx_eq_sel": ("Native", "IBIS-AMI"),
        "rx_eq_sel": ("Native", "IBIS-AMI"),
        "inter_sel": ("native", "single", "multiple"),
    }.items():
        if c[key] not in values:
            raise ValueError(f"{key}={c[key]}: active IBIS/AMI is unsupported; see #10.")
    from pybert.web.viterbi import plan

    plan(c, execution=execution)
    if execution and c["impulse_length"] != 0:
        raise ValueError("impulse_length: nonzero ns is blocked by native inconsistent units; use automatic 0.")
    tx_gw = c["tx_eq_sel"] == "IBIS-AMI" and c["tx_use_getwave"]
    if execution and c["rx_eq_sel"] == "Native" and (c["ctle_enable"] or tx_gw) and c["ctle_sel"] != "Native":
        raise ValueError("ctle_sel=File with CTLE enabled is blocked by the native File path; see #4.")
    if c["use_ctle_file"] != (c["ctle_sel"] == "File"):
        raise ValueError("ctle_sel and use_ctle_file conflict.")
    if execution and c["pkg_enable"] and c["include_fext"]:
        raise ValueError("Package + FEXT is unavailable: victim package and simplified aggressor terminations are not jointly validated.")
    if execution and c["pkg_enable"]:
        from pychopmarg.config.ieee_8023dj_d3p3 import device_model

        device_model(c["pkg_group"], c["tx_pkg_case"], False, include_host=c["pkg_include_host"])
        device_model(c["pkg_group"], c["rx_pkg_case"], True, include_host=c["pkg_include_host"])
    if execution and c["enable_com"] and (c["inter_sel"] != "single" or Path(c["ch_file"]).suffix.lower() != ".s4p"):
        raise ValueError("Run-after COM requires a single .s4p; it uses its own parameters.")


def yaml_text(config, runtime_extensions=None, resource_bindings=None):
    cfg = PyBertCfg.__new__(PyBertCfg)
    cfg.__dict__.update(date_created="", version=__version__, **config)
    for key in TABLES:
        cfg.__dict__[key] = [tuple(row) for row in config[key]]
    header = "# Resources are referenced only; resource bytes are NOT included. Bind before Run.\n"
    if runtime_extensions or resource_bindings:
        extra = {"runtime_extensions": runtime_extensions or {}, "resource_bindings": resource_bindings or {}}
        header += "# pybert-web-runtime-v1: " + json.dumps(extra, ensure_ascii=False, allow_nan=False) + "\n"
        header += "# Runtime extensions above cannot be expressed by native PyBertCfg.\n"
        if runtime_extensions:
            header += "# Native PyBertCfg loss list (desktop ignores): " + ", ".join(sorted(runtime_extensions.get("values", {}))) + "\n"
            header += "# Candidate pulse/FOM/history require a .pybert_opt record; YAML stores draft/initial values only.\n"
    return header + yaml.dump(cfg, sort_keys=False, allow_unicode=True)


class ConfigLoader(yaml.SafeLoader):
    """Accept just the native config and tuple tags, never arbitrary Python objects."""


ConfigLoader.add_constructor("tag:yaml.org,2002:python/tuple", lambda loader, node: loader.construct_sequence(node))
ConfigLoader.add_constructor(
    "tag:yaml.org,2002:python/object:pybert.configuration.PyBertCfg",
    lambda loader, node: loader.construct_mapping(node, deep=True),
)


def parse_yaml(text):
    if len(text.encode("utf-8")) > 4_000_000:
        raise ValueError("Configuration exceeds 4 MB.")
    value = yaml.load(text, Loader=ConfigLoader)
    if not isinstance(value, dict):
        raise ValueError("Expected native PyBertCfg YAML.")  # noqa: TRY004 - HTTP input validation contract
    return {k: v for k, v in value.items() if k not in ("version", "date_created")}


class LegacyLoader(pickle.Unpickler):
    """Only a known inert configuration container and primitive pickle opcodes."""

    def find_class(self, module, name):
        if (module, name) == ("pybert.configuration", "PyBertCfg"):
            return PyBertCfg
        raise ValueError("历史格式不能安全转换，请用原桌面导出 YAML。")


def parse_legacy(content):
    if len(content) > 4_000_000:
        raise ValueError("Configuration exceeds 4 MB.")
    value = LegacyLoader(io.BytesIO(content)).load()
    if not isinstance(value, (PyBertCfg, dict)):
        raise ValueError("历史格式不能安全转换，请用原桌面导出 YAML。")
    result = vars(value) if isinstance(value, PyBertCfg) else value
    # Reject non-primitive state before any native object is populated.
    json.dumps(result, allow_nan=False)
    return {k: v for k, v in result.items() if k not in ("version", "date_created")}


def import_config(supplied, defaults):
    """Known legacy aliases only; report every default/padded slot explicitly."""
    supplied = dict(supplied)
    changes = []
    for key, target, aliases in (
        ("tx_eq_sel", "tx_eq_sel", {"native": "Native", "ibis-ami": "IBIS-AMI"}),
        ("rx_eq_sel", "rx_eq_sel", {"native": "Native", "ibis-ami": "IBIS-AMI"}),
        ("ctle_sel", "ctle_sel", {"native": "Native", "file": "File"}),
        ("inter_sel", "inter_sel", {s: s for s in ("native", "single", "multiple")}),
        ("mod_type", "mod_type", {"nrz": "NRZ", "pam-4": "PAM-4", "duo-binary": "Duo-binary"}),
    ):
        if key in supplied:
            supplied[target] = aliases.get(str(supplied[key]).lower(), supplied[key])
    for old, new in (("tx_use_ibis", "tx_sel"), ("rx_use_ibis", "rx_sel"), ("use_ch_file", "inter_sel")):
        if old in supplied:
            value = supplied.pop(old)
            if type(value) is not bool:
                raise ValueError(f"{old}: boolean required.")
            if old == "use_ch_file" and not value:
                changes.append("use_ch_file=false: native legacy no-op; current inter_sel retained")
                continue
            mapped = ("single" if value else "native") if old == "use_ch_file" else ("ibis" if value else "native")
            if new in supplied and supplied[new] != mapped:
                raise ValueError(f"Conflicting legacy {old} and current {new}.")
            supplied[new] = mapped
            changes.append(f"{old} -> {new}")
    if "delta_t" in supplied:
        value = supplied.pop("delta_t")
        if "delta_t_ui" in supplied:
            changes.append("legacy delta_t ignored by native precedence: explicit delta_t_ui present")
        else:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("delta_t: finite ps required.")
            context = new_engine()
            context.bit_rate = supplied.get("bit_rate", defaults["bit_rate"])
            context.mod_type = supplied.get("mod_type", defaults["mod_type"])
            supplied["delta_t_ui"] = value * 1e-12 / context.ui
            changes.append("delta_t ps -> delta_t_ui using native UI of imported rate/modulation")
    if "ctle_sel" in supplied and "use_ctle_file" not in supplied:
        supplied["use_ctle_file"] = supplied["ctle_sel"] == "File"
    elif "use_ctle_file" in supplied and "ctle_sel" not in supplied:
        supplied["ctle_sel"] = "File" if supplied["use_ctle_file"] else "Native"
    missing = sorted(set(defaults) - set(supplied))
    for key, (length, _) in TABLES.items():
        if key in supplied and isinstance(supplied[key], list) and len(supplied[key]) < length:
            changes.append(f"{key}: padded slots {len(supplied[key])}..{length-1} from constructed defaults")
            supplied[key] = supplied[key] + defaults[key][len(supplied[key]):]
    return supplied, {"defaulted_fields": missing, "default_source": "fresh native constructor at recorded adapter/native version", "compatibility": changes}


def extensions(value):
    if not value:
        return {}
    if set(value) != {"version", "values"} or type(value["version"]) is not int or value["version"] != 1 or not isinstance(value["values"], dict):
        raise ValueError("runtime_extensions requires version=1 and values object.")
    values = value["values"]
    if "rx_viterbi_fec" in values:
        raise ValueError("unsupported_native_fec: API-only FEC is unsupported.")
    if set(values) - {"rlm", "rx_use_clocks", "ami_opt_trials", "tx_ami_params", "rx_ami_params", "optimizer_values", "eq_application", "ami_models"}:
        raise ValueError("Unknown runtime extension.")
    for key in ("rx_use_clocks",):
        if key in values and type(values[key]) is not bool:
            raise ValueError(f"{key}: boolean required.")
    if "rlm" in values and (type(values["rlm"]) not in (int, float) or not math.isfinite(values["rlm"])):
        raise ValueError("rlm: finite native numeric value required.")
    if "ami_opt_trials" in values and (type(values["ami_opt_trials"]) is not int or values["ami_opt_trials"] < 1):
        raise ValueError("ami_opt_trials: positive integer required.")
    for key in ("tx_ami_params", "rx_ami_params"):
        if key in values and not isinstance(values[key], dict):
            raise ValueError(f"{key}: dynamic parameter object required.")
    if "optimizer_values" in values:
        rows = values["optimizer_values"]
        if not isinstance(rows, dict) or set(rows) != {"tx", "ffe"}:
            raise ValueError("optimizer_values: tx and ffe initial-value arrays required.")
        for key, length in (("tx", 6), ("ffe", 100)):
            if not isinstance(rows[key], list) or len(rows[key]) != length or any(type(v) not in (int, float) or not math.isfinite(v) for v in rows[key]):
                raise ValueError(f"optimizer_values.{key}: {length} finite values required.")
    if "eq_application" in values:
        row = values["eq_application"]
        if not isinstance(row, dict) or row.get("version") != 1 or not all(isinstance(row.get(k), str) for k in ("opt_id", "candidate_id", "before_input_hash", "after_input_hash")):
            raise ValueError("eq_application: versioned opt/candidate/input provenance required.")
    json.dumps(value, allow_nan=False)
    if "ami_models" in values:
        from pybert.web.ami import schema

        schema(values["ami_models"])
    return value


def binding_data(value):
    if not isinstance(value, dict) or set(value) - {"ch_file", "ch_files", "com_cfg_file", "tx_model_bundle", "rx_model_bundle"}:
        raise ValueError("resource_bindings: expected known channel/COM field bindings.")
    for key, item in value.items():
        if key == "ch_files" and not isinstance(item, list):
            raise ValueError("ch_files bindings must be an ordered list, including unbound null positions.")
        ids = item if key == "ch_files" else [item]
        if any(rid is not None and (not isinstance(rid, str) or not re.fullmatch(r"[a-f0-9]{64}\.(?:s(?:1|2|4|8|12)p|csv|txt|xls|xlsx|model)", rid)) for rid in ids):
            raise ValueError(f"{key}: invalid resource identity.")
    return value


def unresolved_references(config, bindings):
    result = {}
    for key in ("ch_file", "ch_files", "ctle_file", "com_cfg_file", *RESOURCE_FIELDS):
        value = config[key]
        if key == "ch_files":
            ids = bindings.get(key, [])
            missing = [{"index": i, "reference": ref} for i, ref in enumerate(value) if i >= len(ids) or not ids[i]]
            if missing:
                result[key] = missing
        elif value and not bindings.get(key):
            result[key] = value
    return result


def load_config(engine, config, defaults=None):
    """Reuse native full-load ordering and tap restoration; inactive paths stay inert."""
    defaults = defaults or snapshot(new_engine())
    validate(config, defaults)
    # PyBertCfg order puts dimensions before the complete saved tap lists.
    ordered = {key: config[key] for key in defaults}
    ordered.update({key: int(ordered[key]) for key in INTEGERS})
    paths = {key: ordered[key] for key in RESOURCE_FIELDS}
    ordered.update({key: "" for key in RESOURCE_FIELDS})
    # Loading ordinary draft state must never load a library or silently fall back through an observer.
    modes = {f"{side}_{name}": ordered[f"{side}_{name}"] for side in ("tx", "rx") for name in ("sel", "eq_sel", "use_ami")}
    ordered.update({f"{side}_{name}": value for side in ("tx", "rx") for name, value in
                    (("sel", "native"), ("eq_sel", "Native"), ("use_ami", False))})
    with tempfile.TemporaryDirectory(prefix="pybert-config-") as tmp:
        path = Path(tmp) / "input.yaml"
        path.write_text(yaml_text(ordered), encoding="utf-8")
        engine.load_configuration(path)
    engine.trait_setq(**paths, **modes)
    validate(snapshot(engine), defaults)
    return engine


def normalize(request, check=lambda: False, emit=lambda *a, **k: None):
    """A full load or an ordered observer patch; each call owns one fresh engine."""
    if "rx_viterbi_fec" in request:
        raise ValueError("unsupported_native_fec: API-only FEC is unsupported.")
    engine = new_engine()
    defaults = snapshot(engine)
    runtime = request.get("runtime_extensions", {})
    bindings = request.get("resource_bindings", {})
    report = {}
    mode = request.get("mode", "load")
    if mode == "defaults":
        pass
    elif mode == "load":
        supplied = (parse_yaml(request["yaml"]) if "yaml" in request else
                    parse_legacy(base64.b64decode(request["legacy_base64"], validate=True)) if "legacy_base64" in request else request["config"])
        if "yaml" in request:
            for line in request["yaml"].splitlines():
                if line.startswith("# pybert-web-runtime-v1: "):
                    extra = json.loads(line.split(": ", 1)[1])
                    if not isinstance(extra, dict) or set(extra) - {"runtime_extensions", "resource_bindings"}:
                        raise ValueError("Unknown versioned Web configuration metadata.")
                    runtime = extra.get("runtime_extensions", {})
                    bindings = request.get("resource_bindings", extra.get("resource_bindings", {}))
        supplied, report = import_config(supplied, defaults)
        runtime, bindings = extensions(runtime), binding_data(bindings)
        validate(supplied, defaults, complete=False)
        load_config(engine, defaults | supplied, defaults)
    elif mode == "patch":
        runtime, bindings = extensions(runtime), binding_data(bindings)
        load_config(engine, request["config"], defaults)
        for edit in request["patches"]:
            key, value = edit["field"], edit["value"]
            before = snapshot(engine)
            # Ntaps observer may clamp Npre; validate that derived pair after the edit.
            proposed = before | {key: value}
            if key == "ctle_sel":
                proposed["use_ctle_file"] = value == "File"
            elif key == "use_ctle_file":
                proposed["ctle_sel"] = "File" if value else "Native"
            if key == "rx_n_taps" and isinstance(value, int):
                proposed["rx_n_pre"] = min(before["rx_n_pre"], max(0, value - 1))
            validate(proposed, defaults)
            if key in TABLES or key in RESOURCE_FIELDS:
                load_config(engine, proposed, defaults)
            else:
                setattr(engine, key, value)
                if key == "use_ctle_file":
                    engine.ctle_sel = proposed["ctle_sel"]
            validate(snapshot(engine), defaults)
    elif mode in ("optimizer_plan", "use_eq", "reset_eq", "ami_configure"):
        from pybert.web.optimization import optimizer_action

        runtime, bindings = extensions(runtime), binding_data(bindings)
        load_config(engine, request["config"], defaults)
        if mode != "ami_configure":
            if request.get("frozen_resources"):
                from pybert.web.ami import configure

                configure(engine, request["config"], runtime, request["frozen_resources"], check=check, emit=emit)
            runtime, report = optimizer_action(engine, runtime, mode, request.get("optimization"))
    else:
        raise ValueError(f"Unknown normalize mode {mode}.")
    config = snapshot(engine)
    for side in ("tx", "rx"):
        config[side + "_use_ami"] = config[side + "_eq_sel"] == "IBIS-AMI"
    engine.trait_setq(**{side + "_use_ami": config[side + "_use_ami"] for side in ("tx", "rx")})
    model_report = {}
    if request.get("frozen_resources"):
        from pybert.web.ami import configure

        model_report = configure(engine, config, runtime, request["frozen_resources"], discover=True, check=check, emit=emit)
        # Keep user resource references separate from paths projected into this child's immutable bundle.
        effective = snapshot(engine)
        config.update({k: v for k, v in effective.items() if k not in RESOURCE_FIELDS})
    runtime = extensions(runtime)
    return {
        "config": config,
        "input_hash": input_hash(config),
        "input_identity_hash": input_hash({"config": config, "runtime_extensions": runtime, "resource_bindings": bindings}),
        "input_hash_schema": "native-json-v1-integral-floats",
        "yaml": yaml_text(config, runtime, bindings),
        "runtime_extensions": runtime,
        "runtime_defaults": {key: getattr(engine, key) for key in ("rlm", "rx_use_clocks", "ami_opt_trials")},
        "resource_bindings": bindings,
        "import_report": report,
        "unresolved_references": unresolved_references(config, bindings),
        "warnings": warnings(config),
        "ami_models": model_report,
        "runtime_status": {key: "inactive in Native Run; retained for #8/#10" for key in runtime.get("values", {})},
    }


def warnings(config):
    rows = config["dfe_tap_tuners"]
    prefix = next((i for i, row in enumerate(rows) if not row[0]), len(rows))
    messages = [
        f"DFE consumes the continuous enabled prefix: {prefix} taps.",
        "Rx Cac is retained; the native producer does not consume it.",
        "RLM belongs to optimization; ordinary Run does not consume it.",
    ]
    if any(row[0] for row in rows[prefix:]):
        messages.append("Enabled DFE rows after the first disabled row are retained but not consumed.")
    if not config["ctle_enable"]:
        messages.append("CTLE bypassed; File/native preset is inactive.")
    if config["cdr_type"] == "Mueller-Muller":
        messages.append("Mueller-Muller uses a fixed native lock point, not acquisition dynamics.")
    if config["pkg_enable"]:
        messages.append("Native package replaces ordinary Rs/Cout/Rin/Cin; those stored presets are inactive.")
    if config["pkg_enable"] and config["include_fext"]:
        messages.append("Package + FEXT is unavailable pending joint validation.")
    if config["ctle_enable"] and config["ctle_sel"] == "File":
        messages.append("Enabled CTLE File is blocked by the native File path.")
    if config["impulse_length"] != 0:
        messages.append("Nonzero impulse_length is saved but blocked at Run due to native inconsistent units.")
    if config["tx_use_ts4"] or config["rx_use_ts4"]:
        messages.append("On-die TS4 presets are inactive in Native electrical mode; no IBIS/AMI resources loaded.")
    if config["enable_com"]:
        messages.append("COM is deferred to a separate joined child with its own parameters; no current EQ/noise/bitrate injection.")
    if config["rx_use_viterbi"]:
        from pybert.web.viterbi import plan

        budget = plan(config)
        messages.append(f"Native ISI/MLSD: L={budget['L']}, N={budget['N']}, states={budget['states']}, full samples≤{budget['samples_upper_bound']}; {budget['availability']}: {budget['reason'] or 'bounded native decoder'}. FEC unsupported.")
    return messages
