# 🔧 Hilti Project Prioritization & Optimization Platform

Welcome to the **Hilti Project Prioritization & Optimization Platform**. This cockpit provides strategic portfolio governance, interactive side-by-side simulations, cross-departmental alignment, and on-demand AI consulting to optimize resource allocation and maximize net profit.

## ✨ Key Features

- **📊 Portfolio Overview**: The prioritized portfolio at a glance — a "Cumulative Net Profit over Time" ranking chart, four portfolio KPIs, and a filterable projects table.
- **📈 Project Details**: Plot any KPI (cumulative / discounted net profit, business value, costs, FTE count) per project, plus archetype and break-even composition charts.
- **🎲 Robustness Simulation**: Monte Carlo on the whole portfolio or a single project (P10 / P50 / P90, probability of loss) plus rank-stability analysis (Spearman correlation, Top-N retention).
- **🗓️ Execution Strategy**: Compare the three prioritization methods and a capital-recycling simulation, plus *Sequential* vs. *Parallel* execution under budget, monthly-spend and concurrency limits.
- **🤝 Department Alignment**: A fact-based Organization Alignment Score (OAS) and radar, plus a collaborative review/discussion workspace and a stakeholder report export.
- **🤖 Copilot**: A 100% local, rule-based assistant — compare projects, explain ranking drivers, or run natural-language what-if budget simulations (e.g., *"What if budget is 20,000,000 CHF?"*).
- **➕ Add Project**: Add a detailed monthly business case, or high-level estimates auto-spread into a realistic monthly profile via archetype value curves.

## 🚀 Getting Started

### Prerequisites

Ensure you have Python installed (3.9+ recommended).

### Installation

1. **Clone the repository** (or download the files).
2. **Set up a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   
   # Windows
   .\.venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```
3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

Start the Streamlit server locally:
```bash
streamlit run app.py
```
Your default web browser will automatically open the dashboard (usually at `http://localhost:8501`).

## 🛠️ Tech Stack

- **Frontend / Application Framework**: [Streamlit](https://streamlit.io/)
- **Data Manipulation & Logic**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Visualizations**: [Plotly](https://plotly.com/python/)
- **Formatting Utilities**: Tabulate

## 🧮 Prioritization Methodologies

All three rank by "profit per unit of a scarce resource"; the denominator sets the bottleneck:

- **Capital Velocity** (default): discounted net profit per CHF invested — a time-aware ROI tuned by a reinvestment rate (`Σ NPₜ/(1+r)ᵗ / Total Cost`). At 0% it equals plain ROI.
- **Value Creation Rating**: net profit per month of duration (`Net Profit / Duration`).
- **ROI (Return on Investment)**: net profit per franc invested (`Total Net Profit / Total Cost`).

---
*Built for the Hilti Innovation Lab.*
