"""A/A and A/B simulation calibration tests."""

import numpy as np
import pytest
from scipy import stats


def _simulate_aa_test(n_per_group=500, baseline_rate=0.60, n_simulations=200, seed=42):
    """Run A/A simulations. Returns false_positive_rate."""
    rng = np.random.default_rng(seed)
    false_positives = 0
    for _ in range(n_simulations):
        a = rng.binomial(1, baseline_rate, n_per_group)
        b = rng.binomial(1, baseline_rate, n_per_group)
        n_a, n_b = a.sum(), b.sum()
        p_hat = (n_a + n_b) / (2 * n_per_group)
        se = np.sqrt(p_hat * (1 - p_hat) * (2 / n_per_group))
        z = (n_a / n_per_group - n_b / n_per_group) / max(se, 1e-10)
        p_val = 2 * (1 - stats.norm.cdf(abs(z)))
        if p_val < 0.05:
            false_positives += 1
    return false_positives / n_simulations


def test_aa_false_positive_rate():
    """A/A test: false positive rate should be near alpha=0.05."""
    fpr = _simulate_aa_test(n_simulations=200, seed=42)
    assert 0.01 <= fpr <= 0.09, f"FPR={fpr:.3f} outside [0.01, 0.09]"


def test_ab_recovery():
    """A/B test: known 5pp uplift with adequate sample should be detected."""
    rng = np.random.default_rng(42)
    n_sim = 100
    n_per = 1600  # Need ~1600/group for 80% power at 5pp from 60% baseline
    detected = 0
    for _ in range(n_sim):
        a = rng.binomial(1, 0.60, n_per)
        b = rng.binomial(1, 0.65, n_per)
        na, nb = a.sum(), b.sum()
        p_hat = (na + nb) / (2 * n_per)
        se = np.sqrt(p_hat * (1 - p_hat) * (2 / n_per))
        z = (nb / n_per - na / n_per) / max(se, 1e-10)
        if z > stats.norm.ppf(0.975):
            detected += 1
    power = detected / n_sim
    assert power >= 0.75, f"Empirical power {power:.2f} < 0.75"


@pytest.mark.slow
def test_aa_strict():
    """1000-simulation A/A test for calibration."""
    fpr = _simulate_aa_test(n_simulations=1000, seed=20260616)
    assert 0.03 <= fpr <= 0.07, f"FPR={fpr:.4f} with 1000 sims"
    print(f"A/A FPR (1000 sims): {fpr:.4f}")
