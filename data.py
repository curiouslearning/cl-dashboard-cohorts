"""BigQuery loaders. All cached for one day."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from google.cloud import bigquery

from settings import get_gcp_credentials


_FURTHEST_EVENT_ORDER = [
    "download_completed",
    "tapped_start",
    "selected_level",
    "puzzle_completed",
    "level_completed",
]
_FURTHEST_EVENT_RANK = {e: r for r, e in enumerate(_FURTHEST_EVENT_ORDER)}


def _pick_furthest_progress_row(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse multiple (language, country) rows per learner to one row,
    keeping the row that represents the furthest progress.

    A `level_completed` row always beats a non-`level_completed` row — the
    `is_level_completed` key is what guards against a stray non-completed row
    that happens to carry a non-zero `max_user_level`.
    """
    if df.empty:
        return df
    ranked = df.assign(
        _is_level_completed=(df["furthest_event"] == "level_completed"),
        _event_rank=df["furthest_event"].map(_FURTHEST_EVENT_RANK).fillna(-1),
    )
    ranked = ranked.sort_values(
        ["cr_user_id", "_is_level_completed", "max_user_level", "_event_rank"],
        ascending=[True, False, False, False],
    )
    return (
        ranked.drop_duplicates(subset=["cr_user_id"], keep="first")
        .drop(columns=["_is_level_completed", "_event_rank"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl="1d", show_spinner=False)
def load_all_cohorts() -> list[str]:
    _, bq_client = get_gcp_credentials()
    sql = """
        SELECT DISTINCT cohort_name
        FROM `dataexploration-193817.user_data.cr_cohorts`
        ORDER BY cohort_name
    """
    df = bq_client.query(sql).to_dataframe()
    return df["cohort_name"].tolist()


@st.cache_data(ttl="1d", show_spinner="Loading cohort…")
def load_cohort_users(cohort_name: str) -> pd.DataFrame:
    _, bq_client = get_gcp_credentials()
    # LEFT JOIN from the cohort table: every distributed learner is "reached"
    # (LR) by virtue of cohort membership — standalone builds ship with Feed the
    # Monster pre-loaded and emit no `app_launch` event, so there is no launch
    # signal to join on. Learners who never produced an FTM event have no
    # `cr_user_progress` row; we keep them (flags coalesced to 0) and let
    # `lr_flag` carry the "FTM Interacted" (FTMI) step instead. Numeric progress
    # fields stay NULL for non-players so averages skip them rather than count
    # them as zero.
    sql = """
        SELECT
          c.cr_user_id,
          p.app_language,
          p.country,
          p.max_user_level,
          p.last_event_date,
          COALESCE(p.lr_flag, 0) AS lr_flag,
          COALESCE(p.pc_flag, 0) AS pc_flag,
          COALESCE(p.la_flag, 0) AS la_flag,
          COALESCE(p.ra_flag, 0) AS ra_flag,
          COALESCE(p.gc_flag, 0) AS gc_flag,
          p.gpc,
          p.total_time_minutes,
          p.active_span,
          p.days_to_ra,
          p.furthest_event
        FROM `dataexploration-193817.user_data.cr_cohorts` c
        LEFT JOIN `dataexploration-193817.user_data.cr_user_progress` p
          ON c.cr_user_id = p.cr_user_id
        WHERE c.cohort_name = @cohort_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("cohort_name", "STRING", cohort_name),
        ]
    )
    df = bq_client.query(sql, job_config=job_config).to_dataframe()
    return _pick_furthest_progress_row(df)
