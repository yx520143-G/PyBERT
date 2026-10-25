"""Bounded review of the fixed GUI producer and real Web worker; no product edits."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(r"C:\Users\yx\.codex\worktrees\pybert-final-parity\serial-bus-simulator")
DEPS = Path(r"E:\serial-bus-simulator-dependencies\pybert-issue28-rng-pin")
OUT = Path(__file__).resolve().parent
BASE = "1bc905d577d2f3bd9471421cfbf3d422d4e6080e"
HEAD = "0a7a03652a0f75f8032bf88cb588ca01fb751892"
NAMES = ("F-PAM4-01",)
sys.path[:0] = [str(ROOT / "src"), str(DEPS / "PyAMI/src"), str(DEPS / "PyChOpMarg/src")]
sys.dont_write_bytecode = True
os.environ["ETS_TOOLKIT"] = "null"
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def freeze():
    assert not (OUT / "freeze.json").exists()
    assert git("rev-parse", "HEAD^{tree}").strip() == git("rev-parse", HEAD + "^{tree}").strip()
    assert not git("status", "--porcelain")
    sources = {str(p): digest(p) for p in sorted((ROOT / "src/pybert").rglob("*"))
               if p.is_file() and p.suffix in (".py", ".js", ".html", ".css")}
    sources[str(Path(__file__).resolve())] = digest(Path(__file__).resolve())
    for sub in ("PyAMI", "PyChOpMarg"):
        sources.update({str(p): digest(p) for p in (DEPS / sub / "src").rglob("*.py")})
    fixtures = {}
    for name in NAMES:
        for suffix in (".json", ".yaml", ".extensions.json"):
            p = ROOT / "docs/webui/issue2/fixtures" / (name + suffix)
            fixtures[str(p)] = digest(p)
    packages = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    plan = dict(base=BASE, reviewed_candidate_head=HEAD, source_tree=git("rev-parse", HEAD + "^{tree}").strip(),
                execution_checkout_head=git("rev-parse", "HEAD").strip(), python=sys.executable,
                packages=packages, sources=sources, fixtures=fixtures,
                scope="Remaining original PAM4 fixture only: 1 GUI producer + 1 real spawned Web worker; NRZ saved results reused",
                physical_main_limit=2, numerical_com_limit=0, coopt_limit=0, ami_library_limit=0,
                full_default_com=False, real_ami_deferred=True,
                direct_entry="native load_configuration(original YAML), my_run_simulation(update_plots=True, initial_run=True)",
                web_entry="Tasks.start(run), actual spawn worker, join before publication",
                timeout_note="90 second soft checkpoint per fixture; worker wait 60 seconds; no hard-control development",
                comparison="all arrays: exact dtype/shape/C-order bytes, retain max absolute difference; input/window exact",
                gui_display="original GUI plotdata versus Web source arrays for responses, jitter, bathtub, 3 non-noisy eyes and CDR",
                exclusions=["performance timings", "channel-eye independent display noise", "different waveform/CDR rendering projections",
                            "GUI window/widget interactions", "unlicensed real AMI", "default COM full sweep"])
    (OUT / "commits.txt").write_text(git("log", BASE + ".." + HEAD, "--oneline"), encoding="utf-8")
    (OUT / "native-diff.patch").write_text(git("diff", BASE + "..." + HEAD, "--", "src/pybert/models", "src/pybert/utility",
                                               "src/pybert/pybert.py", "src/pybert/gui/plot.py", "src/pybert/threads/optimization.py",
                                               "PyAMI", "PyChOpMarg", "pyproject.toml"), encoding="utf-8")
    write("freeze.json", plan)
    print("FROZEN", digest(OUT / "freeze.json"), len(sources), flush=True)


def verify_freeze():
    plan = json.loads((OUT / "freeze.json").read_text(encoding="utf-8"))
    for mapping in (plan["sources"], plan["fixtures"]):
        for name, expected in mapping.items():
            assert digest(Path(name)) == expected, name
    assert sys.executable == plan["python"]
    return plan


def run():
    verify_freeze()
    import numpy as np
    import pybert
    import pyibisami
    import pychopmarg
    from pybert.pybert import PyBERT
    from pybert.models.bert import my_run_simulation
    from pybert.web.config import snapshot, input_hash
    from pybert.web.data import collect, plot_payload
    from pybert.web.tasks import Tasks

    assert Path(pybert.__file__).resolve().is_relative_to(ROOT / "src")
    assert Path(pyibisami.__file__).resolve().is_relative_to(DEPS / "PyAMI/src")
    assert Path(pychopmarg.__file__).resolve().is_relative_to(DEPS / "PyChOpMarg/src")
    report = dict(freeze_sha256=digest(OUT / "freeze.json"), modules={m.__name__: m.__file__ for m in (pybert, pyibisami, pychopmarg, np)},
                  fixtures=[], main_attempts=0, numerical_com_calls=0, coopt_calls=0, ami_library_calls=0)
    tasks = Tasks(OUT / "local/workers")
    start = time.perf_counter()

    def equal(label, a, b):
        a, b = np.asarray(a), np.asarray(b)
        shape = a.shape == b.shape
        exact = shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()
        delta = float(np.max(np.abs(a.astype(complex) - b.astype(complex)))) if shape and a.size else 0.0 if shape else None
        return dict(field=label, passed=exact, shape=list(a.shape), dtype=str(a.dtype), max_absolute_difference=delta)

    try:
        for name in NAMES:
            case_start = time.perf_counter()
            config = json.loads((ROOT / f"docs/webui/issue2/fixtures/{name}.json").read_text())
            assert config["seed"] == 1 and config["nbits"] == 15000 and config["nspui"] == 32
            assert not any(config[k] for k in ("enable_com", "rx_use_viterbi", "tx_use_ami", "rx_use_ami"))
            entry = dict(fixture=name, input_hash=input_hash(config), checks=[], display_checks=[], gui_views_absent=[], passed=False)
            report["fixtures"].append(entry)
            direct = OUT / "local" / name
            direct.mkdir(parents=True)
            print(name, "GUI producer", flush=True)
            p = PyBERT(run_simulation=False, gui=False)
            p.load_configuration(ROOT / f"docs/webui/issue2/fixtures/{name}.yaml")
            effective = snapshot(p)
            assert input_hash(effective) == input_hash(config), "Native YAML/effective mismatch"
            observations, decoding = {}, {}
            report["main_attempts"] += 1
            my_run_simulation(p, initial_run=True, update_plots=True, observations=observations, decoding=decoding)
            assert p.status == "Ready."
            assert time.perf_counter() - case_start < 90
            identity = dict(run_id="gui-producer-" + name, input_hash=input_hash(config), requested_input=config,
                            effective_input=effective, draft_revision=0)
            collect(p, observations, direct, identity, decoding=decoding)
            print(name, "Web worker", flush=True)
            report["main_attempts"] += 1
            task = tasks.start("run", {"config": config, "input_hash": input_hash(config)})
            task_id = task["task_id"]
            done = tasks.tasks[task_id]["done"].wait(60)
            if not done:
                tasks.cancel(task_id)
                tasks.tasks[task_id]["done"].wait(15)
                raise TimeoutError("Web worker exceeded frozen wait; no further fixtures")
            final = tasks.get(task_id)
            entry["task"] = final
            assert final["state"] == "succeeded" and final["worker_exited"] and final["exitcode"] == 0, final
            web = tasks.directory(task_id)
            with np.load(direct / "arrays.npz") as a, np.load(web / "arrays.npz") as b:
                assert set(a.files) == set(b.files)
                entry["checks"] = [equal(key, a[key], b[key]) for key in a.files]
                for point in ("chnl", "tx", "tx_out", "ctle", "ctle_out", "dfe", "dfe_out"):
                    for kind in ("h", "s", "p", "H"):
                        key = point + "_" + kind
                        if key not in p.plotdata.list_data():
                            entry["gui_views_absent"].append(key)
                            continue
                        entry["display_checks"].append(equal("GUI " + key, p.plotdata.get_data(key), b["display." + key + ".y"]))
                for point in ("chnl", "tx", "ctle", "dfe"):
                    for kind in ("jitter", "jitter_ext", "jitter_spectrum", "jitter_ind_spectrum", "thresh"):
                        key = kind + "_" + point
                        view = (f"display.pdf.{point}.{kind}.y" if kind in ("jitter", "jitter_ext")
                                else f"display.spec.{point}.{kind}.y")
                        entry["display_checks"].append(equal("GUI " + key, p.plotdata.get_data(key), b[view]))
                    entry["display_checks"].append(equal("GUI bathtub_" + point, p.plotdata.get_data("bathtub_" + point),
                                                        b[f"display.bathtub.{point}.y"]))
                for point, native in (("tx", "eye_tx"), ("ctle", "eye_ctle"), ("dfe", "eye_dfe")):
                    entry["display_checks"].append(equal("GUI " + native, p.plotdata.get_data(native), b[f"eye.{point}.counts"]))
                entry["display_checks"].append(equal("GUI CDR histogram", p.plotdata.get_data("clk_per_hist_vals"), b["cdr.histogram.counts"]))
                entry["display_checks"].append(equal("GUI CDR spectrum", p.plotdata.get_data("clk_spec"), b["display.cdr.spectrum.y"]))
            a = json.loads((direct / "manifest.json").read_text())
            b = json.loads((web / "manifest.json").read_text())
            sa, sb = dict(a["summary"]), dict(b["summary"])
            sa.pop("performance_Msamples_per_min")
            sb.pop("performance_Msamples_per_min")
            entry["summary"] = sa
            entry["summary_equal_excluding_performance"] = sa == sb
            entry["input_and_window_equal"] = a["input_hash"] == b["input_hash"] and a["window"] == b["window"]
            entry["plot_payloads"] = {key: len(plot_payload(web, key).get("data", [])) for key in
                                      ("wave.rx_in", "chnl_H", "jitter.dfe.dist", "jitter.dfe.bathtub", "eye.dfe", "cdr.histogram")}
            entry["elapsed_seconds"] = time.perf_counter() - case_start
            entry["passed"] = (all(x["passed"] for x in entry["checks"] + entry["display_checks"])
                               and entry["summary_equal_excluding_performance"] and entry["input_and_window_equal"])
            write("numerical-report.json", report)
            print(name, entry["passed"], len(entry["checks"]), len(entry["display_checks"]), flush=True)
            assert entry["passed"], "Exact comparison failed; preserve results and stop"
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        report["traceback"] = traceback.format_exc()
        raise
    finally:
        report["elapsed_seconds"] = time.perf_counter() - start
        write("numerical-report.json", report)


if __name__ == "__main__":
    if sys.argv[1] == "freeze":
        freeze()
    elif sys.argv[1] == "run":
        run()
    else:
        raise SystemExit("freeze or run required")
