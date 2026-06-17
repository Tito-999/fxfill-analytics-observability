"""Unit tests for date clamping in dashboard filters."""

from datetime import date

import pytest

from dashboard.components.filters import clamp_date_range


class TestClampDateRangeDefaults:
    def test_none_values_use_last_30_days(self):
        start, end = clamp_date_range(
            None, None, min_date=date(2026, 2, 14), max_date=date(2026, 6, 13)
        )
        assert start == date(2026, 5, 14)
        assert end == date(2026, 6, 13)

    def test_none_end_defaults_to_max(self):
        start, end = clamp_date_range(
            date(2026, 5, 1), None, min_date=date(2026, 2, 14), max_date=date(2026, 6, 13)
        )
        assert start == date(2026, 5, 1)
        assert end == date(2026, 6, 13)


class TestClampDateRangeStaleDates:
    def test_stale_end_clamped_to_max(self):
        """Regression: stale browser session end date beyond new DB max."""
        start, end = clamp_date_range(
            start=date(2026, 5, 18),
            end=date(2026, 6, 17),
            min_date=date(2026, 2, 14),
            max_date=date(2026, 6, 13),
        )
        assert start == date(2026, 5, 18)
        assert end == date(2026, 6, 13)
        assert date(2026, 2, 14) <= start <= end <= date(2026, 6, 13)

    def test_stale_start_clamped_to_min(self):
        start, end = clamp_date_range(
            start=date(2026, 1, 1),
            end=date(2026, 6, 13),
            min_date=date(2026, 2, 14),
            max_date=date(2026, 6, 13),
        )
        assert start == date(2026, 2, 14)
        assert end == date(2026, 6, 13)

    def test_both_stale_clamped(self):
        start, end = clamp_date_range(
            start=date(2025, 1, 1),
            end=date(2027, 1, 1),
            min_date=date(2026, 2, 14),
            max_date=date(2026, 6, 13),
        )
        assert start == date(2026, 2, 14)
        assert end == date(2026, 6, 13)


class TestClampDateRangeEdgeCases:
    def test_start_after_end_uses_default(self):
        start, end = clamp_date_range(
            start=date(2026, 6, 1),
            end=date(2026, 5, 1),
            min_date=date(2026, 2, 14),
            max_date=date(2026, 6, 13),
        )
        assert start == date(2026, 5, 14)
        assert end == date(2026, 6, 13)

    def test_single_day_range(self):
        d = date(2026, 5, 1)
        start, end = clamp_date_range(None, None, min_date=d, max_date=d)
        assert start == d
        assert end == d

    def test_invalid_bounds_raises(self):
        with pytest.raises(ValueError, match="min_date must not be after max_date"):
            clamp_date_range(None, None, min_date=date(2026, 6, 1), max_date=date(2026, 1, 1))


class TestClampDateRangeInvariants:
    def test_all_outputs_in_bounds(self):
        import itertools

        dates = [date(2026, 1, 1), date(2026, 6, 1), date(2026, 12, 31), None]
        min_d = date(2026, 2, 14)
        max_d = date(2026, 6, 13)
        for s, e in itertools.product(dates, dates):
            start, end = clamp_date_range(s, e, min_date=min_d, max_date=max_d)
            assert min_d <= start <= end <= max_d, f"Failed for {s}, {e}: got {start}, {end}"
