"""Tests for distribution helpers in distributions.py."""

import numpy as np
import pytest
from fxfill_analytics.generation.distributions import (
    lognormal_params,
    random_bool,
    sample_lognormal,
    weighted_choice,
)


class TestWeightedChoice:
    def test_output_length(self):
        rng = np.random.default_rng(42)
        result = weighted_choice(rng, ["a", "b", "c"], [0.5, 0.3, 0.2], 100)
        assert len(result) == 100

    def test_all_values_in_choices(self):
        rng = np.random.default_rng(42)
        result = weighted_choice(rng, ["x", "y"], [0.5, 0.5], 50)
        assert all(v in ["x", "y"] for v in result)

    def test_reproducible_with_seed(self):
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        result1 = weighted_choice(rng1, list("ABCDE"), [0.2] * 5, 20)
        result2 = weighted_choice(rng2, list("ABCDE"), [0.2] * 5, 20)
        assert result1 == result2


class TestLognormalParams:
    def test_positive_inputs(self):
        mu, sigma = lognormal_params(500.0, 200.0)
        assert mu > 0
        assert sigma > 0

    def test_zero_mean_raises(self):
        with pytest.raises(ValueError, match="positive"):
            lognormal_params(0.0, 100.0)

    def test_negative_std_raises(self):
        with pytest.raises(ValueError, match="positive"):
            lognormal_params(100.0, -10.0)

    def test_zero_std_raises(self):
        with pytest.raises(ValueError, match="positive"):
            lognormal_params(100.0, 0.0)


class TestSampleLognormal:
    def test_output_shape(self):
        rng = np.random.default_rng(42)
        mu, sigma = lognormal_params(500.0, 200.0)
        samples = sample_lognormal(rng, mu, sigma, 100)
        assert len(samples) == 100

    def test_min_val_enforced(self):
        rng = np.random.default_rng(42)
        mu, sigma = lognormal_params(500.0, 200.0)
        samples = sample_lognormal(rng, mu, sigma, 100, min_val=100.0)
        assert np.all(samples >= 100.0)

    def test_all_non_negative_with_default_min(self):
        rng = np.random.default_rng(42)
        mu, sigma = lognormal_params(500.0, 200.0)
        samples = sample_lognormal(rng, mu, sigma, 100)
        assert np.all(samples >= 0.0)

    def test_reproducible_with_seed(self):
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        mu, sigma = lognormal_params(500.0, 200.0)
        s1 = sample_lognormal(rng1, mu, sigma, 50)
        s2 = sample_lognormal(rng2, mu, sigma, 50)
        assert np.array_equal(s1, s2)


class TestRandomBool:
    def test_output_shape(self):
        rng = np.random.default_rng(42)
        result = random_bool(rng, 0.5, 100)
        assert len(result) == 100

    def test_probability_zero(self):
        rng = np.random.default_rng(42)
        result = random_bool(rng, 0.0, 100)
        assert not np.any(result)

    def test_probability_one(self):
        rng = np.random.default_rng(42)
        result = random_bool(rng, 1.0, 100)
        assert np.all(result)

    def test_dtype_is_bool(self):
        rng = np.random.default_rng(42)
        result = random_bool(rng, 0.3, 10)
        assert result.dtype == bool

    def test_reproducible_with_seed(self):
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        r1 = random_bool(rng1, 0.3, 20)
        r2 = random_bool(rng2, 0.3, 20)
        assert np.array_equal(r1, r2)
