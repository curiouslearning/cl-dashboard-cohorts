# CLAUDE.md — Cohort Tracker

## Project Overview

**Cohort Tracker** is a standalone Streamlit dashboard built for **coaches** who distribute
the Curious Reader app and want to monitor their learners' progress. It is intentionally
simple: one page, one cohort at a time, no filters.

A coach selects their cohort from a sidebar dropdown and sees:
1. A **cohort-level funnel summary** (how many learners reached each milestone)
2. A **learner roster table** showing each user's farthest level reached and last
   active date

This is a separate deployment from the internal CL Dashboard. It shares the same BigQuery
tables but has its own codebase, styling, and deployment pipeline.

**Deployed target:** `https://dashboard-cohorts.curiouslearning.org` (TBD)

---

## Audience

Coaches and program managers who:
- Distribute Curious Reader to a defined group of learners
- Want a quick read on how their cohort is progressing through FTM levels
- Are not data analysts — the UI must be self-explanatory

---

## Design Language: "Deep Current"

A blend of the Nairobi Moms slate-teal and the internal dashboard's color palette.
Navy primary, bright teal accent, warm amber highlight.

```python
# colors.py
NAVY        = "#1E3A5F"   # primary text / headers
TEAL        = "#0E8A8A"   # primary accent / active states
TEAL_LIGHT  = "#B8E0E0"   # backgrounds, dividers
AMBER       = "#E8963A"   # highlights, KPI callouts
WARM_WHITE  = "#F4F7FA"   # page background
CARD_BG     = "#EAF1F5"   # card / tile background
```

### `.streamlit/config.toml`
```toml
[theme]
primaryColor            = "#0E8A8A"
backgroundColor         = "#F4F7FA"
secondaryBackgroundColor = "#EAF1F5"
textColor               = "#1E3A5F"
font                    = "sans serif"
```

### Funnel step tile colors (LR → GC, lightest → darkest)
```python
FUNNEL_STEP_COLORS = [
    "#C5DFF0",
    "#9ECFE0",
    "#77BFD0",
    "#50AFBF",
    "#0E8A8A",
]
```

---

## Stack

| Layer | Library / Service |
|---|---|
| Framework | Streamlit 1.48+ with `st-pages` navigation (`main.py` shell + `app_pages/` page) |
| Data | Google BigQuery — direct query |
| Secrets | GCP Secret Manager |
| Charts | Plotly Graph Objects |
| Auth | GCP Service Account via `google-auth` |
| Containerization | Docker |

---

## Project Structure

```
main.py              # st-pages navigation shell + footer (set_page_config lives here)
settings.py          # get_gcp_credentials() → (creds, bq_client), get_logger(), initialize()
data.py              # All BigQuery queries, all @st.cache_data(ttl="1d")
metrics.py           # compute_funnel(), compute_kpis()
ui.py                # inject_css(), tile/chart HTML renderers
colors.py            # NAVY, TEAL, AMBER, FUNNEL_STEP_COLORS
app_pages/
    cohorts.py       # The actual cohort dashboard page
.streamlit/
    config.toml      # Deep Current theme
    pages.toml       # st-pages navigation config
entrypoint.sh        # Cloud Run entrypoint — `streamlit run main.py`
Dockerfile
requirements.txt
```

### Navigation pattern

`main.py` mirrors the other CL dashboards (Nairobi Moms, Firestore):

```python
import streamlit as st
from st_pages import add_page_title, get_nav_from_toml

st.set_page_config(layout="wide")
nav = get_nav_from_toml(".streamlit/pages.toml")
pg = st.navigation(nav)
add_page_title(pg)
pg.run()
# + Python/Streamlit version footer
```

Page files (e.g. `app_pages/cohorts.py`) MUST NOT call `st.set_page_config` —
that's owned by `main.py`. They call `initialize()` and `inject_css()` at the top.

---

## GCP Project

- **Project ID**: `dataexploration-193817`
- **Dataset**: `user_data`
- **Secret**: `projects/405806232197/secrets/service_account_json/versions/latest`

---

## Data Loading (`data.py`)

All functions decorated `@st.cache_data(ttl="1d")` to match the Firestore dashboard pattern.

