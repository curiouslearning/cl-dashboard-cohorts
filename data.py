"""BigQuery loaders. All cached for one day."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from google.cloud import bigquery

from settings import get_gcp_credentials


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
    sql = """
        SELECT
          p.cr_user_id,
          p.app_language,
          p.country,
          p.max_user_level,
          p.last_event_date,
          p.lr_flag,
          p.pc_flag,
          p.la_flag,
          p.ra_flag,
          p.gc_flag,
          p.gpc,
          p.total_time_minutes,
          p.active_span,
          p.days_to_ra
        FROM `dataexploration-193817.user_data.cr_user_progress` p
        JOIN `dataexploration-193817.user_data.cr_cohorts` c
          ON p.cr_user_id = c.cr_user_id
        WHERE c.cohort_name = @cohort_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("cohort_name", "STRING", cohort_name),
        ]
    )
    return bq_client.query(sql, job_config=job_config).to_dataframe()
