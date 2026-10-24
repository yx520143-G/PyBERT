"""Issue #16 reference: documented physical pairs, independent of PyBERT mapping."""

import hashlib
from pathlib import Path

import numpy as np
from scipy.interpolate import interp1d

ROOT = Path(__file__).resolve().parents[1]
ISSUE = ROOT / "docs/webui/issue16"
REFS = {
    "pre": "9a33d08458aa00782e90169c699857b8b19455a2",
    "post": "92c317401e723e13b5a04a809547dc77f4cf8269",
    "final": "153fcd5a426935387cbdccb1880cabb43f5f4e01",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_touchstone(path):
    """Read the frozen v1 full-matrix DB/MA/RI files; no skrf/PyBERT reader."""
    path = Path(path)
    n = int(path.suffix[2:-1])
    values, option = [], None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("!", 1)[0].strip()
        if not line:
            continue
        if line.startswith("#"):
            option = line[1:].lower().split()
        else:
            assert not line.startswith("["), "Touchstone 2 not in this reader's scope"
            values.extend(float(v) for v in line.split())
    unit, parameter, form, r, z0 = option
    assert parameter == "s" and r == "r" and form in ("ma", "ri", "db")
    data = np.asarray(values).reshape(-1, 1 + 2 * n * n)
    f = data[:, 0] * {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}[unit]
    a = data[:, 1::2]
    b = data[:, 2::2]
    if form == "ri":
        s = a + 1j * b
    else:
        magnitude = 10 ** (a / 20) if form == "db" else a
        s = magnitude * np.exp(1j * np.deg2rad(b))
    # Touchstone N>2 rows enumerate S11,S12,...,S1N,S21,... (2-port is special).
    s = s.reshape(-1, n, n)
    assert n in (8, 12) and np.all(np.diff(f) > 0) and np.isfinite(s).all()
    return f, s, float(z0), {"format": form.upper(), "unit": unit.upper(), "ports": n}


def differential(s, input_pair, output_pair):
    """b_d = B b_se, a_se = B.T a_d, B rows = (+1,-1)/sqrt(2)."""
    b = np.zeros((2, s.shape[1]))
    for row, (plus, minus) in enumerate((input_pair, output_pair)):
        b[row, plus] = 1 / np.sqrt(2)
        b[row, minus] = -1 / np.sqrt(2)
    return np.einsum("ai,fij,bj->fab", b, s, b)


def interpolate(f, s, grid):
    """Independently express the frozen polar interpolation/extension convention."""
    magnitude = interp1d(f, abs(s), axis=0, bounds_error=False, fill_value="extrapolate")(grid)
    angle = interp1d(f, np.unwrap(np.angle(s), axis=0), axis=0,
                     bounds_error=False, fill_value="extrapolate")(grid)
    result = magnitude * np.exp(1j * angle)
    for i in range(2):
        z = result[:, i, i]
        result[:, i, i] = np.minimum(abs(z), 1) * np.exp(1j * np.angle(z))
    outside = (grid < f[0]) | (grid > f[-1])
    result[outside, 0, 1] = result[outside, 1, 0] = 0
    return result


def write_reordered(original, output, new_to_old):
    """Pure port permutation; original bytes retained, no model generation."""
    f, s, z0, _ = read_touchstone(original)
    permuted = s[:, new_to_old][:, :, new_to_old]
    with Path(output).open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("! #16 port-only permutation; see resources.json for provenance/mapping.\n")
        stream.write(f"# Hz S RI R {z0:.17g}\n")
        for frequency, matrix in zip(f, permuted):
            flat = matrix.flatten()
            stream.write(" ".join([f"{frequency:.17g}"] +
                                  [f"{component:.17g}" for z in flat for component in (z.real, z.imag)]) + "\n")


def compare(a, b, rtol=1e-10, atol=1e-12):
    a, b = np.asarray(a), np.asarray(b)
    row = {"shape_actual": list(a.shape), "shape_expected": list(b.shape), "rtol": rtol, "atol": atol}
    if a.shape != b.shape:
        return row | {"passed": False}
    good = np.isfinite(a) & np.isfinite(b) & (abs(a - b) <= atol + rtol * abs(b))
    return row | {"passed": bool(good.all()), "max_abs_error": float(abs(a - b).max(initial=0)),
                  "bad_count": int((~good).sum()),
                  "first_bad_index": None if good.all() else np.argwhere(~good)[0].tolist()}
