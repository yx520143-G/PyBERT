"""Exercise the actual C1 coordinator with ordinary Python model stubs only."""

import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest

from c1_under_test import coordinator, source_path, caller_path, baseline_path


EVENTS = []
COUNTS = {}
CASES = []
FAILURES = {}
CURRENT_ROLE = None
ACTIVE = None
RNG_TOKEN = object()
RNG_ARGUMENTS = []
POINT_HITS = {}
INIT_INPUTS = []
MUTATE_INPUTS = False


def count(name):
    COUNTS[name] = COUNTS.get(name, 0) + 1


def fail(point):
    POINT_HITS[point] = POINT_HITS.get(point, 0) + 1
    if point in FAILURES:
        raise FAILURES[point]


class CopyBuffer(list):
    def __init__(self, values, point):
        super().__init__(values)
        self.point = point

    def __deepcopy__(self, memo):
        count("stub_buffer_copy")
        point = self.point
        if point == "x":
            point = CURRENT_ROLE + ".x_copy" if CURRENT_ROLE else "freeze.x"
        fail(point)
        return CopyBuffer(deepcopy(list(self), memo), self.point)


class CopyRecord(dict):
    def __init__(self, values, point):
        super().__init__(values)
        self.point = point

    def __deepcopy__(self, memo):
        count("stub_record_copy")
        fail(self.point)
        return deepcopy(dict(self), memo)


class InputMarker:
    def __deepcopy__(self, memo):
        count("stub_input_copy")
        fail(CURRENT_ROLE + ".input_copy" if CURRENT_ROLE else "freeze.inputs")
        return InputMarker()


class Message:
    def __init__(self, role):
        self.role = role

    def decode(self, encoding):
        count("stub_message_decode")
        fail(self.role + ".message")
        return self.role


class FakeModel:
    def __init__(self, role):
        global CURRENT_ROLE
        CURRENT_ROLE = role
        assert ACTIVE is None, "overlapping live handles"
        count("stub_model_factory")
        self.role = role
        self.last_init_call = None
        self.last_close_call = None
        self.buffers = []
        EVENTS.append((role, "construct"))
        fail(role + ".construct")

    def initialize(self, inputs):
        global ACTIVE
        ACTIVE = self.role
        count("stub_initialize")
        EVENTS.append((self.role, "initialize"))
        INIT_INPUTS.append(deepcopy(inputs))
        self.last_init_call = CopyRecord({
            "epoch": 1, "input_impulse": list(inputs["channel"]), "init_out": [11, 12],
            "params_in": b"(original)", "params_raw": self.role.encode(), "message_raw": Message(self.role),
        }, self.role + ".init_copy")
        self.buffers.extend([inputs["channel"], self.last_init_call["init_out"]])
        if MUTATE_INPUTS and self.role == "probe":
            inputs["channel"][0] = -1
            inputs["fext"][0][0] = -2
            inputs["parameters"]["tap"][0] = -3
            inputs["info"]["ignore"][0] = -4
        fail(self.role + ".initialize")

    def get_responses(self, **kwargs):
        count("stub_get_responses")
        EVENTS.append((self.role, "responses"))
        fail(self.role + ".responses")
        assert self.role == "probe"
        assert kwargs == {"bits_per_call": 40, "max_run_length": 10, "nbits": 20, "rng": RNG_TOKEN}
        assert kwargs["rng"] is RNG_TOKEN
        h = CopyBuffer([21, 22], "probe.h_copy")
        out_h = CopyBuffer([31, 32], "probe.out_h_copy")
        self.buffers.extend([h, out_h])
        return {"impulse": h, "output": ([], out_h)}

    def getWave(self, wave, *, bits_per_call):
        count("stub_getWave")
        EVENTS.append((self.role, "main", list(wave), bits_per_call))
        fail(self.role + ".main")
        assert wave == [7, 8, 9]
        assert self.role == "main"
        outputs = (CopyBuffer([41, 42, 43], "main.y_copy"), CopyBuffer([0, 2], "main.clocks_copy"),
                   CopyBuffer(["main-params"], "main.params_copy"))
        self.buffers.extend(outputs)
        return outputs

    def close(self):
        global ACTIVE
        count("stub_close")
        EVENTS.append((self.role, "close"))
        for buffer in self.buffers:
            buffer[:] = ["destroyed"]
        if self.last_init_call:
            self.last_init_call["params_raw"] = b"destroyed"
        self.last_close_call = CopyRecord({"method": "close"}, self.role + ".close_copy")
        fail(self.role + ".close")
        ACTIVE = None


