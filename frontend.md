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

Every screen shares the same responsive shell:

```
┌─────────────────────────────────────────────────────────────┐
│  Title + brand caption                                      │
│  ┌───────────┬──────────────┬────────────┬──────────────┐   │
│  │ Selected  │ Total Value  │ Total Cost │ Cumulative NP│   │ ← Selected portfolio KPIs (always visible)
│  └───────────┴──────────────┴────────────┴──────────────┘   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Tabs: Dash | Rank | Details | Risk | Sim | AI | Hub   │  │ ← Executive Navigation
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [active tab content with smooth slide-up fade-in effects]  │
└─────────────────────────────────────────────────────────────┘
```

A **Sidebar** on the left contains weights and optimization controls.

---

## Sidebar Controls

### 🚀 Scoring Weights & Prioritization
- **Weight: Total Net Profit**: Primary signal (0.0 to 1.0) governing return-on-investment size.
- **Weight: Break-Even Speed**: Tiebreaker speed score weight.
- **Prioritization Algorithm**: Select between:
  - **Composite**: Weighted combination of normalized Net Profit and Speed Score.
  - **Hilti Value Creation Rating**: Hilti's official formula. Ranks by `Net Profit / Duration`.
  - **ROI (Return on Investment)**: Ranks by `Net Profit / Cost`.

### 🎛️ Prototype Phase 2 & 3 Optimization Constraints
- **Execution Mode**: Choose **Sequential** (one after another) or **Parallel** (overlapping timelines).
- **Total Budget Limit**: Cap total expenditure.
- **Max Monthly Spend Limit**: Limit concurrent monthly expenditures to prevent cash-flow strain.
- **Max Concurrent Projects**: Cap simultaneous active project timelines.

---

## Executive Tabs

### 📊 Dashboard
Displays a high-level summary of the currently **selected** optimized portfolio:
- **Archetype Pie Chart**: A clean red-gradient donut distribution of projects by business area.
- **Break-Even Distribution**: Histogram plotting when projects reach profitability.
- **Cost vs. Value Bubble Plot**: Displays direct cost on the x-axis, business value on the y-axis, and project duration as bubble size. Includes a diagonal parity line for instant break-even visual inspection.

### 📋 Ranking
The master prioritized table:
- **Selection Status Indicator (✅/❌)**: Displays if a project fits within the current optimization limits.
- **Checkbox Filter**: Switch on `"Show selected projects only"` to isolate scheduled projects.
- **Flexible Filters**: Sliders for duration, net profit, and archetype selectors.

### 📈 Project Details
Inspect individual timelines:
- **Timeseries Charts**: Select multiple projects to plot cumulative/monthly profits, monthly business value, total cost, or active FTE headcounts.
- **Executive Summaries**: Slide-up tables repeating financial properties.
- **Stakeholder Report Generator**: Downloadable sharing summaries.

### 🎲 Risk (Monte Carlo Simulation)
Stress-test individual projects against economic shocks:
- **Gaussian Noise Engine**: Runs thousands of simulations with random volatility applied to costs and values.
- **Confidence Intervals**: Displays P10 (worst case), P50 (expected), and P90 (best case) profit curves.
- **Probability of Loss**: Renders a gauge displaying the statistical chance the project fails to break even.

### 🕹️ Scenario Simulation
Run sequential vs. parallel portfolio timelines side-by-side:
- **Scenario Metrics Grid**: Compares completion times, costs, net profit yields, and return-on-investments.
- **Trajectory Charts**: Dual lines showing cumulative profit growth, FTE utilization concurrency, and a horizontal budget limit line mapping expenditures over time.

### 💬 AI Portfolio Copilot (Phase 3)
A 100% local, zero-API natural language portfolio consultant:
- **Comparison Engine**: Type `"Compare P-0001 and P-0002"` to render side-by-side metric sheets.
- **What-If Constraint Sandbox**: Type `"What if we limit budget to 15M CHF?"` to programmatically run scheduling simulations and output dropped vs. kept lists.
- **Corporate Advisory Notes**: Provides automated consulting insights based on composite scoring logic.

### 🤝 Interdepartmental Alignment Hub (Phase 3)
A collaborative, cross-functional workspace tracking corporate consensus:
- **Organizational Alignment Score (OAS)**: Aggregates real-time ratings (Finance, IT, Sales, Operations) across selected projects.
- **Consensus Radar Chart**: Custom Plotly polar visualization showing departmental buy-in.
- **Feedback Forms**: Real-time review submissions saving rating points and timestamps directly to the JSON store.
- **Chronological Discussion Log**: Beautifully formatted chat bubble threads sorted by department.

### 📖 User Guide
A formal methodology manual featuring LaTeX equations for algorithms and active resource optimization math.
