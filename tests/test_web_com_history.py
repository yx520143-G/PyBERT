"""COM history reads actual saved artifacts without invoking a numerical worker."""

import copy
import json
import shutil
from pathlib import Path

import pytest

from pybert.web.server import create_app
from pybert.web.tasks import Tasks

EVIDENCE = (
    Path(__file__).resolve().parents[1] / "docs/webui/issue4/evidence/chrome-20261024"
)
SUCCESS = "e6e6867a-a976-4e47-a7bd-ee53767a2f9e"
FAILED = "c922f333-2a39-4fe3-abd0-5793c9bba535"
CANCELLED = "b6b85201-e481-4c69-98ce-c66650043535"
EARLY_CANCELLED = "a4dbc128-d042-43fd-b4a8-ede21c019527"


@pytest.fixture
def history(tmp_path):
    manager = Tasks(tmp_path)
    state = json.loads((EVIDENCE / "final-idle.json").read_text(encoding="utf-8"))
    for task in state["state"]["com_tasks"]:
        task_id = task["task_id"]
        directory = tmp_path / task_id
        directory.mkdir()
        for name in ("com-input.json", "com.json"):
            source = EVIDENCE / task_id / name
            if source.exists():
                shutil.copyfile(source, directory / name)
        manager.tasks[task_id] = {"data": copy.deepcopy(task), "directory": directory}
    endpoint = next(
        route.endpoint
        for route in create_app(manager).routes
        if route.path == "/api/com/{com_id}"
    )
    return manager, endpoint


@pytest.mark.parametrize(
    "task_id,input_status,result_status",
    [
        (SUCCESS, "available", "available"),
        (FAILED, "not_produced", "not_produced"),
        (CANCELLED, "available", "not_produced"),
        (EARLY_CANCELLED, "not_produced", "not_produced"),
    ],
)
def test_saved_com_history_preserves_actual_identity_logs_and_availability(
    history, task_id, input_status, result_status
):
    manager, endpoint = history
    original = copy.deepcopy(manager.get(task_id))
    data = endpoint(task_id)
    assert data["task"] == original
    assert data["saved_detail_status"] == {
        "input": input_status,
        "result": result_status,
    }
    if input_status == "available":
        expected = json.loads(
            (EVIDENCE / task_id / "com-input.json").read_text(encoding="utf-8")
        )
        assert data["saved_input"] == expected
        assert data["saved_input"]["com_id"] == task_id
        assert data["saved_input"]["parameter_source"]["parameters_sha256"]
        assert data["saved_input"]["versions"] and data["saved_input"]["source_hashes"]
    else:
        assert data["saved_input"] is None
    if task_id == SUCCESS:
        expected = json.loads(
            (EVIDENCE / task_id / "com.json").read_text(encoding="utf-8")
        )
        assert all(data[key] == value for key, value in expected.items())
        assert data["value_db"] == -15.419984103278814
    else:
        assert "value_db" not in data
    assert manager.get(task_id) == original and manager.active is None


def test_active_com_history_never_reads_unfinished_records(history):
    manager, endpoint = history
    entry = manager.tasks[CANCELLED]
    entry["data"].update(worker_exited=False, state="running")
    (entry["directory"] / "com-input.json").write_text('{"partial":', encoding="utf-8")
    data = endpoint(CANCELLED)
    assert data["saved_input"] is None
    assert data["saved_detail_status"] == {
        "input": "waiting_for_exit",
        "result": "waiting_for_exit",
    }


@pytest.mark.parametrize(
    "fault,status", [("partial", "unreadable"), ("wrong_com_id", "identity_mismatch")]
)
def test_com_history_missing_or_wrong_saved_metadata_is_explicit(
    history, fault, status
):
    manager, endpoint = history
    path = manager.tasks[CANCELLED]["directory"] / "com-input.json"
    path.write_text(
        '{"partial":' if fault == "partial" else json.dumps({"com_id": SUCCESS}),
        encoding="utf-8",
    )
    data = endpoint(CANCELLED)
    assert (
        data["saved_input"] is None and data["saved_detail_status"]["input"] == status
    )
    assert data["task"]["task_id"] == CANCELLED and "value_db" not in data
