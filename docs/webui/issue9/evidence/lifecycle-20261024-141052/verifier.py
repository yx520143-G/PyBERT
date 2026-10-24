"""Bounded real cancellation and explicitly injected decoder/producer failures."""

import json
import shutil
import time
from pathlib import Path

from pybert.web.archive import json_bytes, sha256
from pybert.web.data import source_identity
from pybert.web.tasks import BusyError, Tasks
from pybert.web.worker import run_worker

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/webui/issue9/fixtures/v1"
SAVED = ROOT / "docs/webui/issue9/evidence/numerics-20261024-140115/local/V-NRZ-ISI/saved.pybert_run"


def fault_worker(task_id, operation, request, directory, cancel, pipe):
    """Test-only fault injection in the same child and original run pipeline."""
    import pybert.models.bert as bert

    def fail(*_args, **_kwargs):
        raise RuntimeError(f"injected_native_{request['fault_injection']}_failure")

    if request["fault_injection"] == "decoder":
        bert.ViterbiDecoder_ISI.decode = fail
    else:
        bert.update_trellis = fail
    run_worker(task_id, operation, request, directory, cancel, pipe)


def main():
    output = ROOT / "docs/webui/issue9/evidence" / time.strftime("lifecycle-%Y%m%d-%H%M%S")
    output.mkdir(parents=True)
    report = {"source_identity": source_identity(), "main_calls": 0, "COM_calls": 0, "cases": {}}
    for relative in report["source_identity"]:
        target = output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / relative, target)
    shutil.copyfile(__file__, output / "verifier.py")
    (output / "before-execution.json").write_bytes(json_bytes(report))
    for fault in ("decoder", "trellis", "cancel"):
        manager = Tasks(output / "local" / fault, worker=run_worker if fault == "cancel" else fault_worker)
        old = manager.references.add(SAVED.read_bytes(), "old.pybert_run")
        before = manager.references.index()
        request = json.loads((FIXTURES / ("V-CANCEL.json" if fault == "cancel" else "V-NRZ-ISI.json")).read_text(encoding="utf-8"))
        if fault != "cancel":
            request["fault_injection"] = fault
        task = manager.start("run", request)
        report["main_calls"] += 1
        entry = manager.tasks[task["task_id"]]
        events = []
        requested = False
        started = time.time()
        while not entry["done"].wait(.01):
            status = manager.get(task["task_id"])
            if not events or status["phase"] != events[-1]["phase"]:
                events.append({"time": time.time(), **status})
            if fault == "cancel" and not requested and status["phase"] == "Running Viterbi...":
                requested = True
                request_state = manager.cancel(task["task_id"])
                try:
                    manager.start("normalize", {"mode": "defaults"})
                    busy = False
                except BusyError:
                    busy = True
                events.append({"time": time.time(), **request_state, "slot_refused_new_worker": busy})
            if time.time() - started > 180:
                raise RuntimeError("Lifecycle exceeded frozen 180s bound; not passed")
        final = manager.get(task["task_id"])
        row = {"events": events, "final": final, "old_record_id": old["record_id"],
               "old_success_retained": before == manager.references.index(),
               "elapsed_s": time.time()-started, "peak_working_set_bytes": None,
               "peak_reason": "not sampled for lifecycle batch", "main_calls": 1}
        if fault == "cancel":
            row["passed"] = (requested and final["state"] == "cancelled" and final["cancel_requested"]
                             and final["cancel_observed"] and final["worker_exited"] and final["exitcode"] == 0
                             and any(e.get("slot_refused_new_worker") for e in events))
        else:
            row["passed"] = final["state"] == "failed" and f"injected_native_{fault}_failure" in final["error"] and final["worker_exited"] and not manager.runs
        row["passed"] &= row["old_success_retained"]
        report["cases"][fault] = row
        (output / "report.json").write_bytes(json_bytes(report))
        print(json.dumps({"case": fault, "passed": row["passed"], "state": final["state"], "output": str(output)}), flush=True)
    print(str(output), flush=True)


if __name__ == "__main__":
    main()
