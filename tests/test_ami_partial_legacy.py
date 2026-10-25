"""Execute the retained raw6 fixture against current readers without changing historical evidence."""

import importlib
import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest


def test_retained_raw6_mask_producer_and_archive_contracts(monkeypatch, tmp_path):
    fixture = ModuleType("d2_under_test")
    fixture.np, fixture.destination = np, tmp_path
    fixture.modules = {name: importlib.import_module(name) for name in (
        "pybert.utility.ami_clock", "pybert.web.clocks", "pybert.web.archive", "pybert.web.viterbi")}
    monkeypatch.setitem(__import__("sys").modules, fixture.__name__, fixture)
    path = Path(__file__).resolve().parents[1] / "docs/webui/issue10/d2-web-20261025/d2_cases.py"
    spec = importlib.util.spec_from_file_location("retained_d2_cases", path)
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)
    for cls, method in ((cases.MaskCases, "test_dense_bytes_and_exact_known_compact"),
                        (cases.ProducerCases, "test_fresh_host_producer_and_each_actual_eye_crop"),
                        (cases.ArchiveCases, "test_masked_archive_features_and_lossless_original_files")):
        getattr(cls(), method)()
    archive = fixture.modules["pybert.web.archive"]
    run = archive.read_json((tmp_path / "manual-run/manifest.json").read_bytes())
    raw = (tmp_path / "manual-run/arrays.npz").read_bytes()
    run["ami"]["clock_contract"]["full_analysis_eligible"] = False
    with pytest.raises(ValueError, match="Incomplete saved producer"):
        archive.read_arrays(raw, run=run)
