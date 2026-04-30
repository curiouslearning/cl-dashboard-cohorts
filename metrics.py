"""Funnel and KPI computations over a cohort DataFrame."""

from __future__ import annotations

import pandas as pd
import streamlit as st

FUNNEL_STEPS = [
    {"abbrev": "LR", "label": "Learner Reached",  "col": "lr_flag"},
    {"abbrev": "PC", "label": "Puzzle Completed", "col": "pc_flag"},
    {"abbrev": "LA", "label": "Learner Acquired", "col": "la_flag"},
    {"abbrev": "RA", "label": "Reader Acquired",  "col": "ra_flag"},
    {"abbrev": "GC", "label": "Game Completed",   "col": "gc_flag"},
]


@st.cache_data(ttl="1d", show_spinner=False)
def compute_funnel(df: pd.DataFrame) -> list[dict]:
    total = len(df)
    out: list[dict] = []
    for step in FUNNEL_STEPS:
        count = int((df[step["col"]] == 1).sum())
        out.append({
            **step,
            "count": count,
            "pct_of_total": (count / total) if total else 0.0,
        })
    return out


@st.cache_data(ttl="1d", show_spinner=False)
def compute_kpis(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {
            "total_users": 0,
            "pct_la": 0.0,
            "pct_ra": 0.0,
            "avg_max_level": 0.0,
            "avg_total_time_minutes": 0.0,
        }
    return {
        "total_users": total,
        "pct_la": float((df["la_flag"] == 1).mean()),
        "pct_ra": float((df["ra_flag"] == 1).mean()),
        "avg_max_level": float(df["max_user_level"].mean()),
        "avg_total_time_minutes": float(df["total_time_minutes"].mean()),
    }
