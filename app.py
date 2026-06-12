"""Streamlit frontend for the project prioritization tool.

Run with:    streamlit run app.py

Three tabs:
  1. Ranking            — prioritized table with portfolio KPIs
  2. Project Details    — pick projects, plot KPIs over time
  3. Add Project        — high-level form, appends to the CSVs and re-ranks

The sidebar exposes:
  - weights for the composite score
  - sample-data regeneration
"""

from __future__ import annotations

import os
import json
import re
import datetime
from typing import Callable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from data_generator import (
    ARCHETYPES,
    generate_projects,
    shape_accelerating,
    shape_linear_ramp,
    shape_peak_decay,
    shape_plateau,
    shape_s_curve,
    shape_slow_steady,
)
from models import (
    PROJECTS_META_CSV,
    PROJECTS_MONTHLY_CSV,
    Project,
    append_project,
    apply_cost_buffer,
    build_monthly_long_df,
    load_projects,
    save_projects,
)
from prioritization import (
    ranked_to_dataframe, score_projects, schedule_portfolio, build_global_timeline,
    simulate_portfolio_profit, simulate_rank_stability,
    simulate_reinvestment,
)


CURRENCY = "CHF"

# Logo base64 strings (truncated for brevity - keep your original values)
LIECHTENSTEIN_LOGO_BASE64 = "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"
HILTI_LOGO_BASE64 = "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"

import plotly.io as pio
plotly_template = pio.templates['plotly_dark']
plotly_template.layout.paper_bgcolor = 'rgba(0,0,0,0)'
plotly_template.layout.plot_bgcolor = 'rgba(0,0,0,0)'
plotly_template.layout.font.color = '#ffffff'
plotly_template.layout.font.family = 'Montserrat'
pio.templates.default = 'plotly_dark'

CURRENCY = "CHF"

VALUE_SHAPES: dict[str, Callable] = {
    "Linear ramp":          shape_linear_ramp,
    "Accelerating":         shape_accelerating,
    "Plateau":              shape_plateau,
    "Sharp peak then decay": shape_peak_decay,
    "S-curve adoption":     shape_s_curve,
    "Slow steady":          shape_slow_steady,
}


# --------------------------------------------------------------------------
# Data loading: cached, but the cache key is the mtime of the CSVs so any
# write (regenerate, append project) invalidates it automatically.
# --------------------------------------------------------------------------

def _data_signature() -> tuple[float, float]:
    """File-mtime tuple used as the Streamlit cache key for the loaded portfolio."""
    return (
        os.path.getmtime(PROJECTS_META_CSV) if os.path.exists(PROJECTS_META_CSV) else 0.0,
        os.path.getmtime(PROJECTS_MONTHLY_CSV) if os.path.exists(PROJECTS_MONTHLY_CSV) else 0.0,
    )


@st.cache_data(show_spinner=False)
def _load_projects_cached(signature: tuple[float, float]) -> list[Project]:
    """Cached read of the CSVs. Cache invalidates whenever the mtime changes."""
    return load_projects()


def get_projects() -> list[Project]:
    """Return the current portfolio, bootstrapping a sample dataset on first run."""
    if not os.path.exists(PROJECTS_META_CSV):
        # First run: bootstrap with the standard 100-project portfolio
        save_projects(generate_projects(n_projects=100, seed=42))
    return _load_projects_cached(_data_signature())


# --------------------------------------------------------------------------
# Interdepartmental Hub Helper Functions (Phase 3)
# --------------------------------------------------------------------------

DEPT_REVIEWS_FILE = "data/department_reviews.json"

