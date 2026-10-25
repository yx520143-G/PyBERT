"""Exercise the production AMI wrapper with a Python ABI stand-in; never load a DLL."""

import ast
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from pyibisami.ami import model as ami
from pybert.utility import ibisami


class FakeDLL:
    """Record real wrapper chunks and retain state until the final Close."""

    def __init__(self):
        self.events = []
        self.samples = 0
        self.fail_at = None
        self.close_error = None
        self.close_status = 1
        self.AMI_Close = lambda handle: self._close(handle)

    def AMI_Init(self, impulse, rows, aggressors, ts, ui, params, out_params, handle, message):
        assert out_params._obj.value is None
        self.events.append(("init", tuple(impulse._obj), rows, aggressors))
        self.ts = ts.value
        handle._obj.value = b"one-handle"
        out_params._obj.value = b"(model)"
        message._obj.value = b"initialized"
        return 0 if self.fail_at == "init" else 1

    def AMI_GetWave(self, wave, size, clocks, out_params, handle):
        assert handle.value == b"one-handle"
        assert out_params._obj.value is None
        self.events.append(("wave", np.array(wave._obj), self.samples))
        assert np.all(np.isnan(clocks._obj))
        clocks._obj[0] = self.samples * self.ts
        clocks._obj[1] = -1.
        wave._obj[:] = np.array(wave._obj) + self.samples / 1000
        self.samples += size
        out_params._obj.value = b"(model (tap 0.25))"
        return 0 if self.fail_at == len([event for event in self.events if event[0] == "wave"]) else 1

    def _close(self, handle):
        assert handle.value == b"one-handle"
        self.events.append(("close",))
        if self.close_error:
            raise self.close_error
        return self.close_status


@pytest.fixture
def setup_model(monkeypatch):
    dll = FakeDLL()
    loads, rng_calls, models, python_calls = [], [], [], []
    original_model, original_getwave = ami.AMIModel, ami.AMIModel.getWave
    original_rng = np.random.default_rng

    def load(filename):
        loads.append(filename)
        return dll

    def construct(filename):
        model = original_model(filename)
        models.append(model)
        return model

    def getwave(model, wave, bits_per_call=0):
        python_calls.append((model, np.array(wave), bits_per_call))
        return original_getwave(model, wave, bits_per_call=bits_per_call)

    def rng(*args, **kwargs):
        rng_calls.append((args, kwargs))
        return original_rng(912)  # Test-only capture; production must request fresh entropy without arguments.

    monkeypatch.setattr(ami, "CDLL", load)
    monkeypatch.setattr(ibisami, "AMIModel", construct)
    monkeypatch.setattr(ami.AMIModel, "getWave", getwave)
    monkeypatch.setattr(ami, "default_rng", rng)
    cfg = SimpleNamespace(input_ami_params={"root_name": "model"},
                          info_ami_params={"GetWave_Exists": SimpleNamespace(pvalue=True),
                                           "Init_Returns_Impulse": False,
                                           "Ignore_Bits": SimpleNamespace(pvalue=23)},
                          fetch_param_val=lambda path: True)
    channel = np.r_[.75, .25, np.zeros(78)]
    main = np.linspace(-.5, .5, 166)
    return SimpleNamespace(dll=dll, loads=loads, rng_calls=rng_calls, models=models,
                           python_calls=python_calls, cfg=cfg, channel=channel, main=main)


def run(case, bits_per_call=0, **kwargs):
    return ibisami.run_ami_model("fake-only", case.cfg, True, 1., .25,
                                case.channel, case.main, bits_per_call=bits_per_call, **kwargs)


@pytest.mark.parametrize("block,main_chunks", [(0, [160, 6]), (7, [28, 28, 28, 28, 28, 26])])
def test_original_probe_then_main_on_one_handle(setup_model, block, main_chunks):
    case = setup_model
    global_rng_before = np.random.get_state()
    result = run(case, block)
    assert case.loads == ["fake-only"]
    assert [event[0] for event in case.dll.events] == ["init"] + ["wave"] * (4 + len(main_chunks)) + ["close"]
    calls = case.python_calls
    assert len(calls) == 3 and all(call[0] is case.models[0] for call in calls)
    assert [call[2] for call in calls] == [40, 40, block]
    assert len(calls[0][1]) == (23 + 20) * 4
    np.testing.assert_array_equal(calls[1][1], np.convolve(calls[0][1], case.channel)[:len(calls[0][1])])
    np.testing.assert_array_equal(calls[2][1], case.main)
    chunks = [event for event in case.dll.events if event[0] == "wave"]
    assert [len(event[1]) for event in chunks] == [160, 12, 160, 12] + main_chunks
    assert chunks[4][2] == 344  # Both complete probe records were consumed before Main.
    expected = np.concatenate([event[1] + event[2] / 1000 for event in chunks[4:]])
    np.testing.assert_array_equal(result[0], expected)
    np.testing.assert_array_equal(result[1], [event[2] * .25 for event in chunks[4:]])
    assert case.rng_calls == [((), {})]
    global_rng_after = np.random.get_state()
    assert global_rng_before[0] == global_rng_after[0]
    np.testing.assert_array_equal(global_rng_before[1], global_rng_after[1])
    assert global_rng_before[2:] == global_rng_after[2:]
    case.models[0].close()
    assert len([event for event in case.dll.events if event[0] == "close"]) == 1


