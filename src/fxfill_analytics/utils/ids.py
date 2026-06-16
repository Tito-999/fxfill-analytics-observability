"""
Deterministic ID generation with configurable prefix and zero-padding.

All IDs use a fixed counter per prefix to ensure reproducibility
when combined with a fixed random seed.
"""

import itertools
from collections.abc import Iterator


def generate_ids(prefix: str, count: int, width: int = 6) -> list[str]:
    """
    Generate a list of deterministic IDs.

    Args:
        prefix: ID prefix (e.g., 'U' for users, 'EVT' for events).
        count: Number of IDs to generate.
        width: Zero-padded numeric width.

    Returns:
        List of formatted IDs like ['U000001', 'U000002', ...].

    Examples:
        >>> generate_ids('U', 3)
        ['U000001', 'U000002', 'U000003']
        >>> generate_ids('EVT', 2, width=4)
        ['EVT0001', 'EVT0002']
    """
    return [f"{prefix}{i:0{width}d}" for i in range(1, count + 1)]


def id_counter(prefix: str, width: int = 6) -> Iterator[str]:
    """Return an infinite iterator of sequential IDs with the given prefix."""
    for i in itertools.count(1):
        yield f"{prefix}{i:0{width}d}"