def load_dept_reviews():
    if not os.path.exists(DEPT_REVIEWS_FILE):
        return {}
    try:
        with open(DEPT_REVIEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_dept_reviews(reviews):
    os.makedirs("data", exist_ok=True)
    try:
        with open(DEPT_REVIEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error saving reviews: {e}")

def init_dept_reviews(projects):
    reviews = load_dept_reviews()
    changed = False
    for p in projects:
        pid = p.project_id
        if pid not in reviews:
            # Seed realistic default ratings
            # Simple hash-based seed for reproducibility
            val = hash(pid) % 4
            reviews[pid] = {
                "scores": {
                    "Finance": 6 + (val % 3),
                    "IT/R&D": 7 + ((val + 1) % 3),
                    "Sales/Marketing": 6 + ((val + 2) % 4),
                    "Operations": 5 + ((val + 3) % 4)
                },
                "comments": [
                    {
                        "dept": "Operations",
                        "user": "SysAdmin",
                        "score": 5 + ((val + 3) % 4),
                        "text": f"Initial scheduling analysis shows moderate resource overlap for {p.name}.",
                        "time": "2026-05-17 14:00"
                    },
                    {
                        "dept": "Finance",
                        "user": "Finance Director",
                        "score": 6 + (val % 3),
                        "text": f"Aligned with Hilti standard corporate margin goals.",
                        "time": "2026-05-17 14:30"
                    }
                ]
            }
            changed = True
    if changed:
        save_dept_reviews(reviews)
    return reviews


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------

def fmt_money(x: float) -> str:
    """Format an EUR amount with k/M/B suffixes for compact display."""
    if x is None or pd.isna(x):
        return "—"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e9:
        return f"{sign}{x/1e9:.2f} B {CURRENCY}"
    if x >= 1e6:
        return f"{sign}{x/1e6:.2f} M {CURRENCY}"
    if x >= 1e3:
        return f"{sign}{x/1e3:.0f} k {CURRENCY}"
    return f"{sign}{x:,.0f} {CURRENCY}"


# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Hilti Project Prioritization",
    page_icon="🔧",
    layout="wide",
)

# --------------------------------------------------------------------------
# Logos and styling
# --------------------------------------------------------------------------

# Global styling: reclaim top whitespace + render the sidebar navigation as
# compact "tab/card" buttons (mirrors the logo panel, but smaller).
st.markdown(
    """
    <style>
    /* Reclaim the large default whitespace at the top of the main area */
    [data-testid="stMainBlockContainer"], .block-container { padding-top: 2.5rem !important; }

    /* Sidebar navigation as compact cards/tabs */
    section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 6px; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        display: flex; align-items: center;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 9px 14px; margin: 0;
        cursor: pointer;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background: rgba(210,5,30,0.10);
        border-color: rgba(210,5,30,0.35);
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: rgba(210,5,30,0.18);
        border-color: rgba(210,5,30,0.55);
        box-shadow: inset 3px 0 0 #D2051E;
        font-weight: 700;
    }
    /* Hide the default radio dot for a clean tab look */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Sidebar: weights + portfolio actions
# --------------------------------------------------------------------------

with st.sidebar:
    # 1. Co-branding HTML Logos
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 25px; padding: 12px 14px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; backdrop-filter: blur(8px); box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <img src="data:image/png;base64,{LIECHTENSTEIN_LOGO_BASE64}" style="height: 24px; width: auto; max-width: 52%; object-fit: contain; opacity: 0.95;">
            <img src="data:image/png;base64,{HILTI_LOGO_BASE64}" style="height: 24px; width: auto; max-width: 44%; object-fit: contain; opacity: 0.95;">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 2. Page Navigation Section Title
    st.markdown("<h3 style='color: rgb(203,24,29); margin-top: 5px; margin-bottom: 12px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; opacity: 0.75;'>Navigation</h3>", unsafe_allow_html=True)
    
    # Navigation pages (clean names, no emojis)
    pages = [
        "Portfolio Overview",
        "Project Details",
        "Robustness Simulation",
        "Execution Strategy",
        "Department Alignment",
        "Add Project",
        "Copilot",
        "User Guide",
    ]

    # Initialise / sanitise the selected page BEFORE the widget is created.
    # Binding the radio directly to session_state via key="current_page" fixes
    # the previous "needs two clicks" bug, which was caused by manually passing
    # index= and writing st.session_state *after* the widget on every rerun.
    if st.session_state.get("current_page") not in pages:
        st.session_state["current_page"] = pages[0]

    st.radio(
        "Navigation",
        pages,
        key="current_page",
        label_visibility="collapsed",
    )

    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
    
    # 3. Compact Collapsible Panel for Configuration Widgets
    with st.expander("⚙️ Controls & Parameters", expanded=False):
        st.subheader("Capital Velocity — Reinvestment Rate")
        st.caption("Capital Velocity ranks by **discounted net profit per CHF invested** — money back sooner can be reinvested into the next projects sooner. This rate sets how strongly fast payback is rewarded.")
        reinvest_pct = st.slider("Reinvestment rate (% per year)", 0, 60, 30, 5,
                                 help="0 % = rank by plain return-on-cost (ROI). Higher = reward projects that return capital faster, so it compounds into more projects. Default 30 %.")
        reinvest_rate = reinvest_pct / 100.0
        st.caption("Low = patient (favours total size). High = aggressive (favours fastest payback / capital recycling).")
        weight_value, weight_speed = 0.5, 0.5  # retained for legacy callers; Composite now uses reinvest_rate

        st.divider()
        st.subheader("Prioritization Algorithm")
        prio_method = st.selectbox("Select Method", ["Capital Velocity", "Value Creation Rating", "ROI"], help="Capital Velocity: discounted Net Profit / Cost (rewards fast payback, set via the reinvestment rate). Value Creation Rating: Net Profit / Duration. ROI: Net Profit / Cost.")

        st.divider()
        st.subheader("Estimation Cost Buffer")
        st.caption("Contingency added on top of every project's cost to reflect estimation uncertainty. Flows into ranking, scheduling and all analyses.")
        cost_buffer = st.slider("Cost buffer (% of project cost)", 0, 10, 0, 1) / 100.0

        st.divider()
        st.subheader("Budget")
        st.caption("Spending limits the scheduler uses to decide which projects get funded.")
        enable_budget = st.checkbox("Enable Total Budget Limit", value=True)
        total_budget = st.number_input("Total Budget (CHF)", value=50000000.0, step=1000000.0, format="%.0f") if enable_budget else None

        enable_monthly = st.checkbox("Enable Monthly Spend Limit")
        max_monthly_spend = st.number_input("Max Monthly Spend (CHF)", value=2000000.0, step=500000.0, format="%.0f") if enable_monthly else None

        st.divider()
        st.subheader("Execution Plan")
        st.caption("How the funded projects are run over time.")
        execution_mode = st.radio("Execution Mode", ["Sequential", "Parallel"],
                                  help="Sequential = one project after another. Parallel = projects overlap in time.")

        enable_concurrency = st.checkbox("Limit parallel projects",
                                         help="Cap how many projects run at the same time (Parallel mode only).")
        max_concurrency = st.number_input("Max parallel projects", value=10, min_value=1, step=1) if enable_concurrency else None

        st.divider()
        st.subheader("Portfolio Generator")
        st.caption("Regenerate the sample portfolio from scratch (overwrites CSVs).")
        seed = st.number_input("Random seed", value=42, step=1)
        n_projects = st.number_input("Number of projects", value=100, min_value=10, max_value=500, step=10)
        custom_duration = st.checkbox(
            "Custom project duration",
            value=False,
            help="Force every generated project's duration into a chosen range — e.g. 1-4 months "
                 "for a short-project portfolio. Business value scales with the duration so monthly "
                 "earning rates stay realistic. Off = standard archetype durations; existing seeds "
                 "keep producing exactly the same portfolios.",
        )
        gen_duration_range = None
        if custom_duration:
            gen_duration_range = st.slider("Project duration range (months)", 1, 48, (1, 4),
                                           help="Each project's duration is drawn uniformly from this range.")
        if st.button("Regenerate sample data", type="secondary"):
            save_projects(generate_projects(n_projects=int(n_projects), seed=int(seed),
                                            duration_range=gen_duration_range))
            st.cache_data.clear()
            dur_note = f" (durations {gen_duration_range[0]}-{gen_duration_range[1]} mo)" if gen_duration_range else ""
            st.success(f"Generated {int(n_projects)} projects{dur_note}.")
            st.rerun()

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

# Get projects and scores
projects = get_projects()
# Apply the estimation cost buffer (Point 4) so every downstream calculation —
# scoring, scheduling, risk, robustness — sees the contingency-loaded costs.
projects = apply_cost_buffer(projects, cost_buffer)
ranked = score_projects(projects, weight_value=weight_value, weight_speed=weight_speed, method=prio_method, reinvest_rate=reinvest_rate)
ranked_df = ranked_to_dataframe(ranked)
monthly_df = build_monthly_long_df(projects)

# Discounted cumulative net profit per project — the same time-discounting the
# Capital Velocity score is built on (early profit is worth more). Driven by the
# sidebar reinvestment rate so the Project Details chart stays consistent with it.
_r_m = (1.0 + reinvest_rate) ** (1.0 / 12.0) - 1.0
monthly_df["_disc_np"] = monthly_df["monthly_net_profit"] / (1.0 + _r_m) ** monthly_df["month"]
monthly_df["discounted_cumulative_net_profit"] = monthly_df.groupby("project_id")["_disc_np"].cumsum()

# Schedule Portfolio
scheduled = schedule_portfolio(
    ranked, 
    mode=execution_mode, 
    budget=total_budget, 
    max_concurrency=max_concurrency, 
    parallel_spending=max_monthly_spend
)
selected_projects = [s.scored.project for s in scheduled]
global_timeline = build_global_timeline(scheduled)

# Add Selected column to ranked_df
selected_ids = {p.project_id for p in selected_projects}
ranked_df["Selected"] = ranked_df["project_id"].apply(lambda pid: "✅" if pid in selected_ids else "❌")

# --------------------------------------------------------------------------
# Header: app brand (top) + current page name
# --------------------------------------------------------------------------

current_page = st.session_state["current_page"]

st.markdown(
    f"""
    <div style="margin-bottom: 0.4rem;">
        <div style="font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase;
                    color: rgba(210,5,30,0.85); font-weight: 700;">Project Prioritization Prototype</div>
        <h1 style="margin: 0; padding: 0; font-size: 2.1rem; font-weight: 800;
                   line-height: 1.15;">{current_page}</h1>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Rank a portfolio by total net profit and break-even speed. "
    "Net Profit = Business Value − (Direct Cost + Effort). "
    f"All money values in {CURRENCY}."
)

# --------------------------------------------------------------------------
# Portfolio KPI bar (global context)
# --------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
c1.metric("Selected Projects", f"{len(selected_projects)} / {len(projects)}")
c2.metric("Total business value", fmt_money(sum(p.total_business_value for p in selected_projects)))
c3.metric("Total cost", fmt_money(sum(p.total_cost for p in selected_projects)))
if len(global_timeline) > 0:
    total_np = float(global_timeline["Cumulative Net Profit"].iloc[-1])
else:
    total_np = 0.0
c4.metric("Cumulative Net Profit", fmt_money(total_np))

st.divider()


# Define the helper functions for Add Project tabs
def _finalize_new_project(*, name: str, archetype: str, duration: int,
                          fte_cost_monthly: float,
                          direct_cost: np.ndarray, fte_count: np.ndarray,
                          business_value: np.ndarray,
                          existing: list[Project]) -> None:
    existing_ids = {p.project_id for p in existing}
    n = 1
    while f"P-{n:04d}" in existing_ids:
        n += 1
    new_id = f"P-{n:04d}"
    new_project = Project(
        project_id=new_id,
        name=f"{name.strip()} ({new_id})",
        archetype=archetype,
        duration_months=int(duration),
        fte_cost_monthly=float(fte_cost_monthly),
        direct_cost=direct_cost,
        fte_count=fte_count,
        business_value=business_value,
    )
    append_project(new_project)
    st.cache_data.clear()
    st.success(f"Added '{name.strip()}' as {new_id}. Total NP: {fmt_money(new_project.total_net_profit)} • Break-even: {new_project.break_even_month or 'never'} mo.")
    st.info("Switch to Portfolio Overview — the portfolio has been re-prioritised.")

def _render_detailed_add(projects: list[Project]) -> None:
    st.markdown("**Detailed mode** — enter every KPI per month. The system computes monthly cost, monthly net profit, and the totals automatically.")
    name_d = st.text_input("Project name", key="detailed_name")
    c1, c2, c3 = st.columns(3)
    with c1:
        archetype_d = st.selectbox("Archetype (for tagging only)", options=[a.name for a in ARCHETYPES] + ["Custom"], key="detailed_archetype")
    with c2:
        duration_d = int(st.number_input("Duration (months)", min_value=1, max_value=72, value=12, step=1, key="detailed_duration"))
    with c3:
        fte_cost_monthly_d = float(st.number_input(f"FTE cost / month ({CURRENCY})", min_value=0.0, value=13000.0, step=500.0, 
                                                   key="detailed_fte_cost_monthly", help="Loaded cost per FTE per month (same across the project)."))
    table_key = "detailed_table"
    if (table_key not in st.session_state or len(st.session_state[table_key]) != duration_d):
        st.session_state[table_key] = pd.DataFrame({"month": np.arange(1, duration_d + 1), "business_value": [0.0] * duration_d,
                                                   "direct_cost": [0.0] * duration_d, "fte_count": [0.0] * duration_d})
    st.markdown("##### Monthly inputs")
    edited = st.data_editor(st.session_state[table_key], column_config={
        "month": st.column_config.NumberColumn("Month", format="%d", width="small"),
        "business_value": st.column_config.NumberColumn(f"Business Value ({CURRENCY})", min_value=0.0, step=10000.0, format="%.0f",
                                                        help="Revenue, savings, or reduced risk cost generated this month."),
        "direct_cost": st.column_config.NumberColumn(f"Direct Cost ({CURRENCY})", min_value=0.0, step=5000.0, format="%.0f",
                                                     help="Spend this month: consultants, licenses, infrastructure."),
        "fte_count": st.column_config.NumberColumn("FTE Count", min_value=0.0, step=0.5, format="%.1f",
                                                   help="Full-time-equivalent people on the project this month."),
    }, disabled=["month"], num_rows="fixed", hide_index=True, use_container_width=True, key="detailed_editor")
    st.session_state[table_key] = edited
    bv = edited["business_value"].to_numpy(dtype=float)
    dc = edited["direct_cost"].to_numpy(dtype=float)
    fte = edited["fte_count"].to_numpy(dtype=float)
    monthly_cost = dc + fte * fte_cost_monthly_d
    monthly_np = bv - monthly_cost
    cum = np.cumsum(monthly_np)
    pos = np.where(cum >= 0)[0]
    break_even = int(pos[0] + 1) if pos.size > 0 else None
    st.markdown("##### Live preview")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total business value", fmt_money(bv.sum()))
    m2.metric("Total cost", fmt_money(monthly_cost.sum()))
    m3.metric("Total net profit", fmt_money(monthly_np.sum()))
    m4.metric("Break-even month", str(break_even) if break_even else "never")
    preview_df = pd.DataFrame({"month": np.arange(1, duration_d + 1), "monthly_net_profit": monthly_np, "cumulative_net_profit": cum})
    fig = px.line(preview_df, x="month", y="cumulative_net_profit", markers=True,
                 labels={"month": "Month", "cumulative_net_profit": f"Cumulative NP ({CURRENCY})"})
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)
    fig.update_layout(height=300, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    if st.button("Add project", type="primary", key="detailed_submit"):
        if not name_d.strip():
            st.error("Please provide a project name.")
        elif bv.sum() == 0 and dc.sum() == 0 and fte.sum() == 0:
            st.error("All monthly inputs are zero — please fill in at least some values.")
        else:
            _finalize_new_project(name=name_d, archetype=archetype_d, duration=duration_d, fte_cost_monthly=fte_cost_monthly_d,
                                 direct_cost=dc, fte_count=fte, business_value=bv, existing=projects)
            del st.session_state[table_key]

def _render_highlevel_add(projects: list[Project]) -> None:
    st.markdown("**High-level mode** — enter totals and ranges. The system spreads them across the months using a value-curve shape.")
    archetype_names = [a.name for a in ARCHETYPES]
    archetype_h = st.selectbox("Archetype", options=archetype_names + ["Custom"], key="highlevel_archetype",
                              help="Drives the default value-curve shape and pre-fills sensible numbers.")
    archetype_obj = next((a for a in ARCHETYPES if a.name == archetype_h), None)
    if archetype_obj is not None:
        d_default = sum(archetype_obj.duration_range) // 2
        cost_share_default = sum(archetype_obj.cost_phase_share_range) / 2
        fte_cost_default = sum(archetype_obj.fte_cost_phase_range) // 2
        fte_gain_default = sum(archetype_obj.fte_gain_phase_range) // 2
        dc_cost_default = sum(archetype_obj.direct_cost_phase_range) / 2
        dc_gain_default = sum(archetype_obj.direct_gain_phase_range) / 2
        fte_monthly_default = sum(archetype_obj.fte_cost_monthly_range) / 2
        total_value_default = sum(archetype_obj.total_value_range) / 2
        archetype_shape_name = next((k for k, v in VALUE_SHAPES.items() if v is archetype_obj.value_shape), "Linear ramp")
    else:
        d_default, cost_share_default = 12, 0.5
        fte_cost_default, fte_gain_default = 4, 2
        dc_cost_default, dc_gain_default = 50000.0, 10000.0
        fte_monthly_default, total_value_default = 13000.0, 2000000.0
        archetype_shape_name = "Linear ramp"
    name_h = st.text_input("Project name", key="highlevel_name")
    c1, c2 = st.columns(2)
    with c1:
        duration_h = int(st.number_input("Duration (months)", min_value=1, max_value=72, value=int(d_default), step=1, key="highlevel_duration"))
        cost_share = st.slider("Share of duration in cost phase", 0.0, 1.0, float(cost_share_default), 0.05, key="highlevel_cost_share",
                              help="Fraction of months at the start with no business value yet.")
        total_value = float(st.number_input(f"Total business value over gain phase ({CURRENCY})", min_value=0.0, value=float(total_value_default), 
                                           step=100000.0, key="highlevel_total_value"))
    with c2:
        fte_cost_n = int(st.number_input("FTE count during cost phase", min_value=0, max_value=100, value=int(fte_cost_default), step=1, key="highlevel_fte_cost"))
        fte_gain_n = int(st.number_input("FTE count during gain phase", min_value=0, max_value=100, value=int(fte_gain_default), step=1, key="highlevel_fte_gain"))
        fte_cost_monthly_h = float(st.number_input(f"Avg FTE cost per month ({CURRENCY} / FTE / month)", min_value=0.0, value=float(fte_monthly_default), 
                                                   step=500.0, key="highlevel_fte_cost_monthly"))
        dc_cost_phase = float(st.number_input(f"Avg direct cost / month — cost phase ({CURRENCY})", min_value=0.0, value=float(dc_cost_default), 
                                              step=5000.0, key="highlevel_dc_cost"))
        dc_gain_phase = float(st.number_input(f"Avg direct cost / month — gain phase ({CURRENCY})", min_value=0.0, value=float(dc_gain_default), 
                                              step=1000.0, key="highlevel_dc_gain"))
    st.markdown("##### Value distribution over the gain phase")
    auto_estimate = st.toggle("Auto-estimate distribution from archetype", value=True, key="highlevel_auto_estimate",
                              help="ON: use the typical value-curve shape for the selected archetype. OFF: pick the shape yourself.")
    if auto_estimate:
        if archetype_obj is not None:
            shape_name_h = archetype_shape_name
            st.caption(f"Using **{shape_name_h}** — typical for *{archetype_h}*.")
        else:
            shape_name_h = "Linear ramp"
            st.caption("Custom archetype has no archetype-specific shape; falling back to **Linear ramp**.")
    else:
        shape_name_h = st.selectbox("Value-curve shape", options=list(VALUE_SHAPES.keys()), index=list(VALUE_SHAPES.keys()).index(archetype_shape_name), key="highlevel_shape")
    if st.button("Add project", type="primary", key="highlevel_submit"):
        if not name_h.strip():
            st.error("Please provide a project name.")
        else:
            n = duration_h
            cost_months = max(1, int(round(n * cost_share)))
            cost_months = min(cost_months, n - 1) if n > 1 else cost_months
            gain_months = n - cost_months
            direct = np.empty(n)
            direct[:cost_months] = dc_cost_phase
            if gain_months > 0:
                direct[cost_months:] = dc_gain_phase
            fte = np.empty(n)
            fte[:cost_months] = fte_cost_n
            if gain_months > 0:
                fte[cost_months:] = fte_gain_n
            value = np.zeros(n)
            if gain_months > 0:
                rng = np.random.default_rng()
                shape = VALUE_SHAPES[shape_name_h](gain_months, rng)
                value[cost_months:] = shape * total_value
            _finalize_new_project(name=name_h, archetype=archetype_h if archetype_obj else "Custom", duration=n,
                                 fte_cost_monthly=fte_cost_monthly_h, direct_cost=direct, fte_count=fte, business_value=value, existing=projects)

# --------------------------------------------------------------------------
# Page content based on selected page
# --------------------------------------------------------------------------

if current_page == 'Portfolio Overview':
    # --- The key chart: prioritization visualised as net-profit-over-time ---
    st.markdown("##### Ranking - Cumulative Net Profit over Time")
    max_top = min(50, len(ranked))
    default_top = min(10, max_top)
    top_n_chart = st.slider("Show top N projects by priority", 1, max(1, max_top), default_top, key="overview_topn")
    top = ranked[:top_n_chart]

    if len(top) > 1:
        intensities = list(np.linspace(0.92, 0.40, len(top)))   # rank 1 = deepest red
        colors = px.colors.sample_colorscale("YlOrRd", intensities)
    else:
        colors = ["#D2051E"]

    fig_prio = go.Figure()
    for idx, sp in enumerate(top):
        p = sp.project
        months = list(range(1, p.duration_months + 1))
        cum = p.cumulative_net_profit
        funded = p.project_id in selected_ids
        color = colors[idx]
        fig_prio.add_trace(go.Scatter(
            x=months, y=cum, mode="lines",
            line=dict(color=color, width=2.5, dash="solid" if funded else "dash"),
            name=f"#{sp.rank} {p.name}",
            hovertemplate=(f"<b>#{sp.rank} {p.name}</b><br>"
                           f"{'Funded' if funded else 'Not funded'} • break-even mo "
                           f"{sp.break_even_month or '—'}<br>"
                           f"Month %{{x}}<br>Cumulative NP: %{{y:,.0f}} {CURRENCY}<extra></extra>"),
            showlegend=False,
        ))
        # circled rank badge at the end of each line
        fig_prio.add_trace(go.Scatter(
            x=[months[-1]], y=[cum[-1]], mode="markers+text",
            marker=dict(size=24, color="white", line=dict(color=color, width=2.5)),
            text=[str(sp.rank)], textposition="middle center",
            textfont=dict(color=color, size=11, family="Arial Black"),
            showlegend=False, hoverinfo="skip",
        ))
    fig_prio.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_prio.update_layout(
        title=f"Cumulative Net Profit of the Top {len(top)} Prioritized Projects ({prio_method})",
        xaxis_title="Month", yaxis_title=f"Cumulative Net Profit ({CURRENCY})",
        height=500, margin=dict(t=50, b=20, l=20, r=30),
    )
    st.plotly_chart(fig_prio, use_container_width=True)
    st.caption("Each line tracks a project's net profit accumulating over its lifetime; the **circled number is its priority rank**. **Solid** = funded under the current budget, **dashed** = not funded. Higher-priority projects generally climb higher and/or reach profit (cross zero) sooner.")

    st.divider()
    st.subheader("Prioritized projects")
    c_filt1, c_filt2, c_filt3 = st.columns(3)
    with c_filt1:
        archetypes_selected = st.multiselect(
            "Filter by archetype",
            options=sorted(ranked_df["archetype"].unique()),
            default=sorted(ranked_df["archetype"].unique()),
        )
    with c_filt2:
        duration_range = st.slider("Duration (months)", 1, 60, (1, 60))
    with c_filt3:
        min_np = float(ranked_df["total_net_profit"].min())
        max_np = float(ranked_df["total_net_profit"].max())
        if min_np == max_np:
            max_np += 1.0
        np_range = st.slider(f"Net Profit ({CURRENCY})", min_np, max_np, (min_np, max_np), format="%.0f")

    view = ranked_df[
        (ranked_df["archetype"].isin(archetypes_selected)) &
        (ranked_df["duration_months"].between(duration_range[0], duration_range[1])) &
        (ranked_df["total_net_profit"].between(np_range[0], np_range[1]))
    ].copy()

    show_selected_only = st.checkbox("Show selected projects only", value=False)
    if show_selected_only:
        view = view[view["Selected"] == "✅"]

    display = view.copy()
    for col in ["total_business_value", "total_cost", "total_net_profit"]:
        display[col] = display[col].map(fmt_money)

    cols = ["rank", "Selected", "project_id", "name", "archetype", "duration_months",
            "total_business_value", "total_cost", "total_net_profit", "break_even_month"]
    display = display[cols]

    display = display.rename(columns={
        "rank": "Rank", "Selected": "Selected", "project_id": "ID", "name": "Name",
        "archetype": "Archetype", "duration_months": "Duration (mo)",
        "total_business_value": "Business Value", "total_cost": "Total Cost",
        "total_net_profit": "Net Profit", "break_even_month": "Break-Even (mo)",
    })

    st.dataframe(display, hide_index=True, use_container_width=True, height=520)
    st.caption(f"Projects are ranked by the selected method (**{prio_method}**, set in the sidebar). Change the method or its reinvestment rate there and the table re-ranks live.")
    st.download_button(
        label="📥 Download Filtered Portfolio as CSV",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="prioritized_portfolio.csv",
        mime="text/csv",
    )

elif current_page == 'Project Details':
    st.subheader("Project KPIs over time")
    name_to_id = {f"{r.rank:>3}. {r.project.name}": r.project.project_id for r in ranked}
    default_pick = list(name_to_id.keys())[: min(3, len(name_to_id))]
    picks = st.multiselect("Select one or more projects", options=list(name_to_id.keys()), default=default_pick)
    detail_ids = [name_to_id[p] for p in picks]
    metric = st.selectbox("Metric", options=[
        ("cumulative_net_profit", "Cumulative net profit"),
        ("discounted_cumulative_net_profit", "Discounted cumulative net profit"),
        ("monthly_net_profit", "Monthly net profit"),
        ("business_value", "Monthly business value"),
        ("monthly_cost", "Monthly total cost"),
        ("direct_cost", "Monthly direct cost"),
        ("effort_cost", "Monthly effort cost (FTE × FTE cost)"),
        ("fte_count", "FTE count"),
    ], format_func=lambda x: x[1], index=0)
    metric_col, metric_label = metric
    METRIC_HELP = {
        "cumulative_net_profit": "Running total of net profit (business value − cost) over the project's life. Where the line crosses zero is the break-even point.",
        "discounted_cumulative_net_profit": "Like cumulative net profit, but each month's profit is discounted by the reinvestment rate — early profit counts for more. This is the curve the **Capital Velocity** ranking is built on.",
        "monthly_net_profit": "Net profit generated in each single month (business value − cost that month). Usually negative during the early cost phase.",
        "business_value": "The monthly gross benefit a project creates — revenue, cost savings or reduced risk cost — before subtracting any cost.",
        "monthly_cost": "Total spend in each month: direct cost + effort (FTE × FTE cost).",
        "direct_cost": "Monthly out-of-pocket spend: consultants, licenses, infrastructure.",
        "effort_cost": "Monthly people cost: FTE count × loaded cost per FTE.",
        "fte_count": "How many full-time-equivalent people work on the project each month.",
    }
    st.caption(f"ℹ️ {METRIC_HELP.get(metric_col, '')}")
    if not detail_ids:
        st.info("Pick at least one project above to see its time series.")
    else:
        plot_df = monthly_df[monthly_df["project_id"].isin(detail_ids)].copy()
        plot_df["label"] = plot_df["project_id"] + " — " + plot_df["name"]
        fig = px.line(plot_df, x="month", y=metric_col, color="label", markers=True,
                     labels={"month": "Month", metric_col: metric_label, "label": "Project"})
        if metric_col in ("cumulative_net_profit", "monthly_net_profit", "discounted_cumulative_net_profit"):
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)
            max_abs = float(np.nanmax(np.abs(plot_df[metric_col].to_numpy())))
            if max_abs > 0:
                margin = max_abs * 0.10
                fig.update_yaxes(range=[-(max_abs + margin), max_abs + margin], zeroline=True)
        fig.update_layout(height=480, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("##### Selected projects — summary")
        summary = ranked_df[ranked_df["project_id"].isin(detail_ids)].copy()
        for col in ["total_business_value", "total_cost", "total_net_profit"]:
            summary[col] = summary[col].map(fmt_money)
        st.dataframe(summary[[
            "rank", "project_id", "name", "archetype", "duration_months",
            "total_business_value", "total_cost", "total_net_profit",
            "break_even_month",
        ]].rename(columns={
            "rank": "Rank", "project_id": "ID", "name": "Name",
            "archetype": "Archetype", "duration_months": "Duration (mo)",
            "total_business_value": "Business Value", "total_cost": "Total Cost",
            "total_net_profit": "Net Profit", "break_even_month": "Break-Even (mo)",
        }), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("##### Portfolio composition (selected projects)")
    comp_ranked_df = ranked_df[ranked_df["project_id"].isin(selected_ids)]
    if len(comp_ranked_df) == 0:
        st.info("No projects fit the current constraints, so composition charts are unavailable. Relax the limits in the sidebar.")
    else:
        det_c1, det_c2 = st.columns(2)
        with det_c1:
            archetype_counts = comp_ranked_df["archetype"].value_counts().reset_index()
            archetype_counts.columns = ["Archetype", "Count"]
            fig_donut = px.pie(
                archetype_counts, values="Count", names="Archetype", hole=0.4,
                title="Selected Projects by Archetype",
                color_discrete_sequence=px.colors.sequential.Reds_r
            )
            fig_donut.update_layout(margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_donut, use_container_width=True)
        with det_c2:
            valid_be = comp_ranked_df[comp_ranked_df["break_even_month"].notna()]
            if len(valid_be) > 0:
                fig_hist = px.histogram(
                    valid_be, x="break_even_month", nbins=15,
                    title="Distribution of Break-Even Months (Selected)",
                    labels={"break_even_month": "Break-Even Month"},
                    color_discrete_sequence=["#D2051E"]
                )
                fig_hist.update_layout(bargap=0.1, margin=dict(t=40, b=20, l=20, r=20))
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.caption("No break-even projects in the selected portfolio.")
elif current_page == 'Robustness Simulation':
    # Robustness Simulation = Monte Carlo (top) + rank stability (bottom)
    st.subheader("Monte Carlo Risk Simulation")
    st.caption("Stress-test outcomes under uncertainty: each project's monthly value and cost are randomly perturbed thousands of times to reveal the range of possible results.")

    risk_scope = st.radio(
        "What do you want to simulate?",
        ["Whole Portfolio", "Single Project"],
        horizontal=True, key="risk_scope",
    )
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        iterations = int(st.number_input("Iterations", 100, 5000, 1000, 100, key="risk_iter"))
    with rc2:
        bv_std = st.slider("Value variance (±%)", 0, 100, 20, key="risk_bv",
                           help="Uncertainty in each project's business value (revenue / savings / risk reduction).") / 100.0
    with rc3:
        cost_std = st.slider("Cost variance (±%)", 0, 100, 10, key="risk_cost",
                             help="Uncertainty in each project's cost.") / 100.0

    def _render_mc_results(total_nps: np.ndarray, title: str) -> None:
        prob_loss = (total_nps < 0).mean() * 100
        p10, p50, p90 = np.percentile(total_nps, [10, 50, 90])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("P10 (Worst Case)", fmt_money(p10))
        m2.metric("P50 (Expected)", fmt_money(p50))
        m3.metric("P90 (Best Case)", fmt_money(p90))
        m4.metric("Probability of Loss", f"{prob_loss:.1f}%")
        hist_df = pd.DataFrame({"Total Net Profit": total_nps})
        fig_sim = px.histogram(hist_df, x="Total Net Profit", nbins=45, title=title,
                               color_discrete_sequence=["#D2051E"])
        fig_sim.add_vline(x=0, line_dash="dash", line_color="white", annotation_text="Break-even")
        fig_sim.add_vline(x=p10, line_dash="dot", line_color="orange", annotation_text="P10")
        fig_sim.add_vline(x=p50, line_dash="dot", line_color="green", annotation_text="P50")
        fig_sim.add_vline(x=p90, line_dash="dot", line_color="orange", annotation_text="P90")
        fig_sim.update_layout(margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_sim, use_container_width=True)

    if risk_scope == "Whole Portfolio":
        st.markdown(f"##### Selected portfolio — **{len(selected_projects)} of {len(projects)}** projects (per current constraints)")
        if not selected_projects:
            st.info("No projects are currently selected. Relax the budget / concurrency limits in the sidebar to include projects.")
        elif st.button("Run Portfolio Simulation", type="primary", key="risk_run_portfolio"):
            with st.spinner("Simulating the whole portfolio..."):
                total_nps = simulate_portfolio_profit(selected_projects, n_iter=iterations, bv_std=bv_std, cost_std=cost_std)
            _render_mc_results(total_nps, "Distribution of Simulated Portfolio Net Profit")
            st.caption("Aggregated net profit of all selected projects under simultaneous random shocks. 'Probability of Loss' is the chance the combined portfolio fails to break even.")
    else:
        sim_name_to_id = {f"{r.rank:>3}. {r.project.name}": r.project.project_id for r in ranked}
        selected_sim_project = st.selectbox("Select a project to simulate", options=list(sim_name_to_id.keys()), key="sim_project_select")
        if selected_sim_project and st.button("Run Project Simulation", type="primary", key="risk_run_single"):
            sim_id = sim_name_to_id[selected_sim_project]
            sim_proj = next(p for p in projects if p.project_id == sim_id)
            with st.spinner("Simulating..."):
                total_nps = simulate_portfolio_profit([sim_proj], n_iter=iterations, bv_std=bv_std, cost_std=cost_std)
            _render_mc_results(total_nps, f"Distribution of Simulated Net Profit — {sim_proj.name}")

    st.divider()

    # ---------- B) How stable is the ranking? (rank stability) ----------
    st.markdown("### How stable is the ranking?")
    st.caption("We jitter every project's value and cost and re-rank the whole portfolio many times. If the top projects keep their position, the ranking is robust ('self-stabilizing'). If ranks jump around, the order should be treated with caution.")
    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        rs_iter = int(st.number_input("Iterations", 100, 3000, 500, 100, key="robust_iter"))
    with bc2:
        rs_bv = st.slider("Value variance (±%)", 0, 100, 20, key="robust_bv") / 100.0
    with bc3:
        rs_cost = st.slider("Cost variance (±%)", 0, 100, 10, key="robust_cost") / 100.0
    with bc4:
        rs_topn = int(st.number_input("Focus on Top-N", 3, 30, 10, 1, key="robust_topn"))

    if st.button("Run stability analysis", type="primary", key="robust_run"):
        with st.spinner("Re-ranking the portfolio under uncertainty..."):
            rs = simulate_rank_stability(
                projects, n_iter=rs_iter, bv_std=rs_bv, cost_std=rs_cost,
                weight_value=weight_value, weight_speed=weight_speed,
                method=prio_method, top_n=rs_topn,
            )
        st.session_state["robust_result"] = rs

    rs = st.session_state.get("robust_result")
    if rs is None:
        st.info("Set the parameters and click **Run stability analysis**.")
    else:
        def _verdict(x: float) -> str:
            if x >= 0.9:
                return "Very stable ✅"
            if x >= 0.75:
                return "Stable 🟢"
            if x >= 0.5:
                return "Moderate ⚠️"
            return "Fragile 🚨"
        spearman = rs["spearman_mean"]
        retention = rs["topN_retention"]
        v1, v2 = st.columns(2)
        v1.metric(f"Rank stability (correlation)", f"{spearman:.2f} / 1.00", _verdict(spearman),
                  help="Average Spearman correlation between the perturbed ranking and the current one. 1.00 = order never changes.")
        v2.metric(f"Top-{rs['top_n']} retention", f"{retention*100:.0f}%", _verdict(retention),
                  help=f"On average, this share of today's Top-{rs['top_n']} projects stays in the Top-{rs['top_n']} under uncertainty.")

        # Rank-range plot for the current Top-N
        order = sorted(range(len(rs["base_rank"])), key=lambda i: rs["base_rank"][i])
        top_idx = [i for i in order if rs["base_rank"][i] <= rs["top_n"]]
        yvals = list(range(len(top_idx), 0, -1))   # rank 1 at the top
        names = [rs["project_names"][i] for i in top_idx]
        fig_r = go.Figure()
        for k, i in enumerate(top_idx):
            y = yvals[k]
            fig_r.add_trace(go.Scatter(x=[rs["rank_best"][i], rs["rank_worst"][i]], y=[y, y],
                                       mode="lines", line=dict(color="#D2051E", width=2),
                                       opacity=0.30, showlegend=False, hoverinfo="skip"))
            fig_r.add_trace(go.Scatter(x=[rs["rank_p10"][i], rs["rank_p90"][i]], y=[y, y],
                                       mode="lines", line=dict(color="#D2051E", width=9),
                                       opacity=0.55, showlegend=False, hoverinfo="skip"))
        fig_r.add_trace(go.Scatter(
            x=[rs["base_rank"][i] for i in top_idx], y=yvals, mode="markers",
            marker=dict(color="white", size=11, line=dict(color="#D2051E", width=2)),
            text=names, showlegend=False,
            hovertemplate="<b>%{text}</b><br>current rank %{x}<extra></extra>",
        ))
        fig_r.update_yaxes(tickvals=yvals, ticktext=names)
        fig_r.update_xaxes(title="Rank (1 = best). Thick bar = P10–P90 under uncertainty, thin bar = full range.")
        fig_r.update_layout(title=f"Rank stability of the current Top-{rs['top_n']}",
                            margin=dict(t=40, b=20, l=20, r=20),
                            height=max(320, 32 * len(top_idx) + 80))
        st.plotly_chart(fig_r, use_container_width=True)
        st.caption("Each dot is a project's current rank; the bar shows how far that rank drifts when value and cost are uncertain. Short bars near the left = reliably top-ranked.")

elif current_page == 'Execution Strategy':
    # Execution Strategy (sequential vs. parallel scheduling)
    # --- Capital recycling: most money, fastest, reinvested again & again ---
    st.markdown("### 🔬 Which Approach Compounds Capital Fastest?")
    st.caption(
        "The real goal: make money **fast**, reinvest it into the next projects, and repeat — month after month. "
        "Starting from your **Total Budget** as the initial pot of capital, each project's returns are recycled to "
        "fund further projects as soon as the cash is available. The line that climbs fastest creates the most money "
        "in the least time. *(Capital Velocity rewards early profit, so capital recycles soonest; ROI ignores **when** "
        "profit arrives; Value Creation Rating assumes profit is spread evenly — the latter two leave money on the table.)*"
    )
    start_cap = float(total_budget) if total_budget else 50_000_000.0
    horizon = int(st.slider("Horizon (months)", 1, 60, 12, 1, key="reinvest_horizon"))
    st.caption(f"Starting capital = current **Total Budget** ({fmt_money(start_cap)}); change it in the sidebar.")

    method_colors = {"Capital Velocity": "#D2051E", "VCR": "#1f77b4", "ROI": "#ff8c00"}
    fig_cap = go.Figure()
    cap_rows = []
    for m in ["Capital Velocity", "Value Creation Rating", "ROI"]:
        ranked_m = score_projects(projects, weight_value=weight_value, weight_speed=weight_speed,
                                  method=m, reinvest_rate=reinvest_rate)
        order_m = [s.project for s in ranked_m]
        sim = simulate_reinvestment(order_m, start_cap, horizon)
        short = {"Value Creation Rating": "VCR"}.get(m, m)
        fig_cap.add_trace(go.Scatter(
            x=sim["months"], y=sim["capital"], mode="lines",
            line=dict(color=method_colors.get(short, "#888"), width=3.5 if m == "Capital Velocity" else 2),
            name=short,
            hovertemplate=f"<b>{short}</b><br>Month %{{x}}<br>Capital: %{{y:,.0f}} {CURRENCY}<extra></extra>",
        ))
        cap_rows.append({"Method": short, "final": sim["final_capital"],
                         "mult": sim["final_capital"] / start_cap, "funded": sim["funded"]})
    fig_cap.add_hline(y=start_cap, line_dash="dot", line_color="gray", opacity=0.5,
                      annotation_text="Starting capital")
    fig_cap.update_layout(title=f"Capital Over Time with Reinvestment (start {fmt_money(start_cap)})",
                          xaxis_title="Month", yaxis_title=f"Capital ({CURRENCY})",
                          height=440, margin=dict(t=50, b=20, l=20, r=20), legend_title_text="")
    st.plotly_chart(fig_cap, use_container_width=True)

    df_cap = pd.DataFrame(cap_rows)
    win = df_cap.loc[df_cap["final"].idxmax()]
    msg = (f"🏆 Compounds capital fastest over {horizon} months: **{win['Method']}** — "
           f"{fmt_money(win['final'])} ({win['mult']:.1f}× the starting capital).")
    if win["Method"] == "Capital Velocity":
        msg += " Capital Velocity recycles capital soonest — the most money, in the least time."
    st.success(msg)

    with st.expander("Show the underlying numbers"):
        st.dataframe(pd.DataFrame({
            "Method": df_cap["Method"],
            f"Capital after {horizon} mo": [fmt_money(v) for v in df_cap["final"]],
            "Growth multiple": [f"{v:.2f}×" for v in df_cap["mult"]],
            "Projects funded": [int(v) for v in df_cap["funded"]],
        }), hide_index=True, use_container_width=True)
    st.divider()

    st.subheader("Scenario Comparison: Sequential vs. Parallel Execution")
    seq_sched = schedule_portfolio(ranked, mode="Sequential", budget=total_budget, max_concurrency=None, parallel_spending=None)
    seq_timeline = build_global_timeline(seq_sched)
    par_sched = schedule_portfolio(ranked, mode="Parallel", budget=total_budget, max_concurrency=max_concurrency, parallel_spending=max_monthly_spend)
    par_timeline = build_global_timeline(par_sched)
    if seq_sched:
        max_seq_duration = max(s.end_month for s in seq_sched)
        seq_cost = sum(s.scored.project.total_cost for s in seq_sched)
        seq_value = sum(s.scored.project.total_business_value for s in seq_sched)
        seq_np = float(seq_timeline["Cumulative Net Profit"].iloc[-1]) if len(seq_timeline) > 0 else 0.0
        seq_roi = (seq_np / seq_cost) * 100 if seq_cost > 0 else 0.0
    else:
        max_seq_duration, seq_cost, seq_value, seq_np, seq_roi = 0, 0.0, 0.0, 0.0, 0.0
    if par_sched:
        max_par_duration = max(s.end_month for s in par_sched)
        par_cost = sum(s.scored.project.total_cost for s in par_sched)
        par_value = sum(s.scored.project.total_business_value for s in par_sched)
        par_np = float(par_timeline["Cumulative Net Profit"].iloc[-1]) if len(par_timeline) > 0 else 0.0
        par_roi = (par_np / par_cost) * 100 if par_cost > 0 else 0.0
    else:
        max_par_duration, par_cost, par_value, par_np, par_roi = 0, 0.0, 0.0, 0.0, 0.0
    st.caption("Same projects, cost and net profit either way — only the **time to completion** differs:")
    tc1, tc2 = st.columns(2)
    tc1.metric("Sequential — Time to Completion", f"{max_seq_duration} months")
    tc2.metric("Parallel — Time to Completion", f"{max_par_duration} months")
    st.markdown("### 📈 Cumulative Net Profit Growth Comparison")
    compare_lines = []
    if len(seq_timeline) > 0:
        for _, row in seq_timeline.iterrows():
            compare_lines.append({"Month": int(row["Month"]), "Cumulative Net Profit": float(row["Cumulative Net Profit"]), "Scenario": "Sequential"})
    if len(par_timeline) > 0:
        for _, row in par_timeline.iterrows():
            compare_lines.append({"Month": int(row["Month"]), "Cumulative Net Profit": float(row["Cumulative Net Profit"]), "Scenario": "Parallel"})
    if compare_lines:
        df_line_compare = pd.DataFrame(compare_lines)
        fig_line_compare = px.line(df_line_compare, x="Month", y="Cumulative Net Profit", color="Scenario",
                                  title="Cumulative Net Profit Growth: Sequential vs. Parallel",
                                  color_discrete_map={"Sequential": "#888888", "Parallel": "#D2051E"})
        fig_line_compare.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)
        fig_line_compare.update_layout(margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_line_compare, use_container_width=True)
    else:
        st.info("No timeline data available under the current constraints.")
    st.markdown("### 👥 Resource & Cost Utilization")
    c_res1, c_res2 = st.columns(2)
    with c_res1:
        fte_lines = []
        if len(seq_timeline) > 0:
            for _, row in seq_timeline.iterrows():
                fte_lines.append({"Month": int(row["Month"]), "FTE Count": float(row["FTE Count"]), "Scenario": "Sequential"})
        if len(par_timeline) > 0:
            for _, row in par_timeline.iterrows():
                fte_lines.append({"Month": int(row["Month"]), "FTE Count": float(row["FTE Count"]), "Scenario": "Parallel"})
        if fte_lines:
            df_fte_compare = pd.DataFrame(fte_lines)
            fig_fte = px.line(df_fte_compare, x="Month", y="FTE Count", color="Scenario",
                             title="FTE Resource Usage Over Time",
                             color_discrete_map={"Sequential": "#888888", "Parallel": "#D2051E"})
            fig_fte.update_layout(margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_fte, use_container_width=True)
        else:
            st.caption("No resource utilization data available.")
    with c_res2:
        spend_lines = []
        if len(seq_timeline) > 0:
            for _, row in seq_timeline.iterrows():
                spend_lines.append({"Month": int(row["Month"]), "Cumulative Spend": float(row["Cumulative Cost"]), "Scenario": "Sequential"})
        if len(par_timeline) > 0:
            for _, row in par_timeline.iterrows():
                spend_lines.append({"Month": int(row["Month"]), "Cumulative Spend": float(row["Cumulative Cost"]), "Scenario": "Parallel"})
        if spend_lines:
            df_spend_compare = pd.DataFrame(spend_lines)
            fig_spend_compare = px.line(df_spend_compare, x="Month", y="Cumulative Spend", color="Scenario",
                                       title="Cumulative Investment Spend Over Time",
                                       color_discrete_map={"Sequential": "#888888", "Parallel": "#D2051E"})
            if enable_budget and total_budget:
                fig_spend_compare.add_hline(y=total_budget, line_dash="dash", line_color="orange", annotation_text="Total Budget Limit")
            fig_spend_compare.update_layout(margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig_spend_compare, use_container_width=True)
        else:
            st.caption("No budget consumption data available.")
    st.markdown("### Execution Timeline (Gantt)")
    active_sched = par_sched if execution_mode == "Parallel" else seq_sched
    if active_sched:
        gantt_data = []
        for s in active_sched:
            gantt_data.append({"Rank": s.scored.rank, "Task": f"{s.scored.rank}. {s.scored.project.name}", "Start Month": s.start_month,
                              "Duration (Months)": s.scored.project.duration_months, "Archetype": s.scored.project.archetype})
        df_gantt = pd.DataFrame(gantt_data).sort_values("Rank", ascending=False)  # rank 1 ends up on top
        fig_gantt = px.bar(df_gantt, x="Duration (Months)", y="Task", base="Start Month", color="Archetype", orientation='h',
                          title=f"Project Timeline ({execution_mode} mode) — ordered by priority rank",
                          color_discrete_sequence=px.colors.qualitative.Bold,
                          category_orders={"Task": df_gantt["Task"].tolist()})
        fig_gantt.update_layout(margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("No projects scheduled.")

elif current_page == 'Department Alignment':
    # Department Alignment (cross-functional buy-in)
    st.subheader("Interdepartmental Alignment & Buy-In")
    dept_reviews = init_dept_reviews(projects)

    # --- Fact-based department alignment of the SELECTED portfolio ----------
    # Each department is scored 0-10 from the portfolio's OBJECTIVE KPIs, not
    # from stakeholder opinions:
    #   Finance         = portfolio return on capital (ROI)
    #   IT/R&D          = share of funded business value in R&D / tech project types
    #   Sales/Marketing = share of funded business value in customer-facing types
    #   Operations      = share of funded business value in operations types
    DEPT_ARCHETYPES = {
        "IT/R&D": {"Tool R&D", "Software Platform", "Digital Transformation"},
        "Sales/Marketing": {"Marketing Campaign", "Software Platform"},
        "Operations": {"Manufacturing Process Improvement", "Supply Chain Optimization",
                       "Sustainability / Compliance", "Training & Enablement"},
    }
    sel = selected_projects
    if sel:
        tot_cost = sum(p.total_cost for p in sel)
        tot_np = sum(p.total_net_profit for p in sel)
        tot_value = sum(p.total_business_value for p in sel) or 1.0
        avg_finance = float(np.clip(tot_np / tot_cost, 0, 10)) if tot_cost > 0 else 0.0
        _share = lambda d: 10.0 * sum(p.total_business_value for p in sel if p.archetype in DEPT_ARCHETYPES[d]) / tot_value
        avg_it, avg_sales, avg_ops = _share("IT/R&D"), _share("Sales/Marketing"), _share("Operations")
    else:
        avg_finance = avg_it = avg_sales = avg_ops = 0.0
    oas = float(np.mean([avg_finance, avg_it, avg_sales, avg_ops]))

    align_c1, align_c2 = st.columns([1, 2])
    with align_c1:
        if oas >= 7.0:
            st.metric("Org Alignment Score (OAS)", f"{oas:.1f} / 10", "Well balanced ✅")
        elif oas >= 4.0:
            st.metric("Org Alignment Score (OAS)", f"{oas:.1f} / 10", "Moderately balanced ⚠️")
        else:
            st.metric("Org Alignment Score (OAS)", f"{oas:.1f} / 10", "Heavily concentrated 🔎")
        st.caption("**OAS** = average of the four fact-based department scores. High = the funded portfolio serves all departments fairly evenly; low = it leans heavily toward one or two.")
    with align_c2:
        st.markdown("**Departmental Alignment Radar**")
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=[avg_finance, avg_it, avg_sales, avg_ops, avg_finance],
                                           theta=["Finance", "IT/R&D", "Sales/Marketing", "Operations", "Finance"],
                                           fill="toself", name="Department fit", line_color="#D2051E",
                                           fillcolor="rgba(210, 5, 30, 0.2)"))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False,
                               margin=dict(t=20, b=20, l=20, r=20), height=200)
        st.plotly_chart(fig_radar, use_container_width=True)
        st.caption("Computed from the selected portfolio's hard numbers — Finance from its ROI, the others from the share of funded business value in each department's project types. Not based on opinions.")
    st.divider()
    st.subheader("📝 Project Reviews & Collaboration Workspace")
    col_p_sel, col_empty = st.columns([2, 2])
    with col_p_sel:
        selected_pid = st.selectbox("Select Project to Review", options=[p.project_id for p in projects],
                                   format_func=lambda pid: f"{pid} - {next(p.name for p in projects if p.project_id == pid)}")
    p_obj = next(p for p in projects if p.project_id == selected_pid)
    p_review = dept_reviews.get(selected_pid, {"scores": {"Finance": 7, "IT/R&D": 7, "Sales/Marketing": 7, "Operations": 7}, "comments": []})
    col_rev_left, col_rev_right = st.columns(2)
    with col_rev_left:
        st.markdown("##### Current Department Ratings (avg. of reviews)")
        _comment_scores = {"Finance": [], "IT/R&D": [], "Sales/Marketing": [], "Operations": []}
        for _c in p_review.get("comments", []):
            if _c.get("dept") in _comment_scores:
                _comment_scores[_c["dept"]].append(_c.get("score", 0))
        scores_df = pd.DataFrame({
            "Department": ["Finance", "IT/R&D", "Sales/Marketing", "Operations"],
            "Avg Rating": [f"{np.mean(v):.1f} (n={len(v)})" if v else "—"
                           for v in (_comment_scores["Finance"], _comment_scores["IT/R&D"],
                                     _comment_scores["Sales/Marketing"], _comment_scores["Operations"])],
        })
        st.table(scores_df.set_index("Department"))
        st.caption("Average buy-in rating per department, computed from all reviews in the discussion log for this project. '—' = no review yet.")
        st.markdown("##### Submit a New Department Review")
        with st.form("new_review_form", clear_on_submit=True):
            r_dept = st.selectbox("Department", ["Finance", "IT/R&D", "Sales/Marketing", "Operations"])
            r_name = st.text_input("Reviewer Name", placeholder="e.g. Finance Controller")
            r_score = st.slider("Buy-In Score (1-10)", 1, 10, 7,
                                help="How strongly this department supports / believes in the project. 1 = no support, 10 = full support.")
            r_text = st.text_area("Collaboration Notes", placeholder="Share feedback or alignment flags...")
            submit_review = st.form_submit_button("Submit & Save Review", type="primary")
            if submit_review:
                if not r_name.strip() or not r_text.strip():
                    st.error("Please provide both a Reviewer Name and Collaboration Notes.")
                else:
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    score_key = r_dept
                    p_review["scores"][score_key] = r_score
                    p_review["comments"].append({"dept": r_dept, "user": r_name, "score": r_score, "text": r_text, "time": now_str})
                    dept_reviews[selected_pid] = p_review
                    save_dept_reviews(dept_reviews)
                    st.success("Department review submitted successfully and saved to disk!")
                    st.rerun()
    with col_rev_right:
        st.markdown("##### Collaborative Discussion Log")
        comments = p_review.get("comments", [])
        if len(comments) == 0:
            st.info("No alignment discussion yet. Use the review form to post the first comment!")
        else:
            for c in reversed(comments):
                dept_color = "#D2051E" if c["dept"] == "Finance" else "#005a9c" if c["dept"] == "IT/R&D" else "#228b22" if c["dept"] == "Sales/Marketing" else "#ff8c00"
                st.markdown(f"""
                    <div style="background-color: rgba(120,120,120,0.06); padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid {dept_color};">
                        <strong style="color: {dept_color};">[{c['dept']}]</strong> <strong>{c['user']}</strong> (Score: {c['score']}/10)<br/>
                        <span style="font-size: 0.8rem; color: gray;">{c['time']}</span><br/>
                        <p style="margin-top: 6px; margin-bottom: 0;">{c['text']}</p>
                    </div>
                    """, unsafe_allow_html=True)

    st.divider()
    st.subheader("Stakeholder Report Generator")
    report_name_to_id = {f"{r.rank:>3}. {r.project.name}": r.project.project_id for r in ranked}
    report_proj = st.selectbox("Select project for report", options=list(report_name_to_id.keys()), key="report_sel")
    if report_proj:
        rp_id = report_name_to_id[report_proj]
        rp_row = ranked_df[ranked_df["project_id"] == rp_id].iloc[0]
        notes = st.text_area("Add custom notes for the stakeholder:", placeholder="e.g., This project is critical for Q3 alignment...")
        report_text = f"""# Executive Project Summary: {rp_row['name']}
**Archetype:** {rp_row['archetype']}
**Duration:** {rp_row['duration_months']} months
**Rank:** {rp_row['rank']}

## Financials
- **Total Business Value:** {fmt_money(rp_row['total_business_value'])}
- **Total Cost:** {fmt_money(rp_row['total_cost'])}
- **Net Profit:** {fmt_money(rp_row['total_net_profit'])}
- **Break-Even Month:** {rp_row['break_even_month']}

## Stakeholder Notes
{notes}
"""
        st.markdown("**Report Preview:**")
        st.info(report_text)
        st.download_button(label="📥 Download Stakeholder Report", data=report_text.encode("utf-8"), file_name=f"report_{rp_id}.txt", mime="text/plain")

