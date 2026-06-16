"""Tests for deterministic ID generation in utils/ids.py."""

from fxfill_analytics.utils.ids import generate_ids, id_counter


class TestGenerateIds:
    def test_same_input_same_output(self):
        ids1 = generate_ids("U", 10)
        ids2 = generate_ids("U", 10)
        assert ids1 == ids2

    def test_different_prefix_different_output(self):
        ids_u = generate_ids("U", 10)
        ids_doc = generate_ids("DOC", 10)
        assert ids_u != ids_doc

    def test_no_hash_dependency(self):
        """IDs should not depend on Python hash()."""
        ids1 = generate_ids("TEST", 5)
        ids2 = generate_ids("TEST", 5)
        assert ids1 == ids2

    def test_zero_count(self):
        ids = generate_ids("X", 0)
        assert ids == []

    def test_unique_within_batch(self):
        ids = generate_ids("EVT", 1000)
        assert len(ids) == len(set(ids)), "IDs should be unique"

    def test_large_batch_no_collision(self):
        ids = generate_ids("L", 50000)
        assert len(ids) == len(set(ids)), "No collisions in large batches"


class TestIdCounter:
    def test_counter_generates_sequential(self):
        counter = id_counter("X")
        first = next(counter)
        second = next(counter)
        third = next(counter)
        assert first != second != third
        assert len({first, second, third}) == 3

    def test_counter_is_infinite(self):
        counter = id_counter("INF")
        ids = [next(counter) for _ in range(100)]
        assert len(ids) == len(set(ids))
