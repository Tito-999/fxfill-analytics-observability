"""Load experiment configuration from YAML with sensible defaults.

This module wraps `settings.get_experiments_config()` and enriches the
raw experiment definition with analysis-level defaults so callers never
need to handle missing keys.
"""

from __future__ import annotations

from typing import Any

from fxfill_analytics import settings

# ---------------------------------------------------------------------------
# Defaults applied when a key is absent from the experiment config
# ---------------------------------------------------------------------------
DEFAULT_SIGNIFICANCE_LEVEL: float = 0.05
DEFAULT_BOOTSTRAP_ITERATIONS: int = 10000
DEFAULT_SRM_SIGNIFICANCE_LEVEL: float = 0.05

_DEFAULT_CONFIG: dict[str, Any] = {
    "significance_level": DEFAULT_SIGNIFICANCE_LEVEL,
    "bootstrap_iterations": DEFAULT_BOOTSTRAP_ITERATIONS,
    "srm_significance_level": DEFAULT_SRM_SIGNIFICANCE_LEVEL,
}


def load_experiment_config(experiment_id: str | None = None) -> dict[str, Any]:
    """Load experiment configuration, returning a merged dict with defaults.

    Parameters
    ----------
    experiment_id : str, optional
        Key identifying the experiment in ``experiments.yml``.
        If *None* the first experiment found is returned.

    Returns
    -------
    dict
        Experiment-specific settings merged with analysis defaults.
    """
    raw = settings.get_experiments_config()
    experiments: dict[str, Any] = raw.get("experiments", {})

    if experiment_id is None:
        keys = list(experiments.keys())
        if not keys:
            raise ValueError("No experiments found in configuration")
        experiment_id = keys[0]

    if experiment_id not in experiments:
        raise KeyError(
            f"Experiment {experiment_id!r} not found. "
            f"Available: {list(experiments.keys())}"
        )

    config: dict[str, Any] = experiments[experiment_id]

    # Sprinkle analysis defaults
    analysis = config.get("analysis", {})
    analysis.setdefault("significance_level", DEFAULT_SIGNIFICANCE_LEVEL)
    analysis.setdefault("bootstrap_iterations", DEFAULT_BOOTSTRAP_ITERATIONS)
    analysis.setdefault("srm_significance_level", DEFAULT_SRM_SIGNIFICANCE_LEVEL)
    config["analysis"] = analysis

    return config