elif current_page == 'Add Project':
    # Add Project (detailed monthly or high-level estimate)
    st.subheader("Add a new project")
    st.caption("Choose how much detail you have about the project. Use **Detailed** if you've built a full business case with monthly numbers, or **High-level** if you only have totals.")
    mode = st.radio("Input mode", options=["Detailed business case (monthly numbers ready)", "High-level estimates (totals only)"],
                   horizontal=True, key="add_mode", label_visibility="collapsed")
    st.divider()
    if mode.startswith("Detailed"):
        _render_detailed_add(projects)
    else:
        _render_highlevel_add(projects)

elif current_page == 'User Guide':
    # User Guide & documentation
    st.subheader("Executive Documentation")
    st.markdown("""
    Welcome to the **Hilti Project Prioritization & Optimization Platform**. This cockpit provides strategic portfolio governance, interactive side-by-side simulations, cross-departmental alignment, and on-demand AI consulting.
    """)
    
    with st.expander("Platform Navigation & Feature Guide", expanded=True):
        st.markdown("""
        The platform is divided into sections, accessible via the sidebar navigation:
        
        * **Portfolio Overview**: A high-level view of the portfolio. Shows the key "Ranking — Cumulative Net Profit over Time" chart (each project's net profit accumulating over its lifetime, with its priority rank), the four portfolio KPIs, and the prioritized projects table. You can filter by Archetype, Duration, and Net Profit, and download the filtered list as a CSV.
        * **Project Details**: Deep dive into individual project metrics over time (FTE count, direct costs, effort costs, cumulative and discounted-cumulative net profit) and overall portfolio composition analysis.
        * **Robustness Simulation**: Monte Carlo on the whole portfolio (or a single project) to stress-test net profit under value and cost uncertainty, plus rank-stability analysis (Spearman correlation and Top-N retention) showing how reliable the prioritized order stays.
        * **Execution Strategy**: Compares prioritization methods (Capital Velocity vs. Value Creation Rating vs. ROI) and execution scenarios (Sequential vs. Parallel execution) side-by-side to optimize cumulative net profit.
        * **Department Alignment**: Tracks cross-functional alignment and buy-in across Finance, IT/R&D, Sales/Marketing, and Operations using a radar chart and Org Alignment Score (OAS), and hosts a collaborative discussion workspace.
        * **Add Project**: Allows adding custom projects using a Detailed monthly grid editor or a High-level estimates generator with customizable value shape curves.
        * **Copilot**: An interactive AI Assistant capable of comparing projects, explaining prioritization drivers, and running instant what-if budget scenarios.
        """)

    with st.expander("Prioritization Methodology & Formulas", expanded=False):
        st.markdown(r"""
        The platform supports three distinct prioritization algorithms:
        
        #### 1. Capital Velocity (Default)
        Discounted net profit **per CHF invested** — a time-aware ROI that rewards fast payback, because money back sooner can be reinvested into the next projects sooner:
        $$\text{Capital Velocity} = \frac{\sum_{t=1}^{D} \text{NetProfit}_t \,/\, (1+r)^{t}}{\text{Total Cost}}, \quad r = (1+\text{reinvest})^{1/12}-1$$
        Where:
        - $\text{NetProfit}_t$ is the project's net profit in month $t$ (the real monthly profile, not an average).
        - $r$ comes from the **Reinvestment rate** slider. At $0\%$ Capital Velocity equals plain ROI; higher rates reward earlier profit more strongly.

        #### 2. Value Creation Rating
        Net profit generated per unit of time:
        $$\text{Value Creation Rating} = \frac{\text{Net Profit}}{\text{Duration}} = \frac{\text{Business Value} - \text{Costs}}{\text{Duration}}$$
        
        #### 3. Return on Investment (ROI)
        ROI ranks projects based on financial cost-efficiency:
        $$\text{ROI} = \frac{\text{Total Net Profit}}{\text{Total Cost}}$$
        """)
        
    with st.expander("Multi-Constraint Portfolio Optimization & Parallel Scheduling", expanded=False):
        st.markdown(r"""
        Under the **Execution Strategy** page, the platform schedules projects dynamically based on resource and cash flow constraints:
        
        - **Total Available Budget Constraint**:
          $$\sum_{i \in \text{Selected}} \text{Total Cost}_i \le \text{Total Budget}$$
        - **Monthly Spending Limit Constraint**:
          $$\sum_{i \in \text{Active}(t)} \text{Monthly Spend}_{i, t} \le \text{Max Monthly Spending Limit}$$
        - **Concurrency Constraint**:
          $$|\text{Active}(t)| \le \text{Max Concurrency Limit}$$
          
        *Note: In Parallel mode, the scheduling algorithm operates greedily down the priority list, dynamically sliding projects to start as early as possible (from Month 1 onwards) without violating the overlapping monthly spend or concurrency constraints.*
        """)

    with st.expander("Risk & Robustness Analysis Methodology", expanded=False):
        st.markdown(r"""
        To deal with estimation uncertainty, the platform provides advanced simulation features:
        
        #### 1. Monte Carlo Risk Simulation
        We apply random perturbations to monthly business value and monthly costs:
        - $\text{Value}_t \sim \text{Normal}(\mu_v, \sigma_v)$
        - $\text{Cost}_t \sim \text{Normal}(\mu_c, \sigma_c)$
        
        Key Outputs:
        - **P10 (Worst Case)**: 10% probability that the net profit will fall below this value.
        - **P50 (Expected)**: Median outcome of the simulation.
        - **P90 (Best Case)**: 90% probability that the net profit will be below this value (or 10% chance to exceed it).
        - **Probability of Loss**: The percentage of iterations where cumulative net profit is less than 0.
        
        #### 2. Sensitivity Analysis (Tornado Chart)
        Measures the impact of a $\pm X\%$ shift in each driver (Value, Direct Cost, FTE Cost, Concurrency limit, etc.) on the total portfolio net profit. Drivers are ordered by the magnitude of their swing.
        
        #### 3. Rank Stability
        Runs multiple prioritization passes under random variance and calculates:
        - **Spearman Rank Correlation**: Average correlation coefficient between the baseline priority list and the perturbed lists (value close to 1.0 indicates stable priority order).
        - **Top-N Retention**: The average percentage of baseline Top-N projects that remain in the Top-N after random noise is applied.
        """)

    with st.expander("Interdepartmental Alignment Score (OAS)", expanded=False):
        st.markdown(r"""
        Successful implementation requires buy-in from multiple departments. The **Department Alignment** page aggregates buy-in scores (1-10 scale) from four core business units:
        
        - **Finance**: Evaluates NPV, ROI, and budget alignment.
        - **IT/R&D**: Evaluates technical feasibility and resource capacity.
        - **Sales/Marketing**: Evaluates commercial readiness and customer value.
        - **Operations**: Evaluates delivery complexity and supply chain impact.
        
        The **Org Alignment Score (OAS)** is the average of these ratings:
        $$\text{OAS} = \frac{\text{Finance} + \text{IT/R\&D} + \text{Sales/Marketing} + \text{Operations}}{4}$$
        
        OAS thresholds:
        - **OAS $\ge 8.0$**: Strong Alignment
        - **$6.0 \le$ OAS $< 8.0$**: Moderate Alignment
        - **OAS $< 6.0$**: Needs Review
        """)

