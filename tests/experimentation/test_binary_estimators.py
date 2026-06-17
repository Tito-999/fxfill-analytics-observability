"""Binary estimator tests with known rates."""
import numpy as np
from fxfill_analytics.experimentation.estimators import binary_effect


def test_binary_no_effect():
    """Same rates should give near-zero difference."""
    r = binary_effect(a_success=500, a_n=1000, b_success=500, b_n=1000)
    assert abs(r["risk_difference"]) < 0.001
    assert r["p_value_ztest"] > 0.5


def test_binary_clear_effect():
    """Known difference should be detected. A=0.5, B=0.6 => B-A=+0.1."""
    r = binary_effect(a_success=500, a_n=1000, b_success=600, b_n=1000)
    assert abs(r["risk_difference"] - 0.10) < 0.01
    assert r["p_value_ztest"] < 0.01
