"""Stdlib-only fail-stop sentinel; separate from all product software cases."""

import unittest

from d2_under_test import destination


class GuardOnlyCases(unittest.TestCase):
    def test_a_callback_block_cannot_be_caught_or_continue(self):
        (destination / "sentinel-before.txt").write_text("started\n", encoding="utf-8", newline="\n")

        def stub_guard_trigger():
            (destination / "sentinel-body.txt").write_text("forbidden", encoding="utf-8")

        with self.subTest(ordinary_stdlib_guard=True):
            try:
                stub_guard_trigger()
            except BaseException:
                (destination / "sentinel-caught.txt").write_text("forbidden", encoding="utf-8")
        (destination / "sentinel-after.txt").write_text("forbidden", encoding="utf-8")

    def test_b_next_case_must_never_start(self):
        (destination / "sentinel-next-case.txt").write_text("forbidden", encoding="utf-8")
