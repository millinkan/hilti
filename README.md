# 🔧 Hilti Project Prioritization & Optimization Platform

Welcome to the **Hilti Project Prioritization & Optimization Platform**. This cockpit provides strategic portfolio governance, interactive side-by-side simulations, cross-departmental alignment, and on-demand AI consulting to optimize resource allocation and maximize net profit.

## ✨ Key Features

- **📊 Executive Dashboard**: High-level overview of portfolio KPIs (Cumulative Net Profit, Break-Even distributions, Cost vs. Value analysis).
- **📋 Dynamic Ranking Engine**: Prioritize projects on the fly using multiple methodologies (Composite, WSJF, ROI).
- **🕹️ Scenario Simulation**: Compare *Sequential* vs. *Parallel* execution modes. Apply total budget limits, monthly spending caps, and resource concurrency constraints.
- **🎲 Monte Carlo Risk Analysis**: Run thousands of simulations to identify P10 (Worst Case), P50 (Expected), and P90 (Best Case) outcomes for individual projects.
- **🤝 Interdepartmental Hub**: Foster transparency across Finance, IT, Sales, and Operations. Track Organization Alignment Scores (OAS) and resolve cross-functional blockers.
- **🤖 AI Portfolio Copilot**: Built-in chatbot for immediate insights. Compare projects instantly or run natural language what-if budget simulations (e.g., *"What if budget is 54,000,000 CHF?"*).
- **➕ Project Generation**: Easily add detailed monthly business cases or use high-level archetype estimates to auto-generate project curves.

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

- **Composite Score**: Blends financial yield and time-to-value speed (`w_profit * NP + w_speed * Speed Factor`).
- **WSJF (Weighted Shortest Job First)**: Prioritizes high-value, fast-turnaround projects (`Business Value / Duration`).
- **ROI (Return on Investment)**: Ranks projects based on financial cost-efficiency (`Total Net Profit / Total Cost`).

---
*Built for the Hilti Innovation Lab.*
