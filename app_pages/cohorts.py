"""
cohorts.py  —  Cohort Tracker

Single-page, filter-free dashboard. Coaches select their cohort from
the sidebar dropdown to see funnel summary + learner roster.
"""

import datetime as dt

import pandas as pd
import streamlit as st

from settings import initialize
from cohort_aliases import cohort_for_display, display_name
from colors import FUNNEL_STEP_COLORS
from data import load_all_cohorts, load_cohort_users
from metrics import compute_funnel, compute_kpis
from ui import (
    funnel_dropoff_chart,
    funnel_tile_html,
    inject_css,
    kpi_tile_html,
)


STALE_DAYS = 7


initialize()
inject_css()


# ============================================================
# Formatting helpers
# ============================================================
def fmt_pct(v: float) -> str:
    return f"{v:.1%}"


def fmt_num(v: float) -> str:
    return f"{v:,.0f}"


def learner_status(row, today: dt.date) -> str:
    last = row["last_event_date"]
    if pd.notna(last):
        days_since = (today - pd.Timestamp(last).date()).days
        if days_since > STALE_DAYS:
            return "Stalled"
    if row["ra_flag"] == 1:
        return "Reader ✓"
    if row["la_flag"] == 1:
        return "Learner"
    if row["pc_flag"] == 1:
        return "Exploring"
    return "Just started"


# ============================================================
# Sidebar — cohort picker
# ============================================================
with st.sidebar:
    st.markdown("### Curious Learning")
    st.markdown("---")
    cohorts = sorted(load_all_cohorts(), key=display_name)
    if not cohorts:
        st.error("No cohorts available.")
        st.stop()

    qp_cohort = st.query_params.get("cohort")
    matched = cohort_for_display(qp_cohort, cohorts) if qp_cohort else None
    default_index = cohorts.index(matched) if matched in cohorts else 0
    cohort_name = st.selectbox(
        "Select Cohort",
        cohorts,
        index=default_index,
        format_func=display_name,
        key="cohort_picker",
    )
    cohort_label = display_name(cohort_name)
    if st.query_params.get("cohort") != cohort_label:
        st.query_params["cohort"] = cohort_label

# ============================================================
# Load data
# ============================================================
with st.spinner("Loading cohort…"):
    df = load_cohort_users(cohort_name)

if df.empty:
    st.warning("No learners found for this cohort.")
    st.stop()

df["active_span"] = df["active_span"].clip(lower=0)

with st.sidebar:
    st.markdown(f"**{len(df):,}** learners")
    st.caption("Data refreshes daily.")
    st.markdown("---")
    with st.expander("About this dashboard"):
        st.markdown(
            f"""
            **Funnel steps**

            - **LR** — Learner Reached
            - **PC** — Puzzle Completed
            - **LA** — Learner Acquired (reached level 1)
            - **RA** — Reader Acquired (reached level 25)
            - **GC** — Game Completed

            **Active Span** is the number of days between a learner's
            first and last recorded event — *not* a count of days played.
            A span of `0d` means the learner has only one day of recorded
            activity so far.

            **Status**

            - **Reader ✓** — reached level 25
            - **Learner** — reached level 1
            - **Exploring** — completed a puzzle but not yet level 1
            - **Just started** — no milestone reached yet
            - **Stalled** — no activity in the last {STALE_DAYS} days,
              regardless of milestone

            **Data caveat.** Curious Reader can be played offline.
            Events generated while a device is offline are not recovered
            once the device reconnects, so totals may understate true
            activity.
            """
        )

# ============================================================
# Page header
# ============================================================
st.markdown(
    f"## {cohort_label}"
    f"<span class='ct-cohort-badge'>{len(df):,} learners</span>",
    unsafe_allow_html=True,
)

# ============================================================
# Cohort overview — KPI tiles
# ============================================================
st.markdown('<p class="ct-section-header">Cohort Overview</p>', unsafe_allow_html=True)

kpis = compute_kpis(df)
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        kpi_tile_html("Total Learners", fmt_num(kpis["total_users"])),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        kpi_tile_html("% Learner Acquired", fmt_pct(kpis["pct_la"]), sub="Reached level 1"),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        kpi_tile_html("% Reader Acquired", fmt_pct(kpis["pct_ra"]), sub="Reached level 25"),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        kpi_tile_html("Avg Level", f"{kpis['avg_max_level']:.1f}"),
        unsafe_allow_html=True,
    )

st.markdown("")

# ============================================================
# Funnel tiles — single row of 8
# ============================================================
funnel = compute_funnel(df)
funnel_cols = st.columns(len(funnel))
n_palette = len(FUNNEL_STEP_COLORS)
for i, (col, step) in enumerate(zip(funnel_cols, funnel)):
    bg = FUNNEL_STEP_COLORS[min(i, n_palette - 1)]
    with col:
        st.markdown(
            funnel_tile_html(
                step["abbrev"],
                step["label"],
                step["count"],
                step["pct_of_total"],
                bg,
            ),
            unsafe_allow_html=True,
        )

# ============================================================
# Funnel drop-off chart
# ============================================================
st.markdown("")
st.plotly_chart(funnel_dropoff_chart(funnel), width='content')

# ============================================================
# Learner roster
# ============================================================
st.markdown('<p class="ct-section-header">Learner Roster</p>', unsafe_allow_html=True)

today = dt.date.today()

roster = pd.DataFrame({
    "Learner": df["cr_user_id"].astype(str),
    "Level Reached": df["max_user_level"],
    "Last Active": pd.to_datetime(df["last_event_date"], errors="coerce"),
    "Active Span": df["active_span"],
    "Status": df.apply(lambda r: learner_status(r, today), axis=1),
}).sort_values("Level Reached", ascending=False, na_position="last")

st.dataframe(
    roster,
    hide_index=True,
    width="stretch",
    column_config={
        "Learner": st.column_config.TextColumn(width="medium"),
        "Level Reached": st.column_config.NumberColumn(format="%d"),
        "Last Active": st.column_config.DateColumn(format="MMM D, YYYY"),
        "Active Span": st.column_config.NumberColumn(
            format="%dd",
            help="Days between the learner's first and last recorded event.",
        ),
        "Status": st.column_config.TextColumn(width="small"),
    },
)

st.caption("Data reflects learner activity as of today's last refresh.")