def stub_case(bits=0, seed=123, inputs=None, wave=None):
    roles = iter(["probe", "main"])

    def make_initializer(values):
        count("stub_initializer")
        EVENTS.append(("prepare", list(values["channel"])))
        fail(CURRENT_ROLE + ".prepare")
        return values

    def make_rng(value):
        count("stub_rng_factory")
        RNG_ARGUMENTS.append(value)
        fail("probe.rng")
        return RNG_TOKEN

    return coordinator(lambda: FakeModel(next(roles)), make_initializer,
                       inputs if inputs is not None else {"channel": [1, 2], "marker": InputMarker()},
                       wave if wave is not None else CopyBuffer([7, 8, 9], "x"), bits, seed, make_rng)


class ProbeMainTests(unittest.TestCase):
    def setUp(self):
        global CURRENT_ROLE, ACTIVE, MUTATE_INPUTS, RNG_TOKEN
        CURRENT_ROLE = ACTIVE = None
        EVENTS.clear()
        COUNTS.clear()
        FAILURES.clear()
        POINT_HITS.clear()
        RNG_ARGUMENTS.clear()
        INIT_INPUTS.clear()
        MUTATE_INPUTS = False
        RNG_TOKEN = object()

    def tearDown(self):
        CASES.append({"test": self.id(), "events": list(EVENTS), "stub_counts": dict(COUNTS)})

    def test_primary_and_cleanup_errors_are_both_preserved(self):
        primary, cleanup = ValueError("probe failed"), OSError("close failed")
        FAILURES.update({"probe.responses": primary, "probe.close": cleanup})
        roles = iter(["probe", "main"])

        def make_initializer(inputs):
            count("stub_initializer")
            return inputs

        def make_rng(seed):
            count("stub_rng_factory")
            return RNG_TOKEN

        with self.assertRaises(Exception) as caught:
            coordinator(lambda: FakeModel(next(roles)), make_initializer,
                        {"channel": [1, 2]}, [7, 8, 9], 0, 123, make_rng)
        self.assertIs(caught.exception.primary_error, primary)
        self.assertIs(caught.exception.cleanup_error, cleanup)
        self.assertEqual(caught.exception.role, "probe")
        self.assertFalse(any(event[0] == "main" for event in EVENTS))
        self.assertEqual(COUNTS["stub_close"], 1)

    def test_failure_points_stop_without_retries_and_keep_evidence(self):
        cases = [
            ("freeze.inputs", 0, 0, "freeze"), ("freeze.x", 0, 0, "freeze"),
            ("probe.construct", 1, 0, "construct"), ("probe.input_copy", 1, 1, "prepare"),
            ("probe.prepare", 1, 1, "prepare"), ("probe.initialize", 1, 1, "initialize"),
            ("probe.init_copy", 1, 1, "init_copy"), ("probe.rng", 1, 1, "rng"),
            ("probe.responses", 1, 1, "probe"), ("probe.h_copy", 1, 1, "probe_copy"),
            ("probe.out_h_copy", 1, 1, "probe_copy"), ("probe.close", 1, 1, "cleanup"),
            ("probe.close_copy", 1, 1, "close_copy"), ("main.construct", 2, 1, "construct"),
            ("main.input_copy", 2, 2, "prepare"), ("main.prepare", 2, 2, "prepare"),
            ("main.initialize", 2, 2, "initialize"), ("main.init_copy", 2, 2, "init_copy"),
            ("main.message", 2, 2, "message"), ("main.x_copy", 2, 2, "main_input"),
            ("main.main", 2, 2, "main"), ("main.y_copy", 2, 2, "main_copy"),
            ("main.clocks_copy", 2, 2, "main_copy"), ("main.params_copy", 2, 2, "main_copy"),
            ("main.close", 2, 2, "cleanup"), ("main.close_copy", 2, 2, "close_copy"),
        ]
        for point, factories, closes, phase in cases:
            with self.subTest(point=point):
                self.setUp()
                error = ValueError(point)
                FAILURES[point] = error
                with self.assertRaises(Exception) as caught:
                    stub_case()
                failure = caught.exception
                self.assertEqual(failure.phase, phase)
                self.assertEqual(failure.role, "main" if point.startswith("main.") else "probe")
                if point.endswith(".close"):
                    self.assertIsNone(failure.primary_error)
                    self.assertIs(failure.cleanup_error, error)
                else:
                    self.assertIs(failure.primary_error, error)
                    self.assertIsNone(failure.cleanup_error)
                self.assertEqual(COUNTS.get("stub_model_factory", 0), factories)
                self.assertEqual(COUNTS.get("stub_close", 0), closes)
                self.assertEqual(POINT_HITS[point], 1)
                if point.endswith(".initialize"):
                    self.assertEqual(failure.diagnostics[-1]["init"]["params_raw"], failure.role.encode())
                CASES.append({"matrix_point": point, "events": list(EVENTS), "stub_counts": dict(COUNTS)})

    def test_primary_close_and_diagnostic_errors_remain_separate(self):
        primary, cleanup = ValueError("main init"), OSError("main close")
        init_copy, close_copy = MemoryError("init snapshot"), MemoryError("close snapshot")
        FAILURES.update({"main.initialize": primary, "main.close": cleanup,
                         "main.init_copy": init_copy, "main.close_copy": close_copy})
        with self.assertRaises(Exception) as caught:
            stub_case()
        self.assertIs(caught.exception.primary_error, primary)
        self.assertIs(caught.exception.cleanup_error, cleanup)
        self.assertEqual(caught.exception.diagnostic_errors, [init_copy, close_copy])
        self.assertEqual(COUNTS["stub_close"], 2)
        self.assertEqual(POINT_HITS["main.init_copy"], 1)
        self.assertEqual(POINT_HITS["main.close_copy"], 1)

    def test_seed_zero_and_nonzero_block_policies(self):
        for seed, requested, expected_block in [(0, 0, 40), (0, 17, 17), (123, 0, 40), (123, 17, 17)]:
            with self.subTest(seed=seed, requested=requested):
                self.setUp()
                result = stub_case(seed=seed, bits=requested)
                self.assertEqual(len(result), 6)
                self.assertEqual(RNG_ARGUMENTS, [None if seed == 0 else 123])
                main_event = next(event for event in EVENTS if len(event) > 1 and event[1] == "main")
                self.assertEqual(main_event, ("main", "main", [7, 8, 9], expected_block))
                self.assertEqual(COUNTS["stub_rng_factory"], 1)
                self.assertIn("UNKNOWN" if seed == 0 else "seeded", result[4])
                CASES.append({"policy": [seed, requested], "rng_arguments": list(RNG_ARGUMENTS),
                              "events": list(EVENTS), "stub_counts": dict(COUNTS)})

    def test_mutable_init_inputs_cannot_cross_roles_or_change_main_origin(self):
        global MUTATE_INPUTS
        MUTATE_INPUTS = True
        wave = [7, 8, 9]
        inputs = {"channel": wave, "fext": [[3, 4]], "parameters": {"tap": [3]},
                  "info": {"ignore": [5]}, "ts": 0.25, "ui": 1.0}
        expected = {"channel": [7, 8, 9], "fext": [[3, 4]], "parameters": {"tap": [3]},
                    "info": {"ignore": [5]}, "ts": 0.25, "ui": 1.0}
        result = stub_case(inputs=inputs, wave=wave)
        self.assertEqual(INIT_INPUTS, [expected, expected])
        self.assertEqual(inputs, expected)
        self.assertEqual(wave, [7, 8, 9])
        self.assertEqual(result[:4], ([41, 42, 43], [0, 2], [21, 22], [31, 32]))

    def test_only_target_caller_selects_the_real_coordinator(self):
        source = ast.parse(Path(source_path).read_text(encoding="utf-8"))
        helper = next(node for node in source.body
                      if isinstance(node, ast.FunctionDef) and node.name == "run_ami_model")
        self.assertEqual([arg.arg for arg in helper.args.kwonlyargs], ["_probe_seed"])
        calls = [node for node in ast.walk(helper) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "_run_probe_main"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(ast.unparse(calls[0].args[-1]), "np.random.default_rng")
        self.assertEqual(ast.unparse(calls[0].args[0]), "lambda: AMIModel(dll_fname)")
        self.assertEqual(ast.unparse(calls[0].args[1]), "_make_ami_initializer")
        caller = ast.parse(Path(caller_path).read_text(encoding="utf-8"))
        call_paths = []

        def visit(node, conditions):
            if isinstance(node, ast.If):
                for child in node.body:
                    visit(child, conditions + [(node.test, True)])
                for child in node.orelse:
                    visit(child, conditions + [(node.test, False)])
                return
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_ami_model":
                call_paths.append((node, conditions))
            for child in ast.iter_child_nodes(node):
                visit(child, conditions)

        visit(caller, [])
        self.assertEqual(len(call_paths), 6)
        selected = [(call, path) for call, path in call_paths if any(k.arg == "_probe_seed" for k in call.keywords)]
        self.assertEqual(len(selected), 1)
        call, conditions = selected[0]
        self.assertEqual(ast.unparse(call.args[6]), "rx_in")
        keyword = next(k for k in call.keywords if k.arg == "_probe_seed")
        self.assertEqual(ast.unparse(keyword.value), "self.seed")
        for tx_ami, tx_gw in [(False, False), (False, True), (True, False), (True, True)]:
            for use_clocks in [False, True]:
                this = SimpleNamespace(tx_use_ami=tx_ami, tx_use_getwave=tx_gw,
                                       rx_use_ami=True, rx_use_getwave=True, rx_use_clocks=use_clocks)
                actual = all(eval(compile(ast.Expression(test), "<static-caller-predicate>", "eval"),
                                  {"__builtins__": {}, "self": this}) == branch for test, branch in conditions)
                self.assertEqual(actual, not (tx_ami and tx_gw))
        keyword_index = call.keywords.index(keyword)
        del call.keywords[keyword_index]
        baseline = ast.parse((Path(baseline_path) / "bert.baseline.py.txt").read_text(encoding="utf-8"))
        self.assertEqual(ast.dump(caller), ast.dump(baseline))

    def test_initializer_and_legacy_helper_remain_equivalent(self):
        current = ast.parse(Path(source_path).read_text(encoding="utf-8"))
        baseline = ast.parse((Path(baseline_path) / "ibisami.baseline.py.txt").read_text(encoding="utf-8"))
        functions = {node.name: node for node in current.body if isinstance(node, ast.FunctionDef)}
        old = next(node for node in baseline.body
                   if isinstance(node, ast.FunctionDef) and node.name == "run_ami_model")
        begin = next(i for i, node in enumerate(old.body) if isinstance(node, ast.Assign)
                     and ast.unparse(node.targets[0]) == "row_size")
        end = next(i for i, node in enumerate(old.body) if isinstance(node, ast.Assign)
                   and ast.unparse(node.targets[0]) == "model")
        preparation = old.body[begin:end]

        class ReplaceInputs(ast.NodeTransformer):
            def visit_Attribute(self, node):
                if isinstance(node.value, ast.Name) and node.value.id == "param_cfg":
                    key = {"input_ami_params": "ami_params", "info_ami_params": "info_params"}[node.attr]
                    return ast.Subscript(value=ast.Name(id="inputs", ctx=ast.Load()),
                                         slice=ast.Constant(value=key), ctx=ast.Load())
                return node

        expected = ReplaceInputs().visit(deepcopy(ast.Module(body=preparation, type_ignores=[])))
        factory = functions["_make_ami_initializer"]
        actual = ast.Module(body=factory.body[3:-1], type_ignores=[])
        self.assertEqual(ast.dump(actual), ast.dump(expected))
        aliases = ast.parse('chnl_h, fext_hs = inputs["chnl_h"], inputs["fext_hs"]\n'
                            'ui, ts = inputs["ui"], inputs["ts"]\n')
        self.assertEqual(ast.dump(ast.Module(body=factory.body[1:3], type_ignores=[])), ast.dump(aliases))
        normalized = deepcopy(functions["run_ami_model"])
        normalized.args.kwonlyargs.clear()
        normalized.args.kw_defaults.clear()
        text = normalized.body[0].value.value
        normalized.body[0].value.value = "\n".join(line for line in text.split("\n")
                                                if "_probe_seed: Internal" not in line
                                                and "None retains the legacy path;" not in line)
        start = next(i for i, node in enumerate(normalized.body) if isinstance(node, ast.Assign)
                     and ast.unparse(node.targets[0]) == "init_inputs")
        normalized.body[start:start + 3] = deepcopy(preparation)
        self.assertEqual(ast.dump(normalized), ast.dump(old))
        seam = functions["_run_probe_main"]
        returned = next(node for node in seam.body if isinstance(node, ast.Return))
        self.assertEqual([node.id for node in returned.value.elts], ["y", "clocks", "h", "out_h", "msg", "params"])

    def test_interrupt_and_cleanup_are_both_preserved(self):
        primary, cleanup = KeyboardInterrupt("probe interrupted"), OSError("close failed")
        FAILURES.update({"probe.responses": primary, "probe.close": cleanup})
        with self.assertRaises(BaseException) as caught:
            stub_case()
        self.assertIs(caught.exception.primary_error, primary)
        self.assertIs(caught.exception.cleanup_error, cleanup)
        self.assertEqual(caught.exception.role, "probe")
        self.assertFalse(any(event[0] == "main" for event in EVENTS))

    def test_roles_are_sequential_and_results_survive_close(self):
        self.assertIsNotNone(coordinator, "production C1 coordinator is not implemented")
        roles = iter(["probe", "main"])

        def make_model():
            return FakeModel(next(roles))

        def make_initializer(inputs):
            count("stub_initializer")
            EVENTS.append(("prepare", list(inputs["channel"])))
            return inputs

        def make_rng(seed):
            count("stub_rng_factory")
            self.assertEqual(seed, 123)
            return RNG_TOKEN

        inputs, wave = {"channel": [1, 2], "parameters": {"tap": [3]}}, [7, 8, 9]
        result = coordinator(make_model, make_initializer, inputs, wave, 0, 123, make_rng)
        self.assertEqual(result[:4], ([41, 42, 43], [0, 2], [21, 22], [31, 32]))
        self.assertEqual(result[5], ["main-params"])
        self.assertIn("Message: main", result[4])
        self.assertIn("probe", result[4])
        self.assertIn("main", result[4])
        self.assertEqual(inputs, {"channel": [1, 2], "parameters": {"tap": [3]}})
        self.assertEqual(wave, [7, 8, 9])
        self.assertEqual(EVENTS, [
            ("probe", "construct"), ("prepare", [1, 2]), ("probe", "initialize"),
            ("probe", "responses"), ("probe", "close"),
            ("main", "construct"), ("prepare", [1, 2]), ("main", "initialize"),
            ("main", "main", [7, 8, 9], 40), ("main", "close"),
        ])
