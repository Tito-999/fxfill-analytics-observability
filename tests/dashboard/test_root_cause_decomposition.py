"""Unit test: Kitagawa decomposition on hand-crafted two-segment dataset."""
import pytest


def decompose(curr_vols, prev_vols, curr_rates, prev_rates):
    """Symmetric Kitagawa decomposition. Returns drivers list."""
    total_cv = sum(curr_vols)
    total_pv = sum(prev_vols)
    total_cr = sum(cv * cr for cv, cr in zip(curr_vols, curr_rates)) / max(total_cv, 1)
    total_pr = sum(pv * pr for pv, pr in zip(prev_vols, prev_rates)) / max(total_pv, 1)
    drivers = []
    sum_re = sum_me = 0.0
    for i in range(len(curr_vols)):
        cs = curr_vols[i] / max(total_cv, 1)
        ps = prev_vols[i] / max(total_pv, 1)
        re = 0.5 * (cs + ps) * (curr_rates[i] - prev_rates[i])
        me = 0.5 * (curr_rates[i] + prev_rates[i]) * (cs - ps)
        drivers.append({"segment": f"s{i}", "rate_effect": re, "mix_effect": me, "total": re + me})
        sum_re += re
        sum_me += me
    overall = total_cr - total_pr
    residual = overall - (sum_re + sum_me)
    return drivers, overall, sum_re, sum_me, residual, total_cr, total_pr


class TestKitagawaDecomposition:
    def test_two_segment_symmetric(self):
        """Channel A: rate 0.8->0.9, vol unchanged. Channel B: rate 0.6->0.6."""
        drivers, overall, sum_re, sum_me, residual, tcr, tpr = decompose(
            [50, 50], [50, 50], [0.9, 0.6], [0.8, 0.6]
        )
        # Current: (50*0.9+50*0.6)/100=0.75, Previous: (50*0.8+50*0.6)/100=0.70
        assert abs(tcr - 0.75) < 1e-12
        assert abs(tpr - 0.70) < 1e-12
        assert abs(overall - 0.05) < 1e-12
        assert abs(residual) <= 1e-12, f"Residual {residual} exceeds 1e-12"

    def test_volume_shift_symmetric(self):
        """Channel A: 60->60 tasks (stable), Channel B: 40->40 tasks (stable)."""
        drivers, overall, sum_re, sum_me, residual, tcr, tpr = decompose(
            [60, 40], [60, 40], [0.5, 0.9], [0.5, 0.9]
        )
        # Current: (60*0.5+40*0.9)/100=0.66, Previous: (60*0.5+40*0.9)/100=0.66
        assert abs(tcr - 0.66) < 1e-12
        assert abs(tpr - 0.66) < 1e-12
        assert abs(overall - 0.0) < 1e-12
        assert abs(residual) <= 1e-12

    def test_both_change_symmetric(self):
        """Both volume and rate change."""
        drivers, overall, sum_re, sum_me, residual, tcr, tpr = decompose(
            [70, 30], [50, 50], [0.8, 0.4], [0.9, 0.5]
        )
        assert abs(residual) <= 1e-12

    def test_shares_sum_to_one(self):
        drivers, overall, sum_re, sum_me, residual, tcr, tpr = decompose(
            [60, 40], [50, 50], [0.7, 0.3], [0.8, 0.4]
        )
        assert abs(residual) <= 1e-12

    def test_zero_volume_segment(self):
        """Segment that exists in current but not previous."""
        drivers, overall, sum_re, sum_me, residual, tcr, tpr = decompose(
            [100, 0], [100, 0], [0.5, 0.0], [0.6, 0.0]
        )
        assert abs(residual) <= 1e-12

    def test_drivers_sum_to_overall_change(self):
        """Generic test: driver contributions sum exactly to overall change."""
        import numpy as np
        rng = np.random.default_rng(42)
        for _ in range(5):
            vols_c = rng.integers(10, 100, 5)
            vols_p = rng.integers(10, 100, 5)
            rates_c = rng.uniform(0.2, 0.9, 5)
            rates_p = rng.uniform(0.2, 0.9, 5)
            drivers, overall, sum_re, sum_me, residual, tcr, tpr = decompose(
                list(vols_c), list(vols_p), list(rates_c), list(rates_p)
            )
            assert abs(residual) <= 1e-13, f"Random test residual: {residual}"