### `load_all_cohorts() → list[str]`
```sql
SELECT DISTINCT cohort_name
FROM `dataexploration-193817.user_data.cr_cohorts`
ORDER BY cohort_name
```

### `load_cohort_users(cohort_name: str) → pd.DataFrame`
```sql
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
```

Parameterized with `bigquery.ScalarQueryParameter("cohort_name", "STRING", cohort_name)`.

Each loader unpacks the BQ client from `get_gcp_credentials()`:

```python
_, bq_client = get_gcp_credentials()
df = bq_client.query(sql, job_config=job_config).to_dataframe()
```

---

## Funnel Definition (`metrics.py`)

```python
FUNNEL_STEPS = [
    {"abbrev": "LR", "label": "Learner Reached",  "col": "lr_flag"},
    {"abbrev": "PC", "label": "Puzzle Completed", "col": "pc_flag"},
    {"abbrev": "LA", "label": "Learner Acquired", "col": "la_flag"},
    {"abbrev": "RA", "label": "Reader Acquired",  "col": "ra_flag"},
    {"abbrev": "GC", "label": "Game Completed",   "col": "gc_flag"},
]
```

### `compute_funnel(df) → list[dict]`
For each step, adds:
- `count` — number of users where flag == 1
- `pct_of_total` — count / total_users

### `compute_kpis(df) → dict`
Returns:
```python
{
    "total_users":            int,
    "pct_la":                 float,   # % reached level 1
    "pct_ra":                 float,   # % reached level 25
    "avg_max_level":          float,
    "avg_total_time_minutes": float,
}
```

---

## Page Layout (`main.py`)

### Sidebar
```
[Curious Learning logo or wordmark]
─────────────────────────────
Select Cohort   [dropdown]
─────────────────────────────
{N} learners
Data refreshes daily.
─────────────────────────────
▶ About this dashboard   [expander]
  Explains funnel steps and level milestones
```

### Main area

```
[Cohort name heading]  [{N} learners badge]

──── Cohort Overview ────────────────────────

[KPI tiles row]
  Total Learners | % Learner Acquired | % Reader Acquired | Avg Level

[Funnel tiles row: LR  PC  LA  RA  GC]

[Funnel drop-off area chart]

──── Learner Roster ─────────────────────────

[Sortable st.dataframe table]
  Columns: Learner | Level Reached | Last Active | Days Playing | Status
  Default sort: Level Reached descending

[st.caption: "Data reflects learner activity as of today's last refresh."]
```

### Learner Roster table columns

| Display name | Source column | Format |
|---|---|---|
| Learner | `cr_user_id` (full ID) | string |
| Level Reached | `max_user_level` | integer |
| Last Active | `last_event_date` | `MMM D, YYYY` |
| Active Span | `active_span` (days between first and last event) | `{n}d` |
| Status | derived (see below) | string |

> Note: `cr_user_progress` is granular by `(cr_user_id, app_language, country)`,
> so the same learner can appear on multiple rows (one per language/country).
> The current roster keeps each row separately — no dedupe.

> **Active Span ≠ days played.** It's the calendar span from a learner's first
> recorded event to their last. A learner who plays heavily on a single day has
> `active_span = 0`. Don't relabel this column "Days Playing" — that's how we
> got into trouble before.

> **Offline-play data loss.** Curious Reader can be played offline; events
> generated while disconnected are not recovered when the device reconnects.
> All cohort metrics (funnel flags, span, last-event date) are best-effort and
> may understate true activity. Surface this caveat anywhere a coach might
> over-interpret a low number.

**Status derivation:**
```python
STALE_DAYS = 7

def learner_status(row, today):
    last = row["last_event_date"]
    if pd.notna(last):
        days_since = (today - pd.Timestamp(last).date()).days
        if days_since > STALE_DAYS:
            return "Stalled"
    if row["ra_flag"] == 1:  return "Reader ✓"
    if row["la_flag"] == 1:  return "Learner"
    if row["pc_flag"] == 1:  return "Exploring"
    return                          "Just started"
```

The 7-day staleness check overrides the milestone label — a learner who reached
level 1 a month ago and hasn't returned reads as **Stalled**, not **Learner**.

