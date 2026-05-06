"""CSS injection and HTML/Plotly renderers for the Deep Current UI."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from colors import (
    AMBER,
    CARD_BG,
    NAVY,
    TEAL,
    TEAL_LIGHT,
    WARM_WHITE,
)


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
          .block-container {{
            padding-top: 2rem;
            max-width: 1200px;
          }}

          .ct-section-header {{
            color: {NAVY};
            font-size: 1.05rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            border-bottom: 2px solid {TEAL};
            padding-bottom: 0.35rem;
            margin: 1.75rem 0 1rem 0;
          }}

          .ct-cohort-badge {{
            display: inline-block;
            background: {NAVY};
            color: {WARM_WHITE};
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-left: 0.75rem;
            vertical-align: middle;
          }}

          .ct-kpi-tile {{
            background: {CARD_BG};
            border-radius: 10px;
            padding: 1rem 1.1rem;
            border-left: 4px solid {AMBER};
            height: 100%;
          }}
          .ct-kpi-tile .label {{
            color: {NAVY};
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.75;
          }}
          .ct-kpi-tile .value {{
            color: {AMBER};
            font-size: 1.85rem;
            font-weight: 700;
            line-height: 1.1;
            margin-top: 0.25rem;
          }}
          .ct-kpi-tile .sub {{
            color: {NAVY};
            font-size: 0.8rem;
            opacity: 0.65;
            margin-top: 0.2rem;
          }}

          .ct-funnel-tile {{
            border-radius: 10px;
            padding: 0.85rem 0.6rem;
            text-align: center;
            color: {NAVY};
            min-height: 110px;
            display: flex;
            flex-direction: column;
            justify-content: center;
          }}
          .ct-funnel-tile .abbrev {{
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: 0.05em;
          }}
          .ct-funnel-tile .label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.8;
            margin-top: 0.1rem;
          }}
          .ct-funnel-tile .count {{
            font-size: 1.4rem;
            font-weight: 700;
            margin-top: 0.45rem;
          }}
          .ct-funnel-tile .pct {{
            font-size: 0.8rem;
            opacity: 0.75;
          }}

          [data-testid="stSidebar"] {{
            background: {WARM_WHITE};
          }}

          [data-testid="stSidebar"] .st-key-cohort_picker {{
            background: {TEAL_LIGHT};
            border: 1px solid {TEAL};
            border-radius: 10px;
            padding: 0.85rem 0.9rem 0.5rem 0.9rem;
            margin-bottom: 0.5rem;
          }}
          [data-testid="stSidebar"] .st-key-cohort_picker label {{
            color: {NAVY} !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.78rem !important;
          }}
          [data-testid="stSidebar"] .st-key-cohort_picker [data-baseweb="select"] > div {{
            background: white;
            border-color: {TEAL};
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_tile_html(label: str, value: str, sub: str | None = None, bg: str = CARD_BG) -> str:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return (
        f'<div class="ct-kpi-tile" style="background:{bg};">'
        f'  <div class="label">{label}</div>'
        f'  <div class="value">{value}</div>'
        f'  {sub_html}'
        f'</div>'
    )


def funnel_tile_html(abbrev: str, label: str, count: int, pct: float, bg: str) -> str:
    return (
        f'<div class="ct-funnel-tile" style="background:{bg};">'
        f'  <div class="abbrev">{abbrev}</div>'
        f'  <div class="label">{label}</div>'
        f'  <div class="count">{count:,}</div>'
        f'  <div class="pct">{pct:.1%}</div>'
        f'</div>'
    )


def funnel_dropoff_chart(funnel_steps: list[dict]) -> go.Figure:
    labels = [s["abbrev"] for s in funnel_steps]
    pcts = [s["pct_of_total"] * 100 for s in funnel_steps]
    counts = [s["count"] for s in funnel_steps]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels,
        y=pcts,
        mode="lines",
        line=dict(color=TEAL, width=0),
        fill="tozeroy",
        fillcolor=TEAL_LIGHT,
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=labels,
        y=pcts,
        mode="lines+markers",
        line=dict(color=TEAL, width=3),
        marker=dict(size=10, color=TEAL, line=dict(color="white", width=2)),
        customdata=counts,
        hovertemplate="<b>%{x}</b><br>%{y:.1f}% (%{customdata:,} learners)<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=20, b=20),
        plot_bgcolor=WARM_WHITE,
        paper_bgcolor=WARM_WHITE,
        font=dict(color=NAVY),
        yaxis=dict(
            title="% of cohort",
            ticksuffix="%",
            range=[0, 105],
            gridcolor="#D6E1EA",
        ),
        xaxis=dict(showgrid=False),
    )
    return fig
