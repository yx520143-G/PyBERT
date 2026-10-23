"""Native configuration snapshots and ordered edits, used only inside a worker."""

import hashlib
import json
import math
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


def validate(config, defaults, complete=True):
    """Reject unsupported active paths before any resource observer can load them."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object.")  # noqa: TRY004 - HTTP input validation contract
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
        "mod_type": ("NRZ", "PAM-4"),
        "tx_sel": ("native",),
        "rx_sel": ("native",),
        "tx_eq_sel": ("Native",),
        "rx_eq_sel": ("Native",),
        "inter_sel": ("native",),
    }.items():
        if c[key] not in values:
            raise ValueError(f"{key}={c[key]} is not supported in #2; see #4/#10.")
    for key in (
        "include_fext",
        "pkg_enable",
        "enable_com",
        "rx_use_viterbi",
        "tx_use_ami",
        "rx_use_ami",
        "tx_use_ts4",
        "rx_use_ts4",
    ):
        if c[key]:
            raise ValueError(f"{key}: active capability is not supported in #2.")
    if c["impulse_length"] != 0:
        raise ValueError("impulse_length: only native automatic length is supported in #2.")
    if c["ctle_enable"] and c["ctle_sel"] != "Native":
        raise ValueError("ctle_sel=File with CTLE enabled is blocked by the native File path; see #4.")


def yaml_text(config):
    cfg = PyBertCfg.__new__(PyBertCfg)
    cfg.__dict__.update(date_created="", version=__version__, **config)
    for key in TABLES:
        cfg.__dict__[key] = [tuple(row) for row in config[key]]
    return yaml.dump(cfg, sort_keys=False, allow_unicode=True)


class ConfigLoader(yaml.SafeLoader):
    """Accept just the native config and tuple tags, never arbitrary Python objects."""


ConfigLoader.add_constructor("tag:yaml.org,2002:python/tuple", lambda loader, node: loader.construct_sequence(node))
ConfigLoader.add_constructor(
    "tag:yaml.org,2002:python/object:pybert.configuration.PyBertCfg",
    lambda loader, node: loader.construct_mapping(node, deep=True),
)


def parse_yaml(text):
    value = yaml.load(text, Loader=ConfigLoader)
    if not isinstance(value, dict):
        raise ValueError("Expected native PyBertCfg YAML.")  # noqa: TRY004 - HTTP input validation contract
    return {k: v for k, v in value.items() if k not in ("version", "date_created")}


def load_config(engine, config, defaults=None):
    """Reuse native full-load ordering and tap restoration; inactive paths stay inert."""
    defaults = defaults or snapshot(new_engine())
    validate(config, defaults)
    # PyBertCfg order puts dimensions before the complete saved tap lists.
    ordered = {key: config[key] for key in defaults}
    ordered.update({key: int(ordered[key]) for key in INTEGERS})
    paths = {key: ordered[key] for key in RESOURCE_FIELDS}
    ordered.update({key: "" for key in RESOURCE_FIELDS})
    with tempfile.TemporaryDirectory(prefix="pybert-config-") as tmp:
        path = Path(tmp) / "input.yaml"
        path.write_text(yaml_text(ordered), encoding="utf-8")
        engine.load_configuration(path)
    engine.trait_setq(**paths)
    validate(snapshot(engine), defaults)
    return engine


def normalize(request):
    """A full load or an ordered observer patch; each call owns one fresh engine."""
    engine = new_engine()
    defaults = snapshot(engine)
    mode = request.get("mode", "load")
    if mode == "defaults":
        pass
    elif mode == "load":
        supplied = parse_yaml(request["yaml"]) if "yaml" in request else request["config"]
        validate(supplied, defaults, complete=False)
        load_config(engine, defaults | supplied, defaults)
    elif mode == "patch":
        load_config(engine, request["config"], defaults)
        for edit in request["patches"]:
            key, value = edit["field"], edit["value"]
            before = snapshot(engine)
            # Ntaps observer may clamp Npre; validate that derived pair after the edit.
            proposed = before | {key: value}
            if key == "rx_n_taps" and isinstance(value, int):
                proposed["rx_n_pre"] = min(before["rx_n_pre"], max(0, value - 1))
            validate(proposed, defaults)
            if key in TABLES or key in RESOURCE_FIELDS:
                load_config(engine, proposed, defaults)
            else:
                setattr(engine, key, value)
            validate(snapshot(engine), defaults)
    else:
        raise ValueError(f"Unknown normalize mode {mode}.")
    config = snapshot(engine)
    return {
        "config": config,
        "input_hash": input_hash(config),
        "input_hash_schema": "native-json-v1-integral-floats",
        "yaml": yaml_text(config),
        "warnings": warnings(config),
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
    return messages