elif current_page == 'Copilot':
    st.subheader("🤖 Hilti Portfolio Copilot")
    st.caption("Ask me about project performance, constraints, and what-if scenarios.")
    
    # Initialize chat history in session state
    if "copilot_messages" not in st.session_state:
        st.session_state.copilot_messages = [{
            "role": "assistant",
            "content": "Hello! I'm your Hilti Portfolio Assistant. I can help you compare projects, run what-if budget simulations, and explain ranking drivers. How can I assist you today?"
        }]
    
    # CSS for chat styling
    chat_css = """
    <style>
    .chat-container {
        background: linear-gradient(145deg, #1a1a1a 0%, #0f0f0f 100%);
        border-radius: 24px;
        padding: 20px;
        margin-top: 15px;
        border: 1px solid rgba(210, 5, 30, 0.25);
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        height: 550px;
        display: flex;
        flex-direction: column;
    }
    .chat-messages {
        flex-grow: 1;
        overflow-y: auto;
        padding-right: 10px;
        margin-bottom: 15px;
        scroll-behavior: smooth;
    }
    .chat-messages::-webkit-scrollbar { width: 6px; }
    .chat-messages::-webkit-scrollbar-track { background: #2a2a2a; border-radius: 3px; }
    .chat-messages::-webkit-scrollbar-thumb { background: #D2051E; border-radius: 3px; }
    .user-message {
        background: rgba(210, 5, 30, 0.12);
        border: 1px solid rgba(210, 5, 30, 0.25);
        border-radius: 18px;
        padding: 10px 16px;
        margin: 10px 0;
        text-align: right;
        max-width: 80%;
        margin-left: auto;
    }
    .assistant-message {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 18px;
        padding: 12px 16px;
        margin: 10px 0;
        text-align: left;
        max-width: 80%;
        margin-right: auto;
    }
    .chat-input {
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 24px;
        padding: 12px 18px;
        color: white;
        width: 100%;
    }
    .chat-input:focus {
        outline: none;
        border-color: #D2051E;
    }
    </style>
    """
    st.markdown(chat_css, unsafe_allow_html=True)
    
    # Copilot logic
    with st.container():
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.copilot_messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="user-message">💬 {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="assistant-message">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
        
        # Chat input
        user_query = st.chat_input("e.g., Compare P-0001 and P-0002, or What if budget is 30 million CHF?", key="copilot_input")
        
        if user_query:
            # Add user message
            st.session_state.copilot_messages.append({"role": "user", "content": user_query})
            query_lower = user_query.lower()
            
            # Simple rule-based response logic
            response = ""
            
            # 1. Compare projects
            if "compare" in query_lower and any(pid in query_lower for pid in ["p-", "project"]):
                import re
                pids = re.findall(r"P-\d{4}", query_lower.upper())
                if len(pids) >= 2:
                    p1, p2 = pids[0], pids[1]
                    p1_obj = next((p for p in projects if p.project_id == p1), None)
                    p2_obj = next((p for p in projects if p.project_id == p2), None)
                    if p1_obj and p2_obj:
                        r1 = ranked_df[ranked_df["project_id"] == p1].iloc[0]
                        r2 = ranked_df[ranked_df["project_id"] == p2].iloc[0]
                        response = f"### 📊 Comparison: {p1_obj.name} ({p1}) vs {p2_obj.name} ({p2})\n\n"
                        comparison_df = pd.DataFrame({
                            "Metric": ["Rank", "Archetype", "Duration (Months)", "Total Cost", "Business Value", "Net Profit", "Break-Even Month", "Status"],
                            p1_obj.name: [f"#{r1['rank']}", r1['archetype'], r1['duration_months'], 
                                         fmt_money(r1['total_cost']), fmt_money(r1['total_business_value']), 
                                         fmt_money(r1['total_net_profit']), f"Month {r1['break_even_month']}" if not pd.isna(r1['break_even_month']) else "Never",
                                         r1['Selected']],
                            p2_obj.name: [f"#{r2['rank']}", r2['archetype'], r2['duration_months'], 
                                         fmt_money(r2['total_cost']), fmt_money(r2['total_business_value']), 
                                         fmt_money(r2['total_net_profit']), f"Month {r2['break_even_month']}" if not pd.isna(r2['break_even_month']) else "Never",
                                         r2['Selected']]
                        })
                        response += comparison_df.to_markdown(index=False)
                        higher_rank_name = p1_obj.name if r1['rank'] < r2['rank'] else p2_obj.name
                        reason = "discounted net profit per CHF (Capital Velocity)" if prio_method == "Capital Velocity" else f"{prio_method} score"
                        response += f"\n\n**💡 Copilot Insight**: **{higher_rank_name}** ranks higher under current weights because of its superior {reason}."
                    else:
                        response = f"I couldn't find one or both of those project IDs ({', '.join(pids)}) in the current portfolio. Please verify the IDs and try again!"
                else:
                    response = "To compare projects, please list at least two project IDs (e.g. *'Compare P-0001 and P-0002'*)."
            
            # 2. What-if Budget simulation
            elif "budget" in query_lower or "limit" in query_lower or "reduce" in query_lower or "chf" in query_lower:
                query_no_commas = query_lower.replace(",", "")
                numbers = re.findall(r"\d+", re.sub(r"[mk]", lambda m: {"m": "000000", "k": "000"}.get(m.group(), ""), query_no_commas))
                budgets = [int(n) for n in numbers if int(n) > 0]
                if len(budgets) > 0:
                    sim_budget = budgets[0]
                    m_match = re.search(r"(\d+\.?\d*)\s*m", query_lower)
                    if m_match:
                        sim_budget = int(float(m_match.group(1)) * 1000000)
                    sim_scheduled = schedule_portfolio(ranked, mode=execution_mode, budget=sim_budget, 
                                                      max_concurrency=max_concurrency, parallel_spending=max_monthly_spend)
                    sim_selected_ids = {s.scored.project.project_id for s in sim_scheduled}
                    kept = [p.name for p in projects if p.project_id in sim_selected_ids]
                    dropped = [p.name for p in projects if p.project_id not in sim_selected_ids]
                    response = f"### 🕹️ What-If Simulation: Budget Constraint = **{fmt_money(sim_budget)}**\n\n" \
                               f"- **Scheduled Projects**: {len(sim_scheduled)} / {len(projects)}\n" \
                               f"- **Total Portfolio Cost**: {fmt_money(sum(s.scored.project.total_cost for s in sim_scheduled))}\n" \
                               f"- **Cumulative Net Profit**: {fmt_money(sum(s.scored.project.total_net_profit for s in sim_scheduled))}\n\n"
                    if len(dropped) > 0:
                        response += f"⚠️ **Dropped Projects due to limit**: {', '.join(dropped[:5])}"
                        if len(dropped) > 5:
                            response += f" and {len(dropped) - 5} others."
                    else:
                        response += "✅ All projects are successfully scheduled within this budget."
                else:
                    response = "To simulate a budget limit, please specify an amount (e.g. *'What if budget is 25,000,000 CHF?'* or *'Limit budget to 5M'*)."
            
            # 3. Top 3 Projects
            elif "top" in query_lower or "best" in query_lower or "rank" in query_lower:
                top_3 = ranked_df.head(3)
                response = "### 🏆 Current Top 3 Prioritized Projects\n\n"
                for idx, row in top_3.iterrows():
                    response += f"1. **{row['name']}** (Rank #{row['rank']}) - Archetype: *{row['archetype']}*, Profit: **{fmt_money(row['total_net_profit'])}**, Selected: {row['Selected']}\n"
            
            # 4. Archetype Analysis
            elif "archetype" in query_lower or "most expensive" in query_lower or "cost" in query_lower:
                arch_costs = ranked_df.groupby("archetype")["total_cost"].sum().reset_index()
                arch_costs = arch_costs.sort_values(by="total_cost", ascending=False)
                response = "### 💰 Archetype Cost Distribution\n\n"
                for idx, row in arch_costs.iterrows():
                    response += f"- **{row['archetype']}**: Total Cost of **{fmt_money(row['total_cost'])}**\n"
                response += f"\n*Insight: The most expensive archetype is **{arch_costs.iloc[0]['archetype']}**.*"
            
            # 5. Default Hilti Consulting Response
            else:
                response = "### 🔧 Hilti Portfolio Assistant\n\n" \
                           "I can help you review alignment, run optimizations, and draft summaries.\n\n" \
                           f"Currently, there are **{len(selected_projects)}** projects scheduled out of **{len(projects)}** total projects. " \
                           f"The total cumulative profit of this portfolio is **{fmt_money(total_np)}** against a total cost of **{fmt_money(sum(p.total_cost for p in selected_projects))}**.\n\n" \
                           "Please try asking to compare projects (e.g., 'Compare P-0001 and P-0002') or simulate budget limits!"
            
            # Add assistant response
            st.session_state.copilot_messages.append({"role": "assistant", "content": response})
            st.rerun()

# Inject JS to style the container
components.html('''
<script>
    const doc = window.parent.document;
    const anchors = doc.querySelectorAll('.copilot-drawer-anchor');
    anchors.forEach(anchor => {
        const container = anchor.closest('div[data-testid="stVerticalBlock"]');
        if (container) {
            container.classList.add('copilot-drawer-content');
        }
    });
</script>
''', height=0, width=0)

# --------------------------------------------------------------------------
# Guided Tour Help Button
# --------------------------------------------------------------------------
components.html('''
<!DOCTYPE html>
<html>
<head>
<style>
  /* ── Floating Help Button ─────────────────────────────────────────── */
  #hilti-help-btn {
    position: fixed;
    bottom: 28px;
    right: 28px;
    z-index: 99999;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #D2051E 0%, #8B0012 100%);
    color: #fff;
    font-size: 1.5rem;
    font-weight: 700;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 20px rgba(210,5,30,0.55), 0 2px 8px rgba(0,0,0,0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    font-family: 'Segoe UI', system-ui, sans-serif;
    user-select: none;
  }
  #hilti-help-btn:hover {
    transform: scale(1.12);
    box-shadow: 0 6px 28px rgba(210,5,30,0.70), 0 3px 12px rgba(0,0,0,0.45);
  }
  #hilti-help-btn:active { transform: scale(0.96); }

  /* Pulse ring on idle */
  #hilti-help-btn::after {
    content: '';
    position: absolute;
    inset: -6px;
    border-radius: 50%;
    border: 2px solid rgba(210,5,30,0.5);
    animation: pulse-ring 2.2s ease-out infinite;
  }
  @keyframes pulse-ring {
    0%   { transform: scale(0.95); opacity: 0.8; }
    70%  { transform: scale(1.25); opacity: 0; }
    100% { transform: scale(1.25); opacity: 0; }
  }

  /* ── Tour Backdrop ────────────────────────────────────────────────── */
  #tour-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.72);
    z-index: 99998;
    backdrop-filter: blur(3px);
    animation: fade-in 0.25s ease;
  }
  @keyframes fade-in { from { opacity:0; } to { opacity:1; } }

  /* ── Tour Card ────────────────────────────────────────────────────── */
  #tour-card {
    position: fixed;
    z-index: 100000;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%) scale(0.92);
    width: min(560px, 92vw);
    background: linear-gradient(160deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    border: 1px solid rgba(210,5,30,0.35);
    border-radius: 20px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04);
    padding: 0;
    overflow: hidden;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    opacity: 0;
    transition: opacity 0.28s ease, transform 0.28s cubic-bezier(.34,1.56,.64,1);
  }
  #tour-card.visible {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }

  /* Card header strip */
  #tour-header {
    background: linear-gradient(90deg, #D2051E 0%, #8B0012 100%);
    padding: 14px 22px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  #tour-header-left { display: flex; align-items: center; gap: 10px; }
  #tour-step-icon {
    width: 36px; height: 36px;
    background: rgba(255,255,255,0.2);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
  }
  #tour-title {
    font-size: 1rem; font-weight: 700; color: #fff;
    letter-spacing: 0.3px;
  }
  #tour-subtitle {
    font-size: 0.72rem; color: rgba(255,255,255,0.72);
    letter-spacing: 1px; text-transform: uppercase; margin-top: 1px;
  }
  #tour-close-x {
    background: rgba(255,255,255,0.15);
    border: none; color: #fff;
    width: 28px; height: 28px;
    border-radius: 50%; font-size: 0.9rem;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: background 0.15s;
  }
  #tour-close-x:hover { background: rgba(255,255,255,0.28); }

  /* Progress bar */
  #tour-progress-wrap {
    height: 3px;
    background: rgba(255,255,255,0.08);
  }
  #tour-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #ff6b6b, #D2051E);
    transition: width 0.4s ease;
  }

  /* Body */
  #tour-body {
    padding: 28px 26px 20px;
  }
  #tour-step-badge {
    display: inline-block;
    background: rgba(210,5,30,0.18);
    border: 1px solid rgba(210,5,30,0.4);
    color: #ff6b6b;
    font-size: 0.7rem; font-weight: 700;
    letter-spacing: 1.2px; text-transform: uppercase;
    border-radius: 20px;
    padding: 3px 10px;
    margin-bottom: 12px;
  }
  #tour-desc {
    color: rgba(255,255,255,0.90);
    font-size: 0.97rem;
    line-height: 1.65;
    min-height: 80px;
  }
  #tour-tip {
    margin-top: 14px;
    background: rgba(255,255,255,0.04);
    border-left: 3px solid rgba(210,5,30,0.6);
    border-radius: 0 8px 8px 0;
    padding: 9px 14px;
    color: rgba(255,255,255,0.60);
    font-size: 0.82rem;
    line-height: 1.5;
    display: none;
  }

  /* Dot indicators */
  #tour-dots {
    display: flex; justify-content: center; gap: 6px;
    padding: 4px 26px 0;
    flex-wrap: wrap;
  }
  .tour-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: rgba(255,255,255,0.18);
    transition: background 0.25s, transform 0.25s;
    cursor: pointer;
  }
  .tour-dot.active {
    background: #D2051E;
    transform: scale(1.4);
  }
  .tour-dot.done {
    background: rgba(210,5,30,0.45);
  }

  /* Footer buttons */
  #tour-footer {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 26px 22px;
    gap: 12px;
  }
  #tour-skip-btn {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.5);
    border-radius: 10px;
    padding: 9px 18px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.18s;
    font-family: inherit;
  }
  #tour-skip-btn:hover {
    border-color: rgba(255,255,255,0.35);
    color: rgba(255,255,255,0.8);
  }
  #tour-nav { display: flex; gap: 10px; align-items: center; }
  #tour-prev-btn {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    color: rgba(255,255,255,0.65);
    border-radius: 10px;
    padding: 9px 16px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.18s;
    font-family: inherit;
  }
  #tour-prev-btn:hover:not(:disabled) {
    background: rgba(255,255,255,0.12);
    color: #fff;
  }
  #tour-prev-btn:disabled { opacity: 0.28; cursor: default; }
  #tour-next-btn {
    background: linear-gradient(135deg, #D2051E 0%, #8B0012 100%);
    border: none;
    color: #fff;
    border-radius: 10px;
    padding: 9px 22px;
    font-size: 0.88rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(210,5,30,0.4);
    transition: all 0.18s;
    font-family: inherit;
    min-width: 100px;
  }
  #tour-next-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(210,5,30,0.55);
  }
  #tour-step-count {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.4);
    min-width: 48px;
    text-align: center;
  }
</style>
</head>
<body>

<!-- Floating Help Button -->
<button id="hilti-help-btn" onclick="startTour()" title="Open Guided Tour">?</button>

<!-- Backdrop -->
<div id="tour-backdrop" onclick="closeTour()"></div>

<!-- Tour Card -->
<div id="tour-card">
  <div id="tour-header">
    <div id="tour-header-left">
      <div id="tour-step-icon">🗺️</div>
      <div>
        <div id="tour-title">Platform Tour</div>
        <div id="tour-subtitle">Hilti Project Prioritization</div>
      </div>
    </div>
    <button id="tour-close-x" onclick="closeTour()">✕</button>
  </div>
  <div id="tour-progress-wrap">
    <div id="tour-progress-bar" style="width:0%"></div>
  </div>
  <div id="tour-body">
    <div id="tour-step-badge">Step 1</div>
    <div id="tour-desc"></div>
    <div id="tour-tip"></div>
  </div>
  <div id="tour-dots"></div>
  <div id="tour-footer">
    <button id="tour-skip-btn" onclick="closeTour()">Skip Tour</button>
    <div id="tour-nav">
      <span id="tour-step-count">1 / 12</span>
      <button id="tour-prev-btn" onclick="prevStep()">← Prev</button>
      <button id="tour-next-btn" onclick="nextStep()">Next →</button>
    </div>
  </div>
</div>

<script>
const STEPS = [
  {
    icon: "👋",
    title: "Welcome to the Platform",
    badge: "Introduction",
    desc: `<b>Welcome to the Hilti Project Prioritization Tool!</b><br><br>
This platform helps you evaluate, rank, and schedule your innovation portfolio based on financial return, break-even speed, and strategic alignment.<br><br>
This short tour will walk you through every section so you can get the most out of the tool.`,
    tip: "💡 You can press <b>Next</b> to advance, <b>Prev</b> to go back, or click any dot below to jump to a section."
  },
  {
    icon: "🧭",
    title: "Sidebar Navigation",
    badge: "Navigation",
    desc: `The <b>sidebar on the left</b> is your main navigation hub. It contains:<br><br>
<b>• Logo Panel</b> — Co-branding area with Hilti and Liechtenstein logos.<br>
<b>• Navigation Radio Buttons</b> — Click any page name to instantly switch views. The active page is highlighted with a red accent bar.<br><br>
All 9 platform pages are reachable from here without any page reload.`,
    tip: "💡 The navigation is persistent — your weights and settings stay intact when switching pages."
  },
  {
    icon: "⚙️",
    title: "Controls & Parameters",
    badge: "Sidebar Expander",
    desc: `Below navigation you'll find the <b>⚙️ Controls & Parameters</b> collapsible panel. Inside it:<br><br>
<b>• Scoring Weights</b> — Adjust how much total net profit vs. break-even speed influences the composite rank.<br>
<b>• Prioritization Algorithm</b> — Choose between Capital Velocity, Value Creation Rating, or ROI scoring methods.<br>
<b>• Cost Buffer</b> — Apply a contingency % on top of every project's cost.<br>
<b>• Execution Constraints</b> — Set total budget, monthly spend caps, and concurrency limits.<br>
<b>• Portfolio Generator</b> — Regenerate sample data with a custom seed, project count, and optional duration range (e.g. 1-4 month short-project portfolios).`,
    tip: "💡 All controls update every chart and table <b>live</b> on the same run — no page reload needed."
  },
  {
    icon: "📊",
    title: "Portfolio Overview",
    badge: "Page 1",
    desc: `The <b>Portfolio Overview</b> page is your command centre. It shows:<br><br>
<b>• Top KPI Bar</b> — Selected projects count, total business value, total cost, and cumulative net profit.<br>
<b>• Bubble Chart</b> — Scatter of cost vs. business value; bubble size = project duration.<br>
<b>• Ranked Table</b> — All projects sorted by composite score with filter controls for archetype, duration, and net profit range.<br>
<b>• CSV Export</b> — Download the filtered portfolio as a CSV file.`,
    tip: "💡 Toggle <b>Show selected projects only</b> to isolate projects approved by the budget scheduler."
  },
  {
    icon: "🔍",
    title: "Project Details",
    badge: "Page 2",
    desc: `The <b>Project Details</b> page lets you deep-dive into individual projects:<br><br>
<b>• Multi-select picker</b> — Choose one or more projects by rank and name.<br>
<b>• Time-series chart</b> — Plot cumulative net profit, monthly business value, cost, effort, or FTE count over the project lifetime.<br>
<b>• Summary table</b> — Side-by-side comparison of the selected projects' KPIs.<br>
<b>• Composition charts</b> — Donut and bar charts showing archetype distribution and budget breakdown across the selected portfolio.`,
    tip: "💡 Select up to all projects to see the full portfolio time-series on a single chart."
  },
  {
    icon: "🎲",
    title: "Robustness Simulation",
    badge: "Page 3",
    desc: `The <b>Robustness Simulation</b> page stress-tests the portfolio under uncertainty:<br><br>
<b>• Monte Carlo simulation</b> — Simulates thousands of outcomes for the whole portfolio (or a single project) under value and cost uncertainty, showing the distribution of net profit and the probability of loss.<br>
<b>• Rank stability</b> — Re-ranks the portfolio many times under noise and measures how reliably the top projects keep their position (rank correlation and Top-N retention).`,
    tip: "💡 A project that stays in the top 10 across 90%+ of simulations is a <b>safe bet</b> to prioritize."
  },
  {
    icon: "🗓️",
    title: "Execution Strategy",
    badge: "Page 4",
    desc: `The <b>Execution Strategy</b> page shows how your approved portfolio plays out over time:<br><br>
<b>• Global timeline chart</b> — Cumulative net profit curve across the entire portfolio lifecycle.<br>
<b>• Gantt-style schedule</b> — Visual lane chart of project start/end dates under sequential or parallel execution.<br>
<b>• Budget & concurrency enforcement</b> — The scheduler automatically enforces the limits you set in the sidebar controls.`,
    tip: "💡 Switch between <b>Sequential</b> and <b>Parallel</b> execution modes in the sidebar to see how scheduling changes the timeline."
  },
  {
    icon: "🤝",
    title: "Department Alignment",
    badge: "Page 5",
    desc: `The <b>Department Alignment</b> page enables cross-functional review and scoring:<br><br>
<b>• Department scores</b> — Finance, IT/R&D, Sales/Marketing, and Operations each rate projects 1–10.<br>
<b>• Comment threads</b> — Each department can leave timestamped notes for collaborative decision-making.<br>
<b>• Alignment heatmap</b> — Visual overview showing which projects have strong or weak cross-departmental buy-in.<br>
<b>• Score aggregation</b> — Average departmental alignment score is computed and displayed per project.`,
    tip: "💡 Projects with high financial scores but low departmental alignment may face <b>execution risk</b>."
  },
  {
    icon: "➕",
    title: "Add Project",
    badge: "Page 6",
    desc: `The <b>Add Project</b> page lets you submit new projects for evaluation in two modes:<br><br>
<b>• High-Level Mode</b> — Enter totals and choose a value-curve shape (S-Curve, Linear Ramp, etc.). The system spreads values across months automatically.<br>
<b>• Detailed Mode</b> — Enter precise monthly business value, direct cost, and FTE count in an editable table.<br>
<b>• Live Preview</b> — See the cumulative net profit curve update as you fill in data.<br>
<br>New projects are immediately ranked against the existing portfolio upon submission.`,
    tip: "💡 The <b>Archetype</b> selector in High-Level mode pre-fills sensible defaults based on historical project patterns."
  },
  {
    icon: "🤖",
    title: "Copilot Assistant",
    badge: "Page 7",
    desc: `The <b>Copilot</b> page is your AI-powered portfolio assistant:<br><br>
<b>• Natural language queries</b> — Ask questions like <em>"Compare P-0001 and P-0002"</em> or <em>"What if the budget is 25M CHF?"</em><br>
<b>• Budget simulation</b> — The copilot re-runs the scheduler with your stated limit and reports impacts.<br>
<b>• Top project summaries</b> — Ask for the best-ranked projects and get an instant formatted report.<br>
<b>• Archetype analysis</b> — Query cost distributions by project category.`,
    tip: "💡 Try typing <em>"What is the total profit?"</em> or <em>"Limit budget to 10M"</em> to see the copilot in action."
  },
  {
    icon: "📖",
    title: "User Guide",
    badge: "Page 8",
    desc: `The <b>User Guide</b> page contains full platform documentation:<br><br>
<b>• Scoring methodology</b> — Explains the Capital Velocity, Value Creation Rating, and ROI methods in detail.<br>
<b>• KPI definitions</b> — Glossary of all metrics (Net Profit, Business Value, FTE, Break-Even, etc.).<br>
<b>• How-to guides</b> — Step-by-step instructions for common tasks like adding projects and adjusting weights.<br>
<b>• FAQ section</b> — Answers to the most common questions about the platform.`,
    tip: "💡 Bookmark the User Guide page for quick reference during stakeholder presentations."
  },
  {
    icon: "🚀",
    title: "You're All Set!",
    badge: "Complete",
    desc: `You've completed the platform tour! Here's a quick summary of what you can do:<br><br>
<b>1.</b> Explore your portfolio on <b>Portfolio Overview</b><br>
<b>2.</b> Deep-dive into projects on <b>Project Details</b><br>
<b>3.</b> Stress-test assumptions in <b>Robustness Simulation</b><br>
<b>4.</b> Visualize execution on <b>Execution Strategy</b><br>
<b>5.</b> Collaborate cross-functionally in <b>Department Alignment</b><br>
<b>6.</b> Submit new ideas via <b>Add Project</b><br>
<b>7.</b> Query insights through the <b>Copilot</b><br><br>
<b>Click the ❓ button anytime to restart this tour.</b>`,
    tip: null
  }
];

let currentStep = 0;

function renderDots() {
  const wrap = document.getElementById('tour-dots');
  wrap.innerHTML = '';
  STEPS.forEach((_, i) => {
    const dot = document.createElement('div');
    dot.className = 'tour-dot' + (i === currentStep ? ' active' : (i < currentStep ? ' done' : ''));
    dot.onclick = () => goToStep(i);
    wrap.appendChild(dot);
  });
}

function goToStep(n) {
  currentStep = n;
  updateCard();
}

function updateCard() {
  const step = STEPS[currentStep];
  const total = STEPS.length;

  document.getElementById('tour-step-icon').textContent = step.icon;
  document.getElementById('tour-title').textContent = step.title;
  document.getElementById('tour-step-badge').textContent = 'Step ' + (currentStep + 1) + ' — ' + step.badge;
  document.getElementById('tour-desc').innerHTML = step.desc;

  const tipEl = document.getElementById('tour-tip');
  if (step.tip) {
    tipEl.innerHTML = step.tip;
    tipEl.style.display = 'block';
  } else {
    tipEl.style.display = 'none';
  }

  const pct = ((currentStep) / (total - 1)) * 100;
  document.getElementById('tour-progress-bar').style.width = pct + '%';

  document.getElementById('tour-step-count').textContent = (currentStep + 1) + ' / ' + total;

  const prevBtn = document.getElementById('tour-prev-btn');
  const nextBtn = document.getElementById('tour-next-btn');
  prevBtn.disabled = currentStep === 0;
  nextBtn.textContent = currentStep === total - 1 ? 'Finish ✓' : 'Next →';

  renderDots();

  // Animate card re-entry
  const card = document.getElementById('tour-card');
  card.classList.remove('visible');
  setTimeout(() => card.classList.add('visible'), 30);
}

function nextStep() {
  if (currentStep < STEPS.length - 1) {
    currentStep++;
    updateCard();
  } else {
    closeTour();
  }
}

function prevStep() {
  if (currentStep > 0) {
    currentStep--;
    updateCard();
  }
}

function startTour() {
  currentStep = 0;
  document.getElementById('tour-backdrop').style.display = 'block';
  const card = document.getElementById('tour-card');
  card.style.display = 'block';
  setTimeout(() => {
    card.classList.add('visible');
    updateCard();
  }, 20);
}

function closeTour() {
  const card = document.getElementById('tour-card');
  const backdrop = document.getElementById('tour-backdrop');
  card.classList.remove('visible');
  setTimeout(() => {
    backdrop.style.display = 'none';
    card.style.display = 'none';
  }, 280);
}

// Keyboard navigation
document.addEventListener('keydown', function(e) {
  const card = document.getElementById('tour-card');
  if (card.style.display === 'none' || !card.style.display) return;
  if (e.key === 'ArrowRight' || e.key === 'Enter') nextStep();
  if (e.key === 'ArrowLeft') prevStep();
  if (e.key === 'Escape') closeTour();
});

// ── Hoist elements into the parent Streamlit document ─────────────────
(function hoistToParent() {
  try {
    const parentDoc = window.parent.document;
    if (!parentDoc) return;

    // Remove any previously hoisted tour elements (idempotent on reruns)
    ['hilti-help-btn','tour-backdrop','tour-card','__tour-styles__'].forEach(id => {
      const old = parentDoc.getElementById(id);
      if (old) old.remove();
    });

    // Clone styles
    const style = document.createElement('style');
    style.id = '__tour-styles__';
    style.textContent = Array.from(document.styleSheets)
      .map(s => { try { return Array.from(s.cssRules).map(r => r.cssText).join('\\n'); } catch(e){ return ''; } })
      .join('\\n');
    parentDoc.head.appendChild(style);

    // Clone DOM nodes
    ['hilti-help-btn','tour-backdrop','tour-card'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        const clone = el.cloneNode(true);
        parentDoc.body.appendChild(clone);
      }
    });

    // Re-bind all interactive functions in parent context
    const script = parentDoc.createElement('script');
    script.textContent = `
      (function() {
        const STEPS = ${JSON.stringify(STEPS)};
        let currentStep = 0;

        function renderDots() {
          const wrap = document.getElementById('tour-dots');
          if (!wrap) return;
          wrap.innerHTML = '';
          STEPS.forEach((_, i) => {
            const dot = document.createElement('div');
            dot.className = 'tour-dot' + (i === currentStep ? ' active' : (i < currentStep ? ' done' : ''));
            dot.onclick = () => goToStep(i);
            wrap.appendChild(dot);
          });
        }

        function goToStep(n) { currentStep = n; updateCard(); }

        function updateCard() {
          const step = STEPS[currentStep];
          const total = STEPS.length;
          const icon = document.getElementById('tour-step-icon');
          const title = document.getElementById('tour-title');
          const badge = document.getElementById('tour-step-badge');
          const desc = document.getElementById('tour-desc');
          const tipEl = document.getElementById('tour-tip');
          const bar = document.getElementById('tour-progress-bar');
          const count = document.getElementById('tour-step-count');
          const prevBtn = document.getElementById('tour-prev-btn');
          const nextBtn = document.getElementById('tour-next-btn');
          if (!icon) return;
          icon.textContent = step.icon;
          title.textContent = step.title;
          badge.textContent = 'Step ' + (currentStep+1) + ' — ' + step.badge;
          desc.innerHTML = step.desc;
          if (step.tip) { tipEl.innerHTML = step.tip; tipEl.style.display = 'block'; }
          else { tipEl.style.display = 'none'; }
          const pct = ((currentStep) / (total - 1)) * 100;
          bar.style.width = pct + '%';
          count.textContent = (currentStep+1) + ' / ' + total;
          prevBtn.disabled = currentStep === 0;
          nextBtn.textContent = currentStep === total - 1 ? 'Finish ✓' : 'Next →';
          renderDots();
          const card = document.getElementById('tour-card');
          card.classList.remove('visible');
          setTimeout(() => card.classList.add('visible'), 30);
        }

        window.__tourNext = function() {
          if (currentStep < STEPS.length - 1) { currentStep++; updateCard(); }
          else { window.__tourClose(); }
        };
        window.__tourPrev = function() {
          if (currentStep > 0) { currentStep--; updateCard(); }
        };
        window.__tourClose = function() {
          const card = document.getElementById('tour-card');
          const bd = document.getElementById('tour-backdrop');
          if (card) card.classList.remove('visible');
          setTimeout(() => {
            if (bd) bd.style.display = 'none';
            if (card) card.style.display = 'none';
          }, 280);
        };
        window.__tourStart = function() {
          currentStep = 0;
          const bd = document.getElementById('tour-backdrop');
          const card = document.getElementById('tour-card');
          if (bd) bd.style.display = 'block';
          if (card) { card.style.display = 'block'; }
          setTimeout(() => {
            if (card) card.classList.add('visible');
            updateCard();
          }, 20);
        };

        // Wire button onclick
        const helpBtn = document.getElementById('hilti-help-btn');
        if (helpBtn) helpBtn.onclick = window.__tourStart;
        const bd2 = document.getElementById('tour-backdrop');
        if (bd2) bd2.onclick = window.__tourClose;
        const cx = document.getElementById('tour-close-x');
        if (cx) cx.onclick = window.__tourClose;
        const skipBtn = document.getElementById('tour-skip-btn');
        if (skipBtn) skipBtn.onclick = window.__tourClose;
        const nextBtn2 = document.getElementById('tour-next-btn');
        if (nextBtn2) nextBtn2.onclick = window.__tourNext;
        const prevBtn2 = document.getElementById('tour-prev-btn');
        if (prevBtn2) prevBtn2.onclick = window.__tourPrev;

        // Keyboard
        document.addEventListener('keydown', function(e) {
          const card = document.getElementById('tour-card');
          if (!card || card.style.display === 'none' || !card.style.display) return;
          if (e.key === 'ArrowRight' || e.key === 'Enter') window.__tourNext();
          if (e.key === 'ArrowLeft') window.__tourPrev();
          if (e.key === 'Escape') window.__tourClose();
        });
      })();
    `;
    parentDoc.body.appendChild(script);
  } catch(err) {
    console.warn('Tour hoist error:', err);
  }
})();
</script>
</body>
</html>
''', height=0, width=0)
