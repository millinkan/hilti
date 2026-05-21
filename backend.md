# Backend Guide - Hilti Portfolio Optimization Engine

This document explains the numbers, formulas, constraints, and scheduling algorithms powering the app. The backend is designed for high-performance and lightweight execution: written in clean Python modules utilizing NumPy and Pandas, with local files on disk serving as the source of truth.

| File | Purpose |
|---|---|
| `models.py` | Project data model + KPI math + CSV persistence layer |
| `data_generator.py` | Generates a realistic sample portfolio calibrated to Hilti's scale |
| `prioritization.py` | Scoring algorithms (Composite, WSJF, ROI) + Multi-Constraint Scheduler |
| `data/projects_meta.csv` | Project static metadata |
| `data/projects_monthly.csv` | Monthly timeseries values (Direct Cost, FTE Count, Business Value) |
| `data/department_reviews.json` | Cross-departmental reviews and buy-in comments store |

---

## 1. The KPIs

The system follows the project glossary: every project carries **four primary inputs per month**. Everything else is derived from these.

### Primary Inputs (stored on disk)

| Input | Symbol | Unit | Meaning |
|---|---|---|---|
| Direct Cost | `dc[t]` | CHF / month | Money spent on consultants, licenses, infrastructure that month |
| FTE Count | `n[t]` | persons | Full-time-equivalent people on the project that month |
| FTE Cost / Month | `c_fte` | CHF / FTE / month | Loaded cost per FTE per month (one value per project) |
| Business Value | `bv[t]` | CHF / month | Revenue / savings / risk-cost reduction generated that month |

Where `t` runs from `1` to `duration_months`.

### Derived KPIs (computed on the fly)

Implemented as `@property` methods on the `Project` dataclass:

| Derived KPI | Formula |
|---|---|
| **Effort cost** | `effort[t] = n[t] · c_fte` |
| **Monthly cost** | `cost[t] = dc[t] + effort[t]` |
| **Monthly net profit** | `np[t] = bv[t] − cost[t]` |
| **Cumulative net profit** | `cum_np[t] = Σᵢ₌₁ᵗ np[i]` |
| **Total net profit** | `Total_NP = Σ np[t]` over the lifetime |
| **Break-even month** | First `t` where `cum_np[t] ≥ 0`; `None` if never |

---

## 2. Prioritization Algorithms (`prioritization.py`)

Projects are scored and ranked descending based on the user's selected algorithm:

### A. Composite Score (Hilti Default)
Combines normalized lifetime net profit yield and time-to-value speed:
$$\text{composite}[i] = w_{\text{value}} \cdot \text{value\_norm}[i] + w_{\text{speed}} \cdot \text{speed\_score}[i]$$
Where:
- $\text{value\_norm}[i] = \frac{\text{Total\_NP}[i] - \min(\text{Total\_NP})}{\max(\text{Total\_NP}) - \min(\text{Total\_NP})}$
- $\text{speed\_score}[i] = \max(0, 1 - \frac{\text{break\_even\_month}[i] - 1}{\text{duration}[i]})$

### B. WSJF (Weighted Shortest Job First)
Ranks projects to prioritize high-value, fast-turnaround jobs:
$$\text{WSJF}[i] = \frac{\text{Business Value}[i]}{\text{Duration}[i]}$$

### C. ROI (Return on Investment)
Ranks projects based on cost-efficiency:
$$\text{ROI}[i] = \frac{\text{Total Net Profit}[i]}{\text{Total Cost}[i]}$$

---

## 3. Multi-Constraint Portfolio Optimization & Scheduling

The core optimizer `schedule_portfolio()` resolves resource timelines. It supports two execution modes:

### A. Sequential Execution Mode
Projects are placed strictly back-to-back:
$$\text{Start Month}_i = \sum_{j < i} \text{Duration}_j$$
- Budgets are checked cumulatively: if adding project $i$ exceeds the total budget limit, it is skipped.

### B. Parallel Execution Mode
Projects overlap dynamically. The optimizer greedily slots projects down the priority list, sliding each project's start month as early as possible (Month 1, Month 2...) until the following constraints are satisfied for every month $t$ of its execution:
1. **Total Available Budget**:
   $$\sum_{j \in \text{Selected}} \text{Total Cost}_j \le \text{Total Budget}$$
2. **Monthly Spending Limit (Cash-Flow Limit)**:
   $$\text{Monthly Cost}_{i, t - \text{Start}} + \sum_{k \in \text{Active}(t)} \text{Monthly Cost}_{k, t} \le \text{Max Monthly Spending Limit}$$
3. **Concurrency Limit**:
   $$|\text{Active}(t)| \le \text{Max Concurrent Projects}$$

**Infinite Loop Safeguard**: If a project's cost in *any single month* exceeds the `parallel_spending` constraint, it can never be scheduled. The scheduler identifies this upfront and immediately filters out the project to prevent infinite sliding loops.

---

## 4. Collaborative Reviews Storage

Cross-departmental buy-in comments and ratings are persisted inside `data/department_reviews.json` using the following schema:

```json
{
  "P-0001": {
    "scores": {
      "Finance": 8,
      "IT/R&D": 9,
      "Sales/Marketing": 7,
      "Operations": 6
    },
    "comments": [
      {
        "dept": "Finance",
        "user": "Finance Controller",
        "score": 8,
        "text": "Highly profitable Tool R&D project; strong ROI fits criteria.",
        "time": "2026-05-17 14:00"
      }
    ]
  }
}
```

The app handles initialization, read-through loading, and write-through saving dynamically during user reviews submission.