Rendered as a plain `st.dataframe` with `st.column_config` for display names and
formatting. No custom HTML needed for the table itself.

---

## UI Module (`ui.py`)

### `inject_css()`
Injects all custom styles. Call at the top of `main.py` after `st.set_page_config`.

Key CSS classes:
```
.ct-kpi-tile        — KPI summary card (amber highlight on value)
.ct-funnel-tile     — per-step funnel box (gradient teal)
.ct-section-header  — teal-underline section label
.ct-cohort-badge    — navy pill with learner count
```

### `kpi_tile_html(label, value, sub=None, bg=CARD_BG) → str`
Single KPI card. `value` passed in pre-formatted.

### `funnel_tile_html(abbrev, label, count, pct, bg) → str`
One funnel step. Same signature as `nairobimom_ui.funnel_tile_html`.

### `funnel_dropoff_chart(funnel_steps) → go.Figure`
Area + line chart showing % of total at each funnel step.
Deep Current colors. Same shape as Nairobi Moms implementation.

---

## Key Patterns

### Loading
```python
# app_pages/cohorts.py
cohort_name = st.sidebar.selectbox("Select Cohort", load_all_cohorts())
df = load_cohort_users(cohort_name)
if df.empty:
    st.warning("No learners found for this cohort.")
    st.stop()
```

### Formatting helpers
```python
def fmt_pct(v: float) -> str:  return f"{v:.1%}"
def fmt_num(v: float) -> str:  return f"{v:,.0f}"
def fmt_level(v) -> str:       return str(int(v)) if pd.notna(v) else "—"
def fmt_days(v) -> str:        return f"{int(v)}d" if pd.notna(v) and v >= 0 else "—"
```

### `active_span` safety
Always clip before display:
```python
df["active_span"] = df["active_span"].clip(lower=0)
```

### `days_to_ra` safety
Only meaningful for RA users:
```python
avg_days_to_ra = df.loc[df["ra_flag"] == 1, "days_to_ra"].mean()
```

---

## Deployment

- **Cloud Run**, region `us-central1`
- **Cloud Build** trigger on push to `main` branch — no `cloudbuild.yaml`,
  the trigger is configured to build the Dockerfile directly
- Public GitHub repo — Dockerfile mirrors the `cl-dashboard-internal`
  pattern (dual-mode: `remote` clones from GitHub, `local` uses build context)
- Custom domain via AWS Route 53 CNAME → `ghs.googlehosted.com`

```dockerfile
# Set the build mode (default to remote)
ARG BUILD_MODE=remote
FROM python:3.12.3-bookworm

ARG BUILD_MODE
ENV BUILD_MODE=${BUILD_MODE}

# Install required tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3-pip \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Set the workdir to a neutral temp folder first
WORKDIR /tmp/build-context

# Clone OR copy conditionally
RUN if [ "$BUILD_MODE" = "remote" ]; then \
      git clone https://github.com/curiouslearning/cl-dashboard-cohorts.git /cl-dashboard-cohorts ; \
    fi

# Copy only if local
COPY . /tmp/local-copy
RUN if [ "$BUILD_MODE" = "local" ]; then \
      cp -r /tmp/local-copy /cl-dashboard-cohorts ; \
    fi

WORKDIR /cl-dashboard-cohorts

RUN pip3 install --no-cache-dir -r requirements.txt

ENV PORT=8501

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

Local dev build: `docker build --build-arg BUILD_MODE=local -t cohorts .`

```bash
# entrypoint.sh
#!/bin/bash
set -e
exec python -u -m streamlit run main.py \
  --server.port=${PORT:-8501} --server.address=0.0.0.0
```

---

## What This App Does NOT Do

- No date range filters
- No language or country filters
- No multi-cohort comparison
- No FTM event timeline or per-user drill-down
- No Unity app data
- No book detail analytics
- No GCS parquet cache

Keep it simple. If a coach needs more, they use the internal CL Dashboard.

---

## Relationship to Internal Dashboard

Shares the same BigQuery tables (`cr_user_progress`, `cr_cohorts`).
**Do not import** from the internal dashboard's modules.
This codebase is fully self-contained.