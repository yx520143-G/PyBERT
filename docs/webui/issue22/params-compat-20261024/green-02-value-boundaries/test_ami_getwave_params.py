"""Pure returned-parameter contract tests; run directly to avoid simulation fixtures."""

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

from numpy import array
from parsec import ParseError, generate, many, regex, string

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/webui/issue22/params-compat-20261024"
PARSER = EVIDENCE / "source/parser.py"
CORE = ROOT / "src/pybert/models/bert.py"
PARSER_CALLS = 0

# This is the pinned dependency's grammar verbatim, not a replacement grammar.
assert hashlib.sha256(PARSER.read_bytes()).hexdigest() == (
    "2c2e688e3257476d38c175bcd37bb8050b253ad822139c55001eff920ba65594"
)
parser_ns = dict(re=re, generate=generate, many=many, regex=regex, string=string)
grammar = "\n".join(PARSER.read_text(encoding="utf-8").splitlines()[84:143])
exec(compile("from __future__ import annotations\n" + grammar, str(PARSER), "exec"), parser_ns)


def parse(text):
    """Count pure parsing only; no PyAMI module import or model construction."""
    global PARSER_CALLS  # pylint: disable=global-statement
    PARSER_CALLS += 1
    return parser_ns["ami_parse"](text)


def load_processor():
    """Execute the actual production pure function, without importing the engine."""
    tree = ast.parse(CORE.read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "getwave_parameters")
    namespace = {"ami_parse": parse, "AmiName": str, "AmiNode": object, "array": array}
    # The unmodified baseline block refers to this actual pinned dataclass.
    parser_tree = ast.parse(PARSER.read_text(encoding="utf-8"))
    leaf = next(n for n in parser_tree.body if isinstance(n, ast.ClassDef) and n.name == "AmiLeaf")
    namespace["dataclass"] = dataclass
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.Module(body=[future, leaf, function], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(CORE), "exec"), namespace)
    return namespace["getwave_parameters"]


class GetWaveParameterTests(unittest.TestCase):
    """Observe numeric histories and tap rows at the production consumer boundary."""

    def test_saved_750_return_strings_preserve_numeric_tap_histories(self):
        consume = load_processor()
        outputs = []
        for side in ("direct", "worker"):
            path = ROOT / "docs/webui/issue10/evidence/numerics-20261024-160343/A-NRZ-ADAPT-GetWave"
            params = json.loads((path / side / "ami-execution.json").read_text(encoding="utf-8"))["calls"][0]["params_out"]
            with self.subTest(side=side):
                values, taps = consume(params)
                self.assertEqual(sorted(values), [(f"dfe_tap{i}",) for i in range(1, 6)])
                self.assertEqual([len(v) for v in values.values()], [375] * 5)
                self.assertEqual(len(taps), 375)
                self.assertEqual(taps[0], [-0.232317, -0.286812, -0.186812, -0.0610478, 0.0131884])
                self.assertEqual(taps[-1], [-0.361426, -0.385818, -0.285818, -0.185818, -0.0858182])
                outputs.append((values, taps))
        if len(outputs) == 2:
            self.assertEqual(outputs[0], outputs[1])

    def test_full_paths_and_case_insensitive_taps(self):
        values, taps = load_processor()([
            "(rx (a.b (tap 3)) (a (b.tap 4)) (tapZ 5) (TapA 6) (cdr_locked 1) (cdr_ui 1e-10))"
        ])
        self.assertEqual(values, {
            ("a.b", "tap"): [3.0], ("a", "b.tap"): [4.0], ("tapZ",): [5.0], ("TapA",): [6.0],
            ("cdr_locked",): [1.0], ("cdr_ui",): [1e-10],
        })
        self.assertEqual(taps, [[6.0, 4.0, 3.0, 5.0]])
        same_names, _ = load_processor()(["(rx (left (gain 1)) (right (gain 2)) (ab (c 3)) (a (bc 4)))"])
        self.assertEqual(same_names, {
            ("left", "gain"): [1.0], ("right", "gain"): [2.0], ("ab", "c"): [3.0], ("a", "bc"): [4.0],
        })

    def test_non_numeric_mixed_and_table_values_are_unavailable(self):
        values, taps = load_processor()([
            '(rx (note Ready) (mixed 1 Ready) (TapStatus "N/A") (empty) '
            '(Table (0 1) (1 2)) (weight (Table (0 1) (1 2))) '
            '(cdr_locked 1) (cdr_ui 1e-10) (tap2 -0.2))'
        ])
        self.assertEqual(values, {("cdr_locked",): [1.0], ("cdr_ui",): [1e-10], ("tap2",): [-0.2]})
        self.assertEqual(taps, [[-0.2]])

    def test_empty_returns_have_no_taps(self):
        consume = load_processor()
        for params in ([], ["(rx)"], ["(rx)", "(rx)"], ["(rx (gain 2))"]):
            with self.subTest(params=params):
                values, taps = consume(params)
                self.assertEqual(taps, [])
                self.assertEqual(values, {("gain",): [2.0]} if "gain" in str(params) else {})

    def test_ambiguous_node_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "mixed.*bad"):
            load_processor()(["(rx (bad 1 (child 2)))"])

    def test_invalid_syntax_still_fails(self):
        with self.assertRaises(ParseError):
            load_processor()(["(rx (tap1 1)"])


if __name__ == "__main__":
    assert not any(name.startswith(("pybert", "pyibisami")) for name in sys.modules)
    unittest.main()