@pytest.mark.parametrize("failure", ["init", 1, 3, 5])
def test_failure_closes_without_retry_or_reinitializing(setup_model, failure):
    case = setup_model
    case.dll.fail_at = failure
    with pytest.raises(ami.AMIModelError, match="Unsuccessful return status"):
        run(case)
    assert len(case.loads) == 1
    assert [event[0] for event in case.dll.events].count("init") == 1
    assert case.dll.events[-1] == ("close",)
    assert [event[0] for event in case.dll.events].count("close") == 1
    assert len(case.python_calls) == (0 if failure == "init" else (failure + 1) // 2)


@pytest.mark.parametrize("cleanup", ["exception", "status_zero"])
def test_primary_and_cleanup_failures_are_both_retained(setup_model, cleanup):
    case = setup_model
    case.dll.fail_at = 5
    if cleanup == "exception":
        case.dll.close_error = RuntimeError("close failed")
    else:
        case.dll.close_status = 0
    with pytest.raises(RuntimeError) as caught:
        run(case)
    assert isinstance(caught.value.primary_error, ami.AMIModelError)
    assert isinstance(caught.value.cleanup_error, ami.AMIModelError)
    assert "Unsuccessful return status" in str(caught.value.primary_error)
    message = "close failed" if cleanup == "exception" else "Unsuccessful return status 0"
    assert message in str(caught.value.cleanup_error)
    if cleanup == "status_zero":
        assert caught.value.cleanup_error.diagnostic["status"] == 0
    assert case.dll.events[-1] == ("close",)


@pytest.mark.parametrize("cleanup", ["exception", "status_zero"])
def test_cleanup_failure_prevents_success(setup_model, cleanup):
    case = setup_model
    if cleanup == "exception":
        case.dll.close_error = RuntimeError("close failed")
    else:
        case.dll.close_status = 0
    message = "close failed" if cleanup == "exception" else "Unsuccessful return status 0"
    with pytest.raises(ami.AMIModelError, match=message):
        run(case)
    assert case.dll.events[-1] == ("close",)


@pytest.mark.parametrize("use_getwave", [False, True])
def test_shared_initializer_preserves_fext_rows_and_init_only(setup_model, use_getwave):
    case = setup_model
    case.cfg.info_ami_params["Init_Returns_Impulse"] = True
    case.cfg.info_ami_params["GetWave_Exists"].pvalue = use_getwave
    fext = [np.array([.1, .2]), np.arange(85) / 1000]
    result = ibisami.run_ami_model("fake-only", case.cfg, use_getwave, 1., .25,
                                  case.channel, case.main, fext_hs=fext)
    event = case.dll.events[0]
    assert event[0] == "init" and event[2:] == (80, 2)
    expected = np.concatenate([case.channel, np.pad(fext[0], (0, 78)), fext[1][:80]]) / .25
    np.testing.assert_array_equal(event[1], expected)
    assert case.dll.events[-1] == ("close",)
    assert all(np.all(np.isfinite(value)) for value in result[:4])
    if not use_getwave:
        assert [event[0] for event in case.dll.events] == ["init", "close"]
        assert not case.rng_calls and not case.python_calls
        assert not len(result[1]) and result[-1] == []
        np.testing.assert_array_equal(result[0], np.convolve(case.main, result[3])[:len(case.main)])


def test_copy_failure_still_closes(setup_model, monkeypatch):
    failure = MemoryError("copy failed")

    def fail_copy(_value):
        raise failure

    monkeypatch.setattr(ibisami, "deepcopy", fail_copy)
    with pytest.raises(MemoryError) as caught:
        run(setup_model)
    assert caught.value is failure
    assert setup_model.dll.events[-1] == ("close",)


def test_interruption_still_closes(setup_model, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(ami.AMIModel, "get_responses", interrupt)
    with pytest.raises(KeyboardInterrupt):
        run(setup_model)
    assert [event[0] for event in setup_model.dll.events] == ["init", "close"]


def test_returns_are_copied_before_close(setup_model, monkeypatch):
    original_responses = ami.AMIModel.get_responses
    original_wave, original_close = ami.AMIModel.getWave, ami.AMIModel.close
    buffers = []

    def responses(model, **kwargs):
        result = original_responses(model, **kwargs)
        buffers.extend([result[ami.IMP_RESP_GETW], result[ami.OUT_RESP_GETW][1]])
        return result

    def wave(model, *args, **kwargs):
        result = original_wave(model, *args, **kwargs)
        buffers.extend(result[:2])
        return result

    def close(model):
        if getattr(model, "_ami_mem_handle", None):
            for buffer in buffers:
                buffer[:] = np.nan
        original_close(model)

    monkeypatch.setattr(ami.AMIModel, "get_responses", responses)
    monkeypatch.setattr(ami.AMIModel, "getWave", wave)
    monkeypatch.setattr(ami.AMIModel, "close", close)
    result = run(setup_model)
    assert all(np.all(np.isfinite(value)) for value in result[:4])
    assert buffers and all(np.all(np.isnan(buffer)) for buffer in buffers)


def test_rx_caller_does_not_seed_probes_or_claim_fresh_main():
    # Execute the two actual caller statements without starting a full simulation.
    path = Path(ibisami.__file__).parents[1] / "models/bert.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    block = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                 and ast.unparse(node.test) == "self.rx_use_ami and self.rx_use_getwave"
                 and "clock_info.update" in ast.unparse(node.body[1]))
    calls = []

    def call(*args, **kwargs):
        calls.append(kwargs)
        return None, np.array([12.]), None, None, "", []

    namespace = dict(self=SimpleNamespace(rx_dll_file="fake", _rx_cfg=None, seed=123),
                     ui=1., ts=.25, tx_out_h=None, rx_in=None, clock_info={}, np=np, run_ami_model=call)
    exec(compile(ast.Module(body=block.body[:2], type_ignores=[]), str(path), "exec"), namespace)
    assert calls == [{"fext_hs": []}]
    assert namespace["clock_info"]["main_origin"] == "same_init_after_probes"
    np.testing.assert_array_equal(namespace["clock_info"]["returned_edges_s"], [12.])
