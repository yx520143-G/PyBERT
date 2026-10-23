"""The existing 4-port entry keeps its literal/renumbered physical semantics."""

import numpy as np
import pytest
import skrf

from pybert.utility.sparam import import_freq
from test_multilane_physical import physical_network, differential_oracle


@pytest.mark.parametrize("numbering", ["interleaved", "grouped"])
@pytest.mark.parametrize("renumber", [False, True])
def test_fourport_complex_s_and_z0_unchanged(tmp_path, numbering, renumber):
    net, pairs = physical_network(1, numbering)
    path = tmp_path / "fourport.s4p"
    net.write_touchstone(str(path), write_z0=True, form="ri")
    saved = skrf.Network(str(path))
    near, far = pairs[0] if renumber else ((0, 2), (1, 3))
    expected, z0 = differential_oracle(saved, near, far)
    actual = import_freq(str(path), renumber=renumber)
    np.testing.assert_allclose(actual.s, expected, rtol=2e-12, atol=2e-12)
    np.testing.assert_array_equal(actual.z0, z0)
