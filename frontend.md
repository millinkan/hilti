# Frontend Guide - Hilti Portfolio Optimization Cockpit

Web app for evaluating, simulating, and prioritizing a portfolio of projects. Built with [Streamlit](https://streamlit.io/) — a Python framework that turns plain Python scripts into interactive, ultra-premium web pages styled with glassmorphism layouts, Montserrat typography, and corporate red (`#D2051E`) accents.

## Launch

From the project root:

```bash
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

The app opens automatically in your browser at `http://localhost:8501`. On the very first run, it bootstraps a sample portfolio of 100 projects.

---

## Page Layout & Navigation

A left **sidebar** carries the co-branded logos, the **page navigation** (a radio list), and the collapsible **Controls & Parameters** panel. The main area shows a brand header, the four portfolio KPIs (always visible), and the active page:

```
┌──────────────┬──────────────────────────────────────────────┐
│  Sidebar     │  Project Prioritization Prototype  ·  <Page>  │
│  • Logos     │  ┌─────────┬────────────┬──────────┬────────┐ │
│  • Navigation│  │Selected │ Total Value│Total Cost│Cum. NP │ │ ← KPIs (always visible)
│  • Controls &│  └─────────┴────────────┴──────────┴────────┘ │
│    Parameters│                                               │
│              │  [active page content]                        │
└──────────────┴──────────────────────────────────────────────┘
```

**Pages:** Portfolio Overview · Project Details · Robustness Simulation · Execution Strategy · Department Alignment · Add Project · Copilot · User Guide.

---

## Sidebar Controls (Parameter Center)

The collapsible **Controls & Parameters** panel drives every page:

- **Reinvestment Rate** (0–60 %/yr): sets how strongly Capital Velocity rewards fast payback (0 % = plain ROI).
- **Prioritization Algorithm**: choose the ranking method —
  - **Capital Velocity**: discounted Net Profit / Cost (rewards fast payback, via the reinvestment rate).
  - **Value Creation Rating**: Net Profit / Duration.
  - **ROI**: Net Profit / Cost.
- **Estimation Cost Buffer** (0–10 %): a contingency added on top of every project's cost.
- **Budget**: a Total Budget limit and an optional Max Monthly Spend limit (drive the scheduler / funded selection).
- **Execution Plan**: Sequential vs. Parallel execution, plus an optional Max parallel projects cap.
- **Portfolio Generator**: regenerate the sample portfolio from a chosen seed and project count, optionally forcing a custom project-duration range.

---

## Pages

### 📊 Portfolio Overview
- **Ranking — Cumulative Net Profit over Time**: one line per top-N ranked project; circled rank badge, solid = funded / dashed = not funded, dashed zero line = break-even.
- **Prioritized projects table**: rank, funded flag (✅/❌), ID, name, archetype, duration, business value, total cost, net profit, break-even (filterable by archetype/duration/net profit; CSV export).

### 📈 Project Details
- **Project KPIs over time**: plot any metric — cumulative / discounted-cumulative / monthly net profit, monthly business value, monthly cost, direct cost, effort cost, FTE count — for one or more selected projects.
- **Portfolio composition**: archetype donut + break-even-month histogram of the funded portfolio.

### 🎲 Robustness Simulation
- **Monte Carlo**: perturbs monthly value & cost to produce a net-profit distribution (P10 / P50 / P90, probability of loss) for the whole portfolio or a single project.
- **Rank Stability**: re-ranks under noise → Spearman rank correlation and Top-N retention, with a per-project rank-range plot.

### 🗓️ Execution Strategy
- **Capital over Time with Reinvestment**: capital-recycling comparison of the three methods.
- **Sequential vs. Parallel**: time-to-completion, cumulative net-profit growth, FTE/spend utilisation, and a Gantt timeline ordered by priority rank.

### 🤝 Department Alignment
- **Fact-based OAS + radar**: department scores computed from the funded portfolio's KPIs (not opinions).
- **Collaboration Workspace**: subjective buy-in reviews and a colour-coded discussion log, plus a downloadable stakeholder report.

### ➕ Add Project
- **Detailed mode**: enter monthly business value, direct cost and FTE count; the tool derives the rest.
- **High-level mode**: enter totals; the value is spread across the months by a chosen/auto value-curve shape.

### 💬 Copilot
- A 100 % local, rule-based assistant: compare projects, run what-if budget scenarios, and explain ranking drivers — nothing leaves the tool.

### 📖 User Guide
- In-app documentation of the logic, formulas and visualisations behind every page.
