"""
Deterministic distribution helpers for synthetic data generation.

All random processes use a NumPy Generator with fixed seed for reproducibility.
"""

from typing import Any

import numpy as np


def weighted_choice(
    rng: np.random.Generator,
    choices: list[Any],
    weights: list[float],
    count: int,
) -> list[Any]:
    """
    Sample from a categorical distribution with given weights.

    Args:
        rng: Seeded NumPy random generator.
        choices: List of possible values.
        weights: Probability weights (must sum to ~1).
        count: Number of samples.

    Returns:
        List of sampled values.
    """
    normalized = np.array(weights, dtype=float) / np.sum(weights)
    indices = rng.choice(len(choices), size=count, p=normalized)
    return [choices[i] for i in indices]


def lognormal_params(mean_ms: float, std_ms: float) -> tuple[float, float]:
    """
    Convert desired mean/std in milliseconds to lognormal (mu, sigma).

    For lognormal: E[X] = exp(mu + sigma^2/2), Var[X] = (exp(sigma^2)-1)*exp(2*mu+sigma^2).
    """
    if mean_ms <= 0 or std_ms <= 0:
        raise ValueError("mean_ms and std_ms must be positive")
    sigma2 = float(np.log(1 + (std_ms**2) / (mean_ms**2)))
    mu = float(np.log(mean_ms) - sigma2 / 2)
    return mu, float(np.sqrt(sigma2))


def sample_lognormal(
    rng: np.random.Generator,
    mu: float,
    sigma: float,
    count: int,
    min_val: float = 0.0,
) -> np.ndarray:
    """Sample from lognormal, clamped to min_val."""
    samples = rng.lognormal(mu, sigma, size=count)
    return np.maximum(samples, min_val)


def random_bool(rng: np.random.Generator, probability: float, count: int) -> np.ndarray:
    """Generate boolean array with given probability of True."""
    return rng.random(size=count) < probability
