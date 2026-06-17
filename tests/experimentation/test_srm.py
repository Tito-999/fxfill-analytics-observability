"""SRM test with known-answer data."""

import numpy as np
from scipy.stats import chisquare


def _compute_srm(observed: dict, expected_allocation: dict, srm_alpha=0.001):
    """Standalone SRM calculation for testing."""
    groups = sorted(observed.keys())
    obs = np.array([observed[g] for g in groups], dtype=float)
    exp_props = np.array([expected_allocation.get(g, 0) for g in groups])
    exp = exp_props / exp_props.sum() * obs.sum()
    chi2, p_val = chisquare(f_obs=obs, f_exp=exp)
    return {"chi2": chi2, "p_value": p_val, "passed": p_val >= srm_alpha}


def test_srm_balanced():
    """50/50 split should not reject."""
    r = _compute_srm({"A": 500, "B": 500}, {"A": 0.5, "B": 0.5})
    assert r["passed"]
    assert r["p_value"] > 0.05


def test_srm_imbalanced():
    """70/30 split should clearly reject."""
    r = _compute_srm({"A": 700, "B": 300}, {"A": 0.5, "B": 0.5})
    assert not r["passed"]
    assert r["p_value"] < 0.001
