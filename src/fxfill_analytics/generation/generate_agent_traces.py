"""
Synthetic agent run and span generation.

Each agent run is a trace containing multiple spans with parent-child
relationships mirroring a real document processing pipeline:
  document_classification → ocr_extraction → pii_detection →
  anonymization → risk_detection → field_mapping →
  form_autofill → output_validation
"""

import hashlib
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from fxfill_analytics.generation.distributions import random_bool, weighted_choice
from fxfill_analytics.utils.dates import generate_timestamps

# ── Enum constants ──
MODEL_NAMES = ["gpt-4o-mini-2024-07-18", "gpt-4o-2024-08-06", "claude-haiku-3.5-20241022"]
MODEL_WEIGHTS = [0.40, 0.35, 0.25]

PROMPT_VERSIONS = ["v1.0.0", "v1.1.0", "v2.0.0-beta"]
PROMPT_WEIGHTS = [0.50, 0.35, 0.15]

SPAN_TYPES = ["agent", "llm", "tool", "retrieval", "validation"]
SPAN_TYPE_WEIGHTS = [0.20, 0.40, 0.25, 0.10, 0.05]

SPAN_NAMES = [
    "document_classification",
    "ocr_extraction",
    "pii_detection",
    "anonymization",
    "risk_detection",
    "field_mapping",
    "form_autofill",
    "output_validation",
]

RUN_ERROR_TYPES = [None, "ocr_error", "timeout", "api_error", "parse_error"]
RUN_ERROR_WEIGHTS = [0.85, 0.05, 0.04, 0.03, 0.03]

SPAN_ERROR_TYPES = [None, "timeout", "rate_limit", "invalid_input", "internal_error"]
SPAN_ERROR_WEIGHTS = [0.90, 0.03, 0.03, 0.02, 0.02]

SPAN_STATUSES = ["ok", "error", "warning"]
SPAN_STATUS_WEIGHTS = [0.85, 0.08, 0.07]

TOOL_NAMES = [None, "ocr_api", "pii_scanner", "risk_api", "field_mapper"]
TOOL_WEIGHTS = [0.40, 0.20, 0.15, 0.15, 0.10]

EXPERIMENT_GROUPS = ["A", "B"]

# ── Model pricing (per million tokens) ──
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini-2024-07-18": (0.150, 0.600),
    "gpt-4o-2024-08-06": (2.500, 10.000),
    "claude-haiku-3.5-20241022": (0.250, 1.250),
}


def _estimate_cost(
    model_names: list[str],
    input_tokens: np.ndarray,
    output_tokens: np.ndarray,
) -> np.ndarray:
    """Calculate estimated cost in USD for each run/span based on model pricing."""
    costs = np.zeros(len(model_names), dtype=float)
    for i, name in enumerate(model_names):
        iprice, oprice = MODEL_PRICES.get(name, (0.0, 0.0))
        costs[i] = (input_tokens[i] * iprice + output_tokens[i] * oprice) / 1_000_000
    return np.round(costs, 6)


