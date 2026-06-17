"""Global filter sidebar for Streamlit dashboard."""

from datetime import date, timedelta

import streamlit as st

from dashboard.services.database import get_min_max_dates


def init_filters():
    """Initialize filter state in session."""
    if "filters_initialized" not in st.session_state:
        min_d, max_d = get_min_max_dates()
        if min_d and max_d:
            st.session_state.date_start = max(date.today() - timedelta(days=30), min_d)
            st.session_state.date_end = max_d
            st.session_state.min_date = min_d
            st.session_state.max_date = max_d
        st.session_state.filters_initialized = True


def render_filters(page: str = "all"):
    """Render filter sidebar. Returns dict of active filters."""
    init_filters()

    with st.sidebar:
        st.markdown("### Filters")

        d1 = st.date_input(
            "Date Range",
            value=(
                st.session_state.get("date_start", date.today() - timedelta(30)),
                st.session_state.get("date_end", date.today()),
            ),
            min_value=st.session_state.get("min_date", date(2026, 1, 1)),
            max_value=st.session_state.get("max_date", date(2026, 12, 31)),
            key="date_filter",
        )

        if d1 and len(d1) == 2:
            st.session_state.date_start = d1[0]
            st.session_state.date_end = d1[1]

        filters = {"date_start": st.session_state.date_start, "date_end": st.session_state.date_end}

        if page in ("all", "funnel", "executive", "feature"):
            filters["device_type"] = st.selectbox(
                "Device Type", ["All", "desktop", "mobile", "tablet"], key="filter_device"
            )

        if page in ("all", "funnel", "executive"):
            filters["acquisition_channel"] = st.selectbox(
                "Channel",
                ["All", "organic", "paid_search", "social", "referral", "campus"],
                key="filter_channel",
            )

        if page in ("all", "funnel", "feature"):
            filters["complexity"] = st.selectbox(
                "Complexity", ["All", "simple", "medium", "complex"], key="filter_complexity"
            )

        if page in ("all", "agent", "root_cause"):
            filters["model_name"] = st.selectbox(
                "Model",
                ["All", "gpt-4o-mini-2024-07-18", "gpt-4o-2024-08-06", "claude-haiku-3.5-20241022"],
                key="filter_model",
            )

        if page in ("all", "ab_test"):
            filters["experiment_group"] = st.selectbox(
                "Experiment Group", ["All", "A", "B"], key="filter_exp_group"
            )

        if st.button("Reset Filters"):
            for k in list(st.session_state.keys()):
                if k.startswith("filter_") or k.startswith("date_"):
                    del st.session_state[k]
            st.rerun()

        st.caption(f"Showing: {filters.get('date_start')} → {filters.get('date_end')}")

    return filters
