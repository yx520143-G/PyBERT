"""Declaration-aware auxiliary histories; no simulation or model DLL is run."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from pybert.models.bert import getwave_parameters
from pyibisami.ami.configurator import AMIParamConfigurator
from traits.api import Dict, HasTraits


def config(model_specific="", reserved=""):
    return AMIParamConfigurator(f"""(rx
        (Reserved_Parameters (GetWave_Exists (Usage Info) (Type Boolean) (Value True))
            (Init_Returns_Impulse (Usage Info) (Type Boolean) (Value True)) {reserved})
        {f'(Model_Specific {model_specific})' if model_specific else ''})""")


def test_auxiliary_key_changes_keep_complete_independent_histories_and_raw():
    raw = ["(rx (gain 1) (tap_note 3))", "(rx (gain 2) (later 4))"]
    observation = {}
    values, taps = getwave_parameters(raw, config(), observations=observation)
    assert values == {("gain",): [1., 2.]}
    assert taps == []
    assert observation["parameter_strings"] == raw
    assert observation["unavailable_paths"] == [["later"], ["tap_note"]]
    assert observation["tap_status"] == "unavailable"
    assert observation["status"] == "partial"


def test_numeric_looking_strings_and_table_row_counts_do_not_become_tap_columns():
    cfg = config('''(tap_label (Usage Out) (Type String) (Value "1"))
        (table (Usage Out) (Type Float Float) (Table (1 2)))''')
    raw = ['(rx (tap_label "1") (table 1 2))', '(rx (tap_label "2") (table 1 2 3 4))']
    values, taps = getwave_parameters(raw, cfg)
    assert values == {} and taps == []


@pytest.mark.parametrize("payload", ["", "(child 2)", "(1 2)"])
def test_required_table_must_return_nonempty_leaf_values(payload):
    cfg = config("(table (Usage Out) (Type Float Float) (Table (1 2)))")
    with pytest.raises(ValueError, match="required"):
        getwave_parameters([f"(rx (table {payload}))"], cfg)


@pytest.mark.parametrize("usage", ["Out", "InOut"])
@pytest.mark.parametrize("later", ["(rx)", "(rx (gain))", "(rx (gain Missing))", ""])
def test_required_numeric_output_cannot_be_downgraded_to_unavailable(usage, later):
    cfg = config(f"(gain (Usage {usage}) (Type Float) (Value 1))")
    observation = {}
    raw = ["(rx (gain 1))", later]
    with pytest.raises(ValueError, match="required|numeric"):
        getwave_parameters(raw, cfg, observations=observation)
    assert observation["parameter_strings"] == raw
    assert observation["status"] == "partial"


@pytest.mark.parametrize("malformed", ["(1 2)", "(child 2)"])
def test_required_scalar_cannot_be_returned_as_a_row_or_branch(malformed):
    cfg = config("(gain (Usage Out) (Type Float) (Value 1))")
    with pytest.raises(ValueError, match="required"):
        getwave_parameters([f"(rx (gain {malformed}))"], cfg)


def test_expected_root_is_checked_even_for_one_call():
    with pytest.raises(ValueError, match="root"):
        getwave_parameters(["(other)"], config())


def test_reserved_required_output_is_checked_too():
    cfg = config(reserved="(PAM4_UpperThreshold (Usage Out) (Type Float) (Value 0.2))")
    with pytest.raises(ValueError, match="required"):
        getwave_parameters(["(rx)"], cfg)


def test_one_declared_tap_group_is_ordered_by_position_and_keeps_all_rows():
    cfg = config("""(dfe
        (10 (Usage Out) (Type Tap) (Value 0))
        (2 (Usage Out) (Type Tap) (Value 0)))""")
    observation = {}
    values, taps = getwave_parameters([
        "(rx (dfe (10 10 20) (2 1 2)) (tap_temperature 31))",
        "(rx (dfe (10 30) (2 3)) (tap_temperature 32))",
    ], cfg, observations=observation)
    assert values[("dfe", "2")] == [1., 2., 3.]
    assert taps == [[1., 10.], [2., 20.], [3., 30.]]
    assert observation["tap_status"] == "available"
    assert observation["tap_paths"] == [["dfe", "2"], ["dfe", "10"]]


@pytest.mark.parametrize("extra_row", ["", "(99 9)"])
def test_declared_numeric_taps_can_share_a_branch_with_named_parameters(extra_row):
    cfg = config("""(dfe (1 (Usage Out) (Type Tap) (Value 0))
        (2 (Usage Out) (Type Tap) (Value 0)) (gain (Usage Out) (Type Float) (Value 1)))""")
    raw = [f"(rx (dfe (1 1) (2 2) (gain 3) {extra_row}))"]
    if extra_row:
        with pytest.raises(ValueError, match="mixed"):
            getwave_parameters(raw, cfg)
    else:
        values, taps = getwave_parameters(raw, cfg)
        assert values == {("dfe", "1"): [1.], ("dfe", "2"): [2.], ("dfe", "gain"): [3.]}
        assert taps == [[1., 2.]]


def test_misaligned_declared_taps_only_disable_the_matrix():
    cfg = config("(dfe (1 (Usage Out) (Type Tap) (Value 0)) (2 (Usage Out) (Type Tap) (Value 0)))")
    observation = {}
    values, taps = getwave_parameters(["(rx (dfe (1 1 2) (2 10)) (gain 7))"], cfg,
                                      observations=observation)
    assert values == {("dfe", "1"): [1., 2.], ("dfe", "2"): [10.], ("gain",): [7.]}
    assert taps == [] and observation["tap_reason"] == "unaligned_columns"


def test_distinct_declared_groups_are_never_zipped_together():
    cfg = config("""(left (1 (Usage Out) (Type Tap) (Value 0)))
                    (right (1 (Usage Out) (Type Tap) (Value 0)))""")
    observation = {}
    values, taps = getwave_parameters(["(rx (left (1 1 2)) (right (1 3)))"], cfg,
                                      observations=observation)
    assert len(values) == 2 and taps == []
    assert observation["tap_reason"] == "multiple_declared_groups"


def test_unparseable_declarations_do_not_claim_required_outputs_verified():
    cfg = SimpleNamespace(input_ami_params={"root_name": "rx"},
                          ami_parsing_errors=["Skipped parameter gain: invalid Type"], ami_param_defs={})
    with pytest.raises(ValueError, match="declaration"):
        getwave_parameters(["(rx)"], cfg)


def test_empty_model_specific_branch_does_not_make_valid_wave_observations_fail():
    cfg = config(" ")  # The current parser warns even for this empty container.
    assert "Skipped parameter Model_Specific: No tags or subparameters." in cfg.ami_parsing_errors
    assert getwave_parameters(["(rx)"], cfg) == ({}, [])


@pytest.mark.parametrize("traits_dict", [False, True])
def test_actual_rx_consumer_keeps_raw_and_does_not_fabricate_diagnostic_arrays(traits_dict):
    class Owner(HasTraits):
        info = Dict()

    info = Owner().info if traits_dict else {}
    source = Path(__file__).parents[1] / "src/pybert/models/bert.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "my_run_simulation")
    projection = next(node for node in ast.walk(main) if isinstance(node, ast.Assign)
                      and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                      and node.value.func.id == "getwave_parameters")
    statements = next(node.body for node in ast.walk(main) if isinstance(node, ast.If) and projection in node.body)
    # Execute the real consumer statements following the already completed AMI call.
    body = statements[statements.index(projection):]
    raw = ["(rx (gain 1) (cdr_locked 1) (tap_a 2))", "(rx (gain 2))"]
    tap_weights, lockeds, ui_estimates = object(), object(), object()
    context = {"getwave_parameters": getwave_parameters, "params": raw, "clock_info": info,
               "self": SimpleNamespace(_rx_cfg=config()), "tap_weightss": tap_weights,
               "lockeds": lockeds, "ui_ests": ui_estimates}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(source), "exec"), context)  # noqa: S102 - local source only.
    assert context["param_vals"] == {("gain",): [1., 2.]}
    assert info["parameter_history"]["parameter_strings"] == raw
    assert info["parameter_history"]["unavailable_paths"] == [["cdr_locked"], ["tap_a"]]
    assert info["model_lock_status"] == "unavailable"
    assert context["tap_weightss"] is tap_weights
    assert context["lockeds"] is lockeds and context["ui_ests"] is ui_estimates


def test_declared_table_does_not_hide_mixed_structure_errors():
    cfg = config("(table (Usage Out) (Type Float Float) (Table (1 2)))")
    with pytest.raises(ValueError, match="mixed"):
        getwave_parameters(["(rx (table 1 (child 2)))"], cfg)
