"""Content identities for explicitly supplied local resources; never infer a cwd."""

import copy
import hashlib
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Resources:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.items = {}

    def model_bundle(self, files, source):
        """Store explicit files as one content identity, preserving relative dependencies."""
        if not files or len(files) > 256:
            raise ValueError("Model bundle requires 1..256 explicitly supplied files.")
        content = {}
        for name, data in files:
            name = name.replace("\\", "/")
            if (name.startswith("/") or ":" in name or any(p in ("", ".", "..") for p in name.split("/"))
                    or name.casefold() in {p.casefold() for p in content}):
                raise ValueError("Model bundle paths must be unique safe relative paths.")
            if not data or len(data) > 64 * 1024**2:
                raise ValueError("Model file is empty or exceeds 64 MiB.")
            content[name] = data
        if sum(map(len, content.values())) > 256 * 1024**2:
            raise ValueError("Model bundle exceeds 256 MiB.")
        manifest = [{"relative_path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                    for name, data in sorted(content.items())]
        import json

        sha = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        resource_id = sha + ".model"
        directory = self.root / resource_id
        for name, data in content.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != data:
                raise ValueError("Stored model resource content mismatch.")
            path.write_bytes(data)
        row = {"resource_id": resource_id, "sha256": sha, "format": ".model", "files": manifest,
               "bytes": sum(map(len, content.values())), "source": source, "original_name": "model bundle",
               "permission": "explicitly supplied for this local session", "parse_status": "not checked; binary loading requires a child task"}
        self.items[resource_id] = row
        return copy.deepcopy(row)

    def local_model(self, directory):
        base = Path(directory)
        if not base.is_absolute() or not base.is_dir():
            raise ValueError("Model bundle needs an explicit existing absolute directory.")
        base = base.resolve()
        paths = sorted(p for p in base.rglob("*") if p.is_file())
        if any(not p.resolve().is_relative_to(base) for p in paths):
            raise ValueError("Model dependency escapes the explicit bundle directory.")
        return self.model_bundle([(p.relative_to(base).as_posix(), p.read_bytes()) for p in paths],
                                 {"kind": "local_directory", "path": str(base)})

    def for_models(self, config, bindings):
        rows = []
        for side in ("tx", "rx"):
            field = side + "_model_bundle"
            rid = bindings.get(field)
            active = config.get(side + "_sel") == "ibis" or config.get(side + "_eq_sel") == "IBIS-AMI"
            if not rid:
                if active:
                    raise ValueError(f"{side}: model resource unbound; explicitly bind the complete model directory.")
                continue
            row = copy.deepcopy(self.items.get(rid))
            if not row or row["format"] != ".model":
                raise ValueError(f"{side}: model resource unavailable; rebind original content.")
            directory = self.root / rid
            for file in row["files"]:
                if digest(directory / file["relative_path"]) != file["sha256"]:
                    raise ValueError(f"{side}: model dependency hash mismatch.")
            row.update(field=field, index=None, reference=config.get(side + "_ibis_file", ""), worker_path=str(directory))
            rows.append(row)
        return rows

    def add(self, name, content, source):
        name = Path(name.replace("\\", "/")).name
        suffix = Path(name).suffix.lower()
        if not re.fullmatch(r"\.s(?:1|2|4|8|12)p|\.(?:csv|txt|xls|xlsx)", suffix):
            raise ValueError(
                "Resource format must be Touchstone, csv/txt, or COM xls/xlsx."
            )
        if not content:
            raise ValueError("Empty resources are not valid inputs.")
        sha = hashlib.sha256(content).hexdigest()
        resource_id = f"{sha}{suffix}"
        path = self.root / resource_id
        if not path.exists():
            path.write_bytes(content)
        if digest(path) != sha:
            raise ValueError("Stored resource content hash mismatch.")
        row = {
            "resource_id": resource_id,
            "original_name": name,
            "format": suffix,
            "bytes": len(content),
            "sha256": sha,
            "source": source,
            "permission": "explicitly supplied for this local session",
            "parse_status": "pending task validation",
            "intended_uses": ["COM configuration"]
            if suffix in (".xls", ".xlsx")
            else ["channel", "COM THRU"]
            if suffix == ".s4p"
            else ["channel"],
        }
        self.items[resource_id] = row
        return copy.deepcopy(row)

    def local(self, filename):
        path = Path(filename)
        if not path.is_absolute():
            raise ValueError("Local registration requires an explicit absolute path.")
        path = path.resolve(strict=True)
        return self.add(
            path.name, path.read_bytes(), {"kind": "local_path", "path": str(path)}
        )

    def freeze(self, resource_id, field, reference, index=None):
        if resource_id not in self.items:
            raise ValueError(
                f"{field}: resource is unbound/unavailable; upload or register its path explicitly."
            )
        row = copy.deepcopy(self.items[resource_id])
        path = self.root / resource_id
        if digest(path) != row["sha256"]:
            raise ValueError(f"{field}: frozen resource was modified (hash mismatch).")
        row.update(field=field, index=index, reference=reference, worker_path=str(path))
        return row

    def for_run(self, config, bindings):
        rows = self.for_models(config, bindings)
        if config["inter_sel"] == "single":
            rows.append(
                self.freeze(bindings.get("ch_file"), "ch_file", config["ch_file"])
            )
        elif config["inter_sel"] == "multiple":
            ids = bindings.get("ch_files", [])
            if not config["ch_files"] or len(ids) != len(config["ch_files"]):
                raise ValueError(
                    "ch_files: bind every ordered element, including duplicates."
                )
            rows.extend(
                self.freeze(rid, "ch_files", ref, i)
                for i, (rid, ref) in enumerate(zip(ids, config["ch_files"]))
            )
        if config["enable_com"] and config["com_cfg_file"]:
            rows.append(
                self.freeze(
                    bindings.get("com_cfg_file"), "com_cfg_file", config["com_cfg_file"]
                )
            )
        return rows

    def bind_base(self, config, base_directory):
        base = Path(base_directory)
        if not base.is_absolute() or not base.is_dir():
            raise ValueError(
                "An explicit existing absolute YAML base directory is required."
            )
        bindings = {}
        fields = (
            ["ch_file"]
            if config.get("inter_sel") == "single"
            else ["ch_files"]
            if config.get("inter_sel") == "multiple"
            else []
        )
        if config.get("enable_com") and config.get("com_cfg_file"):
            fields.append("com_cfg_file")
        for field in fields:
            refs = (
                config.get(field, [])
                if field == "ch_files"
                else [config.get(field, "")]
            )
            ids = [
                self.local(str((base / ref).resolve()))["resource_id"] for ref in refs
            ]
            bindings[field] = ids if field == "ch_files" else ids[0]
        return bindings


def projection(config, rows):
    result = copy.deepcopy(config)
    result["enable_com"] = False  # COM is a separate, joined child task.
    for row in rows:
        if row["field"] == "ch_files":
            result["ch_files"][row["index"]] = row["worker_path"]
        elif row["field"] == "ch_file":
            result["ch_file"] = row["worker_path"]
    return result


def inspect_channels(config, rows):
    """Read content/port metadata in the same worker as the consuming engine."""
    import numpy as np
    from skrf import Network
    from pybert.utility.sparam import _lane_through_ports

    report = []
    for row in rows:
        if digest(Path(row["worker_path"])) != row["sha256"]:
            raise ValueError("Worker resource content hash mismatch.")
        if row["field"] not in ("ch_file", "ch_files"):
            continue
        suffix = row["format"]
        if suffix in (".csv", ".txt"):
            raise ValueError(
                "Time-domain channel import is blocked pending native H_2_s2p/step-impulse semantic validation; resource retained."
            )
        if row["field"] == "ch_files" and suffix != ".s4p":
            raise ValueError(
                "Ordered cascade supports native single-ended .s4p segments only."
            )
        net = Network(row["worker_path"])
        n = net.nports
        if (
            suffix != f".s{n}p"
            or n not in (1, 2, 4, 8, 12)
            or not np.isfinite(net.s).all()
        ):
            raise ValueError(
                "Touchstone content/port count or finite S data is invalid."
            )
        if (
            len(net.f) < 2
            or not np.all(np.diff(net.f) > 0)
            or not np.isfinite(net.z0).all()
        ):
            raise ValueError(
                "Touchstone needs a finite strictly increasing frequency axis and finite z0."
            )
        lane = config["lane_sel"] if row["field"] == "ch_file" and n >= 8 else 0
        if n >= 8 and not 0 <= lane < n // 4:
            raise ValueError(f"Victim lane {lane} is outside 0..{n // 4 - 1}.")
        ports = list(range(4 * lane, 4 * lane + 4)) if n >= 4 else list(range(n))
        actual = _lane_through_ports(net, lane, config["renumber"]) if n >= 4 else ports
        swap = actual != ports
        lane_ports = (
            [_lane_through_ports(net, j, config["renumber"]) for j in range(n // 4)]
            if n >= 8
            else []
        )
        report.append(
            {
                **row,
                "ports": n,
                "frequency_hz": [float(net.f[0]), float(net.f[-1])],
                "frequency_samples": len(net.f),
                "s_unit": "dimensionless complex",
                "z0_unit": "ohm",
                "victim_lane": lane,
                "port_mapping_0based": actual,
                "renumber_swapped_1_2": bool(swap),
                "requested_fmax_hz": config["f_max"] * 1e9,
                "coverage": "covered"
                if net.f[-1] >= config["f_max"] * 1e9
                else "native extrapolation above resource fmax",
                "interpolation": "native interp_s2p: polar interpolation; reflection extrapolation capped to unit magnitude; transmission fill_value=0 outside coverage",
                "native_mapping": "corrected #13 interleaved caller; source-lane through detection only",
                "input_pair_0based": [actual[0], actual[2]] if n >= 4 else None,
                "output_pair_0based": [actual[1], actual[3]] if n >= 4 else None,
                "parse_status": "validated for this task and frequency grid",
                "renumber_requested": config["renumber"],
                "use_window": config["use_window"],
                "window_policy": "native raised_cosine before irfft when enabled; stored chnl_H remains pre-window",
                "fext_path_status": "active"
                if config["include_fext"] and n >= 8
                else "inactive",
                "termination_policy": {
                    "kind": "package" if config["pkg_enable"] else "ordinary lumped",
                    "rs_ohm": config["rs"],
                    "cout_pf": config["cout"],
                    "rin_ohm": config["rin"],
                    "cin_pf": config["cin"],
                    "package_group": config["pkg_group"]
                    if config["pkg_enable"]
                    else None,
                    "tx_case": config["tx_pkg_case"] if config["pkg_enable"] else None,
                    "rx_case": config["rx_pkg_case"] if config["pkg_enable"] else None,
                    "include_host": config["pkg_include_host"]
                    if config["pkg_enable"]
                    else None,
                    "ordinary_values_active": not config["pkg_enable"],
                },
                "aggressors": [
                    {
                        "lane": j,
                        "port_mapping_0based": [
                            lane_ports[j][0],
                            actual[1],
                            lane_ports[j][2],
                            actual[3],
                        ],
                    }
                    for j in range(n // 4)
                    if j != lane
                ]
                if n >= 8
                else [],
            }
        )
    if config["include_fext"] and (
        config["inter_sel"] != "single"
        or not report
        or report[0]["ports"] not in (8, 12)
    ):
        raise ValueError("FEXT requires one actual .s8p/.s12p channel.")
    return report