def generate_agent_runs(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
    doc_ids: list[str],
    start_date: datetime,
    end_date: datetime,
    *,
    models: list[str] | None = None,
    model_weights: list[float] | None = None,
    prompt_versions: list[str] | None = None,
    prompt_weights: list[float] | None = None,
    success_rate: float = 0.88,
    experiment_fraction: float = 0.10,
    lognormal_mu: float = 8.5,
    lognormal_sigma: float = 0.5,
) -> pd.DataFrame:
    """
    Generate a synthetic agent runs fact table.

    Each run represents one complete document processing trace.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of agent runs to generate.
        user_ids: Pool of user IDs.
        doc_ids: Pool of document IDs.
        start_date: Earliest run start (inclusive).
        end_date: Latest run start (exclusive).
        models: Model name options.
        model_weights: Probability weights for models.
        prompt_versions: Prompt version options.
        prompt_weights: Probability weights for prompt versions.
        success_rate: Fraction of runs that succeed.
        experiment_fraction: Fraction of runs in an experiment.
        lognormal_mu: Mu parameter for lognormal latency distribution.
        lognormal_sigma: Sigma parameter for lognormal latency distribution.

    Returns:
        DataFrame with agent_run_id, trace_id, and all run-level fields.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")
    if not user_ids:
        raise ValueError("user_ids must not be empty")
    if not doc_ids:
        raise ValueError("doc_ids must not be empty")

    models = models or MODEL_NAMES
    model_weights = model_weights or MODEL_WEIGHTS
    prompt_versions = prompt_versions or PROMPT_VERSIONS
    prompt_weights = prompt_weights or PROMPT_WEIGHTS

    n = count
    run_ids = [f"AGN{i:07d}" for i in range(1, n + 1)]
    trace_ids = [f"TRC{i:07d}" for i in range(1, n + 1)]
    task_ids = [f"TSK{i:06d}" for i in range(1, n + 1)]

    started_ats = generate_timestamps(rng, start_date, end_date, n)
    latencies = np.maximum(rng.lognormal(lognormal_mu, lognormal_sigma, size=n).astype(int), 100)
    ended_ats = [started_ats[i] + timedelta(milliseconds=float(latencies[i])) for i in range(n)]

    model_names = weighted_choice(rng, models, model_weights, n)
    input_tokens = rng.integers(5000, 30001, size=n)
    output_tokens = rng.integers(500, 5001, size=n)
    costs = _estimate_cost(model_names, input_tokens, output_tokens)

    # Deterministic experiment group assignment (avoids spurious correlation)
    # Uses MD5 instead of Python hash() which is non-deterministic across processes
    assigned_user_ids = list(rng.choice(user_ids, size=n))
    exp_groups = [
        (
            ("A" if int(hashlib.md5(uid.encode()).hexdigest(), 16) % 2 == 0 else "B")
            if rng.random() < experiment_fraction
            else None
        )
        for uid in assigned_user_ids
    ]

    return pd.DataFrame(
        {
            "agent_run_id": run_ids,
            "trace_id": trace_ids,
            "task_id": task_ids,
            "user_id": assigned_user_ids,
            "document_id": list(rng.choice(doc_ids, size=n)),
            "started_at": started_ats,
            "ended_at": ended_ats,
            "total_latency_ms": list(latencies),
            "total_input_tokens": list(input_tokens),
            "total_output_tokens": list(output_tokens),
            "estimated_cost_usd": list(costs),
            "model_name": model_names,
            "prompt_version": weighted_choice(rng, prompt_versions, prompt_weights, n),
            "tool_call_count": list(rng.integers(3, 11, size=n)),
            "retry_count": list(rng.integers(0, 5, size=n)),
            "success_flag": list(rng.random(size=n) < success_rate),
            "quality_score": list(np.round(rng.uniform(0.70, 1.0, size=n), 2)),
            "field_accuracy": list(np.round(rng.uniform(0.75, 1.0, size=n), 2)),
            "manual_edit_count": list(rng.poisson(2, size=n)),
            "error_type": weighted_choice(
                rng, RUN_ERROR_TYPES, [float(w) for w in RUN_ERROR_WEIGHTS], n
            ),
            "experiment_group": exp_groups,
        }
    )


def generate_agent_spans(
    rng: np.random.Generator,
    count: int,
    trace_ids: list[str],
    start_date: datetime,
    end_date: datetime,
    *,
    span_names: list[str] | None = None,
    span_types: list[str] | None = None,
    span_type_weights: list[float] | None = None,
    models: list[str] | None = None,
    model_weights: list[float] | None = None,
    child_span_probability: float = 0.70,
    lognormal_mu: float = 5.5,
    lognormal_sigma: float = 0.6,
) -> pd.DataFrame:
    """
    Generate a synthetic agent spans fact table.

    Each span belongs to a trace (from agent_runs) and may have a parent span
    within the same trace. Span types distinguish LLM calls from tool calls.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of spans to generate.
        trace_ids: Pool of trace IDs to assign spans to.
        start_date: Earliest span start (inclusive).
        end_date: Latest span start (exclusive).
        span_names: Span name options.
        span_types: Span type options.
        span_type_weights: Probability weights for span types.
        models: Model name options (None for non-LLM spans).
        model_weights: Probability weights for models.
        child_span_probability: Fraction of spans that are children.
        lognormal_mu: Mu parameter for lognormal latency distribution.
        lognormal_sigma: Sigma parameter for lognormal latency distribution.

    Returns:
        DataFrame with span_id, trace_id, parent_span_id, and all span-level fields.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")
    if not trace_ids:
        raise ValueError("trace_ids must not be empty")

    span_names = span_names or SPAN_NAMES
    span_types = span_types or SPAN_TYPES
    span_type_weights = span_type_weights or SPAN_TYPE_WEIGHTS
    models = models or MODEL_NAMES
    model_weights = model_weights or MODEL_WEIGHTS

    n = count
    span_id_list = [f"SPN{i:07d}" for i in range(1, n + 1)]

    # Assign spans to traces
    assigned_traces = list(rng.choice(trace_ids, size=n))

    # Determine span types and names
    span_type_list = weighted_choice(rng, span_types, span_type_weights, n)
    span_name_list = list(rng.choice(span_names, size=n))

    # Parent-child relationships
    is_child = random_bool(rng, child_span_probability, n)
    parent_span_ids: list[str | None] = []
    trace_last_span: dict[str, str] = {}
    for i in range(n):
        trace = assigned_traces[i]
        if is_child[i] and trace in trace_last_span:
            parent_span_ids.append(trace_last_span[trace])
        else:
            parent_span_ids.append(None)
        trace_last_span[trace] = span_id_list[i]

    start_times = generate_timestamps(rng, start_date, end_date, n)
    span_latencies = np.maximum(
        rng.lognormal(lognormal_mu, lognormal_sigma, size=n).astype(int), 10
    )
    end_times = [
        start_times[i] + timedelta(milliseconds=float(span_latencies[i])) for i in range(n)
    ]

    # Only LLM spans have model names and tokens
    is_llm = [t == "llm" for t in span_type_list]
    model_col: list[str | None] = []
    input_tokens: list[int] = []
    output_tokens: list[int] = []
    costs: list[float] = []
    for i in range(n):
        if is_llm[i]:
            mname: str = rng.choice(models, p=model_weights)
            model_col.append(mname)
            it = int(rng.integers(1000, 10001))
            ot = int(rng.integers(100, 2001))
            input_tokens.append(it)
            output_tokens.append(ot)
            iprice, oprice = MODEL_PRICES.get(mname, (0.0, 0.0))
            costs.append(round((it * iprice + ot * oprice) / 1_000_000, 6))
        else:
            model_col.append(None)
            input_tokens.append(0)
            output_tokens.append(0)
            costs.append(0.0)

    return pd.DataFrame(
        {
            "span_id": span_id_list,
            "trace_id": assigned_traces,
            "parent_span_id": parent_span_ids,
            "span_name": span_name_list,
            "span_type": span_type_list,
            "start_time": start_times,
            "end_time": end_times,
            "latency_ms": list(span_latencies),
            "status": weighted_choice(rng, SPAN_STATUSES, SPAN_STATUS_WEIGHTS, n),
            "model_name": model_col,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": costs,
            "tool_name": weighted_choice(rng, TOOL_NAMES, [float(w) for w in TOOL_WEIGHTS], n),
            "error_type": weighted_choice(
                rng, SPAN_ERROR_TYPES, [float(w) for w in SPAN_ERROR_WEIGHTS], n
            ),
            "metadata_json": [r'{"source":"synthetic"}' for _ in range(n)],
        }
    )
