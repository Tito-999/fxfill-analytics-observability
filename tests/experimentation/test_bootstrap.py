"""Bootstrap determinism and accuracy tests."""

import numpy as np
from fxfill_analytics.experimentation.bootstrap import bootstrap_diff


def test_bootstrap_deterministic():
    """Same seed produces identical CI."""
    a = np.random.default_rng(42).normal(0.7, 0.1, 100)
    b = np.random.default_rng(42).normal(0.75, 0.1, 100)
    r1 = bootstrap_diff(list(a), list(b), iterations=200, seed=42)
    r2 = bootstrap_diff(list(a), list(b), iterations=200, seed=42)
    assert r1["ci_lower"] == r2["ci_lower"]
    assert r1["ci_upper"] == r2["ci_upper"]


def test_bootstrap_positive_injection():
    """Known positive effect should produce positive CI."""
    rng = np.random.default_rng(99)
    a = rng.normal(0.60, 0.10, 200)
    b = rng.normal(0.65, 0.10, 200)  # +0.05 uplift
    r = bootstrap_diff(list(a), list(b), iterations=500, seed=99)
    assert r["ci_lower"] < r["ci_upper"]
