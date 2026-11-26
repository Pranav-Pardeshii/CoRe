"""Main Streamlit UI for CoRe - MHT-CET College Finder."""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from frontend.api_client import (  # noqa: E402
    fetch_catalog_filters,
    fetch_recommendations,
    fetch_trends,
)
from frontend.auth_ui import is_logged_in, render_auth_sidebar  # noqa: E402
from frontend.category_labels import decode_category  # noqa: E402
from frontend.saved_list_ui import render_saved_list_sidebar, save_college  # noqa: E402

PAGE_SIZE = 10  # must satisfy backend's ge=5, le=30

st.set_page_config(
    page_title="CoRe - MHT-CET College Finder",
    page_icon="🐦‍🔥",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2.5rem; max-width: 780px; }
    .core-subtitle {
        color: #6b7280; font-size: 0.95rem; margin-top: -0.6rem; margin-bottom: 1.5rem;
    }
    .college-name { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.1rem; }
    .college-branch { color: #6b7280; font-size: 0.85rem; margin-bottom: 0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def load_catalog_filters() -> tuple[dict[str, Any] | None, str | None]:
    """Fetch and cache dynamic catalog filter options from the backend."""
    result = fetch_catalog_filters()
    if not result.ok:
        return None, result.error or "Failed to load catalog filters."
    return dict(result.data), None


def fetch_page(filters: dict[str, Any], page: int) -> bool:
    """Fetch one page of recommendations and store results in session_state."""
    params = {**filters, "page": page, "page_size": PAGE_SIZE}
    result = fetch_recommendations(params)
    if not result.ok:
        st.error(f"Request failed: {result.error or 'Unknown error'}")
        return False
    st.session_state["results"] = result.data
    st.session_state["current_page"] = page
    st.session_state["active_filters"] = filters
    return True


render_auth_sidebar()
render_saved_list_sidebar()

st.title("CoRe")
st.markdown(
    '<p class="core-subtitle">'
    "Find engineering colleges you're eligible for, based on your MHT-CET percentile.</p>",
    unsafe_allow_html=True,
)

catalog_data, catalog_error = load_catalog_filters()
if catalog_data is None:
    st.error(f"Unable to load filter options from the backend: {catalog_error}")
    st.stop()

categories = ["All", *[str(c) for c in catalog_data.get("categories", []) if c != "All"]]
branches = ["All", *[str(b) for b in catalog_data.get("branches", []) if b != "All"]]
divisions = ["All", *[str(d) for d in catalog_data.get("divisions", []) if d != "All"]]
default_cat_idx = categories.index("GOPENS") if "GOPENS" in categories else 0

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        percentile = st.number_input(
            "Your percentile",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            format="%.2f",
        )
        branch = st.selectbox("Preferred branch", branches)
    with col2:
        category = st.selectbox(
            "Your category",
            categories,
            index=default_cat_idx,
            format_func=decode_category,
        )
        if category == "All":
            st.caption("Note: 'All' mixes General, Reserved, PWD, and Orphan cutoffs together.")
        division = st.selectbox("Preferred division", divisions)

    search_clicked = st.button("Find Colleges", use_container_width=True, type="primary")

st.write("")

if search_clicked:
    with st.spinner("Searching colleges that match your profile..."):
        filters = {
            "percentile": percentile,
            "category": category,
            "branch": branch,
            "division": division,
        }
        fetch_page(filters, page=1)

if "results" in st.session_state:
    data = st.session_state["results"]
    total = int(data["count"])

    if total == 0:
        st.warning(
            "No colleges matched. Try lowering your percentile or "
            "widening branch/division to 'All'."
        )
    else:
        st.success(f"Found {total} eligible college{'s' if total != 1 else ''} for your profile.")
        st.write("")
        active_category = st.session_state.get("active_filters", {}).get("category", category)

        for college in data["eligible_colleges"]:
            safe_college = html.escape(str(college["college"]))
            safe_branch = html.escape(str(college["branch"]))
            branch_code = str(college["branch_code"])

            with st.container(border=True):
                st.markdown(
                    f'<div class="college-name">{safe_college}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="college-branch">{safe_branch}</div>',
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns(2)
                c1.metric("Min Cutoff", f"{college['min_cutoff']:.2f}")
                c2.metric("Max Cutoff", f"{college['max_cutoff']:.2f}")
                normalized = min(max(float(college["max_cutoff"]) / 100.0, 0.0), 1.0)
                st.progress(normalized)

                trend_col, save_col = st.columns([3, 1])
                with trend_col:
                    trend_clicked = st.button("View cutoff trend", key=f"trend_{branch_code}")
                with save_col:
                    if is_logged_in():
                        if st.button(
                            "💾 Save",
                            key=f"save_{branch_code}",
                            use_container_width=True,
                        ):
                            save_college(branch_code)
                    else:
                        st.caption("Log in to save")

                if trend_clicked:
                    trend_result = fetch_trends(branch_code, str(active_category))
                    if not trend_result.ok:
                        st.error(f"Couldn't load trend: {trend_result.error or 'Unknown error'}")
                    elif trend_result.data["count"] == 0:
                        st.info("Not enough historical data for a trend.")
                    else:
                        trends_list = trend_result.data["trends"]
                        df = pd.DataFrame(trends_list)
                        df["series"] = df["year"].astype(str) + " (" + df["level"].astype(str) + ")"
                        percentiles = [float(point["percentile"]) for point in trends_list]
                        y_min = min(percentiles) - 1.0
                        y_max = max(percentiles) + 1.0

                        chart = (
                            alt.Chart(df)
                            .mark_line(point=True)
                            .encode(
                                x=alt.X("round:O", title="CAP Round"),
                                y=alt.Y(
                                    "percentile:Q",
                                    title="Percentile",
                                    scale=alt.Scale(domain=[y_min, y_max]),
                                ),
                                color=alt.Color("series:N", title="Year (Level)"),
                                tooltip=["year:O", "round:O", "level:N", "percentile:Q"],
                            )
                        )
                        st.altair_chart(chart, use_container_width=True)

        current_page = int(st.session_state["current_page"])
        total_pages = -(-total // PAGE_SIZE)

        st.write("")
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if (
                current_page > 1
                and st.button("← Previous", use_container_width=True)
                and fetch_page(st.session_state["active_filters"], page=current_page - 1)
            ):
                st.rerun()
        with nav_col2:
            st.markdown(
                "<div style='text-align:center; color:#6b7280;'>"
                f"Page {current_page} of {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with nav_col3:
            if (
                current_page < total_pages
                and st.button("Next →", use_container_width=True)
                and fetch_page(st.session_state["active_filters"], page=current_page + 1)
            ):
                st.rerun()
