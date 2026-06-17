"""FxFill Analytics — Experimentation module.

A/B experiment analysis: configuration loading, Sample Ratio Mismatch testing,
user-level metric computation, statistical estimation (binary and continuous),
bootstrapping, guardrail non-inferiority testing, Benjamini-Hochberg multiplicity
correction, rule-based decision engine, and structured reporting.
"""

from fxfill_analytics.experimentation.config import load_experiment_config
from fxfill_analytics.experimentation.srm import srm_test
from fxfill_analytics.experimentation.metrics import get_user_metrics
from fxfill_analytics.experimentation.estimators import binary_effect, continuous_effect
from fxfill_analytics.experimentation.bootstrap import bootstrap_diff
from fxfill_analytics.experimentation.guardrails import test_guardrail
from fxfill_analytics.experimentation.multiplicity import bh_correction
from fxfill_analytics.experimentation.decision import (
    make_decision,
    SHIP,
    SHIP_WITH_MONITORING,
    CONTINUE_EXPERIMENT,
    STOP_FOR_HARM,
    INCONCLUSIVE,
)
from fxfill_analytics.experimentation.report import generate_report

__all__ = [
    "load_experiment_config",
    "srm_test",
    "get_user_metrics",
    "binary_effect",
    "continuous_effect",
    "bootstrap_diff",
    "test_guardrail",
    "bh_correction",
    "make_decision",
    "SHIP",
    "SHIP_WITH_MONITORING",
    "CONTINUE_EXPERIMENT",
    "STOP_FOR_HARM",
    "INCONCLUSIVE",
    "generate_report",
]
