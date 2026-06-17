"""Global filter sidebar with robust date clamping and page-specific controls."""

from datetime import date, timedelta

import streamlit as st

from dashboard.services.database import get_min_max_dates

FILTER_STATE_KEYS = {
    "date_filter",
    "date_start",
    "date_end",
    "min_date",
    "max_date",
    "_date_bounds",
    "filters_initialized",
    "filter_device",
    "filter_channel",
    "filter_complexity",
    "filter_model",
    "filter_exp_group",
}

PAGE_FILTERS = {
    "executive": {"date"},
    "funnel": {"date", "channel", "device", "complexity"},
    "feature": {"date", "device", "complexity"},
    "agent": {"date"},
    "ab_test": {"experiment_group"},
    "root_cause": {"date"},
    "data_quality": set(),
}


def clamp_date_range(
    start: date | None,
    end: date | None,
    min_date: date,
    max_date: date,
    window_days: int = 30,
) -> tuple[date, date]:
    if min_date > max_date:
        raise ValueError("min_date must not be after max_date")
    default_end = max_date
    default_start = max(min_date, max_date - timedelta(days=window_days))
    if start is None:
        start = default_start
    if end is None:
        end = default_end
    start = max(min_date, min(start, max_date))
    end = max(min_date, min(end, max_date))
    if start > end:
        return default_start, default_end
    return start, end


def init_filters() -> None:
    min_d, max_d = get_min_max_dates()
    if min_d is None or max_d is None:
        fallback = date.today()
        min_d = fallback
        max_d = fallback
    current_bounds = (min_d, max_d)
    previous_bounds = st.session_state.get("_date_bounds")
    if previous_bounds != current_bounds:
        st.session_state.pop("date_filter", None)
    start, end = clamp_date_range(
        start=st.session_state.get("date_start"),
        end=st.session_state.get("date_end"),
        min_date=min_d,
        max_date=max_d,
    )
    st.session_state.date_start = start
    st.session_state.date_end = end
    st.session_state.min_date = min_d
    st.session_state.max_date = max_d
    st.session_state._date_bounds = current_bounds
    st.session_state.filters_initialized = True


def render_filters(page_name: str = "executive"):
    init_filters()
    allowed = PAGE_FILTERS.get(page_name, {"date"})

    # Data quality page has no business filters
    if page_name == "data_quality":
        st.sidebar.markdown("### Data Quality")
        st.sidebar.caption("Audit reports are not controlled by product filters.")
        return {}

    with st.sidebar:
        st.markdown("### Filters")

        if "date" in allowed:
            safe_start, safe_end = clamp_date_range(
                st.session_state.get("date_start"),
                st.session_state.get("date_end"),
                st.session_state.min_date,
                st.session_state.max_date,
            )
            selected = st.date_input(
                "Date Range",
                value=(safe_start, safe_end),
                min_value=st.session_state.min_date,
                max_value=st.session_state.max_date,
                key="date_filter",
            )
            if isinstance(selected, tuple) and len(selected) == 2:
                clamped = clamp_date_range(
                    selected[0],
                    selected[1],
                    st.session_state.min_date,
                    st.session_state.max_date,
                )
                st.session_state.date_start = clamped[0]
                st.session_state.date_end = clamped[1]

        filters = {
            "date_start": st.session_state.get("date_start"),
            "date_end": st.session_state.get("date_end"),
        }

        if "channel" in allowed:
            filters["acquisition_channel"] = st.selectbox(
                "Channel",
                ["All", "organic", "paid_search", "social", "referral", "campus"],
                key="filter_channel",
            )

        if "device" in allowed:
            filters["device_type"] = st.selectbox(
                "Device Type", ["All", "desktop", "mobile", "tablet"], key="filter_device"
            )

        if "complexity" in allowed:
            filters["complexity"] = st.selectbox(
                "Complexity", ["All", "simple", "medium", "complex"], key="filter_complexity"
            )

        if "experiment_group" in allowed:
            filters["experiment_group"] = st.selectbox(
                "Experiment Group", ["All", "A", "B"], key="filter_exp_group"
            )

        if st.button("Reset Filters"):
            for key in FILTER_STATE_KEYS:
                st.session_state.pop(key, None)
            st.rerun()

        if "date" in allowed:
            st.caption(f"Showing: {filters.get('date_start')} -> {filters.get('date_end')}")

    return filters
