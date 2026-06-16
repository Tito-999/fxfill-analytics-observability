"""
Synthetic document dimension table generation.

Generates documents with types, languages, complexity levels,
PII and risk indicators, and creation timestamps.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from fxfill_analytics.generation.distributions import random_bool, weighted_choice
from fxfill_analytics.utils.dates import generate_timestamps

# ── Enum constants ──
DOCUMENT_TYPES = [
    "bank_transfer_form",
    "invoice",
    "identity_document",
    "beneficiary_form",
    "exchange_declaration",
]
LANGUAGES = ["en", "zh", "ja", "de", "es", "fr"]
COMPLEXITY_LEVELS = ["simple", "medium", "complex"]

# ── Default probability weights ──
DOC_TYPE_WEIGHTS = [0.25, 0.25, 0.15, 0.20, 0.15]
COMPLEXITY_WEIGHTS = [0.40, 0.35, 0.25]


def generate_documents(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
    start_date: datetime,
    end_date: datetime,
    *,
    doc_types: list[str] | None = None,
    doc_type_weights: list[float] | None = None,
    languages: list[str] | None = None,
    complexity_levels: list[str] | None = None,
    complexity_weights: list[float] | None = None,
    pii_probability: float = 0.55,
    high_risk_probability: float = 0.25,
    max_page_count: int = 15,
) -> pd.DataFrame:
    """
    Generate a synthetic document dimension table.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of documents to generate.
        user_ids: Pool of user IDs to assign as document owners.
        start_date: Earliest creation timestamp (inclusive).
        end_date: Latest creation timestamp (exclusive).
        doc_types: Document type options.
        doc_type_weights: Probability weights for document types.
        languages: Language options.
        complexity_levels: Complexity level options.
        complexity_weights: Probability weights for complexity levels.
        pii_probability: Fraction of documents containing PII.
        high_risk_probability: Fraction with high-risk terms.
        max_page_count: Maximum page count (inclusive upper bound, min=1).

    Returns:
        DataFrame with document_id, user_id, and dimension columns.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")
    if not user_ids:
        raise ValueError("user_ids must not be empty")

    doc_types = doc_types or DOCUMENT_TYPES
    doc_type_weights = doc_type_weights or DOC_TYPE_WEIGHTS
    languages = languages or LANGUAGES
    complexity_levels = complexity_levels or COMPLEXITY_LEVELS
    complexity_weights = complexity_weights or COMPLEXITY_WEIGHTS

    doc_ids = [f"DOC{i:06d}" for i in range(1, count + 1)]
    created_ats = generate_timestamps(rng, start_date, end_date, count)

    return pd.DataFrame(
        {
            "document_id": doc_ids,
            "user_id": list(rng.choice(user_ids, size=count)),
            "document_type": weighted_choice(rng, doc_types, doc_type_weights, count),
            "language": list(rng.choice(languages, size=count)),
            "page_count": list(rng.integers(1, max_page_count + 1, size=count)),
            "complexity_level": weighted_choice(rng, complexity_levels, complexity_weights, count),
            "contains_pii": random_bool(rng, pii_probability, count),
            "contains_high_risk_terms": random_bool(rng, high_risk_probability, count),
            "created_at": created_ats,
        }
    )
