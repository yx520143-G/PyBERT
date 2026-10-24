"""Producer-owned AMI clock records shared by Web consumers and archive validation."""

import numpy as np


def validate_period(t, period_ps, known):
    """Validate the exact dense masked exception; return compact references without changing raw bytes."""
    t, period_ps, known = np.asarray(t), np.asarray(period_ps), np.asarray(known)
    if (t.ndim != 1 or t.dtype.kind not in "fiu" or not np.isfinite(t).all()
            or period_ps.dtype.kind != "f" or known.dtype.kind != "b"
            or period_ps.shape != t.shape or known.shape != t.shape
            or not np.isfinite(period_ps[known]).all() or np.any(period_ps[known] <= 0)
            or not np.isnan(period_ps[~known]).all()):
        raise ValueError("AMI period requires a same-grid bool mask, positive finite known and NaN unknown values")
    indices = np.flatnonzero(known)
    return indices, t[indices], period_ps[indices]
