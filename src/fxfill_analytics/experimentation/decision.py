"""Rule-based experiment decision engine.

Produces one of five possible decisions:

* ``SHIP`` — primary significant, all guardrails pass.
* ``SHIP_WITH_MONITORING`` — primary significant, minor guardrail degradation.
* ``CONTINUE_EXPERIMENT`` — primary not significant, no safety concerns.
* ``STOP_FOR_HARM`` — severe guardrail degradation.
* ``INCONCLUSIVE`` — SRM, data validation failure, or ambiguous results.
"""

from __future__ import annotations

from typing import Any

from fxfill_analytics.experimentation.config import load_experiment_config

# ---------------------------------------------------------------------------
# Decision labels
# ---------------------------------------------------------------------------
SHIP = "SHIP"
SHIP_WITH_MONITORING = "SHIP_WITH_MONITORING"
CONTINUE_EXPERIMENT = "CONTINUE_EXPERIMENT"
STOP_FOR_HARM = "STOP_FOR_HARM"
INCONCLUSIVE = "INCONCLUSIVE"

_SEVERE_DEGRADATION_PCT = 50.0  # >50 % change triggers STOP_FOR_HARM


def make_decision(
    primary_result: dict[str, Any] | None = None,
    guardrail_results: list[dict[str, Any]] | None = None,
    srm_passed: bool = True,
    data_validation_passed: bool = True,
    experiment_id: str | None = None,
) -> dict[str, Any]:
    """Produce a rule-based experiment decision.

    Parameters
    ----------
    primary_result : dict or None
        Result dict for the primary metric (must contain ``p_value`` or
        ``welch_p_value`` and ``mean_diff`` or ``risk_difference``).
    guardrail_results : list[dict] or None
        List of results from ``guardrails.test_guardrail``.
    srm_passed : bool
        Whether the SRM test passed.
    data_validation_passed : bool
        Whether data validation passed.
    experiment_id : str, optional
        Used to look up config thresholds (significance level).

    Returns
    -------
    dict
        ``decision`` — one of the five constants above.
        ``reason`` — human-readable explanation.
        ``details`` — sub-dict with diagnostic fields.
    """
    if guardrail_results is None:
        guardrail_results = []

    # ── load significance level from config ──────────────────────────
    alpha = 0.05
    if experiment_id:
        try:
            config = load_experiment_config(experiment_id)
            alpha = config.get("analysis", {}).get("significance_level", 0.05)
        except (KeyError, ValueError):
            pass

    # ------------------------------------------------------------------
    # Decision tree
    # ------------------------------------------------------------------
    # 1. SRM failure → INCONCLUSIVE
    if not srm_passed:
        return {
            "decision": INCONCLUSIVE,
            "reason": "Sample Ratio Mismatch detected.  Results are unreliable.",
            "details": {
                "srm_passed": False,
                "data_validation_passed": data_validation_passed,
                "primary_significant": False,
                "guardrail_failures": [],
            },
        }

    # 2. Data validation failure → INCONCLUSIVE
    if not data_validation_passed:
        return {
            "decision": INCONCLUSIVE,
            "reason": "Data validation failed.  Results may be unreliable.",
            "details": {
                "srm_passed": True,
                "data_validation_passed": False,
                "primary_significant": False,
                "guardrail_failures": [],
            },
        }

    # 3. Identify guardrail failures
    guardrail_failures = [
        g for g in guardrail_results if not g.get("non_inferiority_passed", True)
    ]

    # Check for severe degradation → STOP_FOR_HARM
    severe = [
        g for g in guardrail_failures
        if abs(g.get("diff_pct", 0.0)) >= _SEVERE_DEGRADATION_PCT
    ]
    if severe:
        names = [g.get("metric_name", f"#{i}") for i, g in enumerate(severe)]
        return {
            "decision": STOP_FOR_HARM,
            "reason": f"Severe guardrail degradation: {', '.join(names)}.",
            "details": {
                "srm_passed": True,
                "data_validation_passed": True,
                "primary_significant": False,
                "guardrail_failures": guardrail_failures,
            },
        }

    # 4. Evaluate primary metric
    if primary_result is not None:
        p_value = (
            primary_result.get("p_value")
            or primary_result.get("welch_p_value")
            or primary_result.get("p_value_ztest")
        )
        effect = primary_result.get("mean_diff") or primary_result.get("risk_difference", 0.0)

        is_significant = p_value is not None and p_value < alpha
        direction_positive = effect is not None and float(effect) > 0

        if is_significant and direction_positive:
            if guardrail_failures:
                return {
                    "decision": SHIP_WITH_MONITORING,
                    "reason": (
                        "Primary metric is significantly positive but some "
                        "guardrails show degradation.  Ship with monitoring."
                    ),
                    "details": {
                        "srm_passed": True,
                        "data_validation_passed": True,
                        "primary_significant": True,
                        "guardrail_failures": guardrail_failures,
                    },
                }
            else:
                return {
                    "decision": SHIP,
                    "reason": "Primary metric is significantly positive and all guardrails pass.",
                    "details": {
                        "srm_passed": True,
                        "data_validation_passed": True,
                        "primary_significant": True,
                        "guardrail_failures": [],
                    },
                }

        if not is_significant:
            return {
                "decision": CONTINUE_EXPERIMENT,
                "reason": (
                    "Primary metric is not statistically significant.  "
                    "Continue collecting data or consider stopping."
                ),
                "details": {
                    "srm_passed": True,
                    "data_validation_passed": True,
                    "primary_significant": False,
                    "guardrail_failures": guardrail_failures,
                },
            }

    # 5. Fallback
    return {
        "decision": INCONCLUSIVE,
        "reason": "Could not determine a clear decision from the available data.",
        "details": {
            "srm_passed": srm_passed,
            "data_validation_passed": data_validation_passed,
            "primary_significant": primary_result is not None,
            "guardrail_failures": guardrail_failures,
        },
    }
