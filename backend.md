# Backend Guide - Hilti Portfolio Optimization Engine

This document explains the numbers, formulas, constraints, and scheduling algorithms powering the app. The backend is designed for high-performance and lightweight execution: written in clean Python modules utilizing NumPy and Pandas, with local files on disk serving as the source of truth.

| File | Purpose |
|---|---|
| `models.py` | Project data model + KPI math + CSV persistence layer |
| `data_generator.py` | Generates a realistic sample portfolio calibrated to Hilti's scale |
| `prioritization.py` | Scoring algorithms (Capital Velocity, Value Creation Rating, ROI) + scheduler + reinvestment & robustness simulations |
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

All three methods follow the same pattern — **profit per unit of a scarce resource**; the denominator reveals the bottleneck the method optimises for. In every case **Net Profit (NP) = Business Value − Costs = Business Value − (Direct Cost + Effort)**.

### A. Capital Velocity (Default) — bottleneck: capital + time
Discounted net profit **per CHF invested** — a time-aware ROI that rewards fast payback, because money returned sooner can be reinvested into the next projects sooner:
$$\text{Capital Velocity}[i] = \frac{\sum_{t=1}^{D_i} \text{NP}_i[t] \,/\, (1+r)^{t}}{\text{Total Cost}[i]}, \qquad r = (1+\text{reinvest})^{1/12} - 1$$
Where $\text{NP}_i[t]$ is the project's **real monthly net profit** (not an average) and $r$ is the monthly rate derived from the **Reinvestment rate** slider (default 30 %/yr). At reinvest = 0 % Capital Velocity reduces **exactly to ROI**; a higher rate increasingly rewards early payback. It is therefore a tunable generalisation of ROI that also accounts for the timing of cash returns.

The **Execution Strategy** page visualises this with a capital-recycling simulation (`simulate_reinvestment`): the Total Budget is treated as the **starting capital of a revolving pool** — project returns flow back monthly and fund the next projects, so the ranking that frees capital fastest compounds fastest.

### B. Value Creation Rating — bottleneck: time / execution capacity
Net profit per unit of time (an alias `WSJF` is still accepted internally for backward compatibility). Costs are subtracted in the numerator but **not** normalised in the denominator, so it is "capital-binding-blind" and assumes an even profit distribution over the duration:
$$\text{Value Creation Rating}[i] = \frac{\text{Net Profit}[i]}{\text{Duration}[i]} = \frac{\text{Business Value}[i] - \text{Costs}[i]}{\text{Duration}[i]}$$

### C. ROI (Return on Investment) — bottleneck: capital
Ranks projects based on cost-efficiency (blind to *when* the return arrives):
$$\text{ROI}[i] = \frac{\text{Total Net Profit}[i]}{\text{Total Cost}[i]}$$

### D. Estimation Cost Buffer
A global contingency set by a sidebar slider (0–10 %) is applied on top of every project's cost before scoring and scheduling, via `models.apply_cost_buffer`:
$$\text{Effective Cost} = \text{Total Cost} \times (1 + \text{buffer})$$
It flows through into net profit, break-even, the ranking and the scheduler.

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

## 4. Risk & Robustness Simulations (`prioritization.py`)

Two Monte-Carlo simulations stress-test the result under estimation uncertainty:

- **`simulate_portfolio_profit`** — perturbs each project's monthly business value and cost by multiplicative Gaussian noise ($\varepsilon \sim \mathcal{N}(1,\sigma)$) over many iterations and returns the distribution of total net profit: P10 / P50 / P90 and the **probability of loss** (share of iterations below 0).
- **`simulate_rank_stability`** — applies the same noise but **re-ranks** the portfolio every iteration, returning the average **Spearman rank correlation** vs. the baseline ranking and the **Top-N retention** (share of the baseline Top-N that stays in the Top-N).

---

## 5. Department Alignment — fact-based OAS

The Organizational Alignment Score and radar are computed from the **funded portfolio's objective KPIs, not from opinions**. Each department scores 0–10: **Finance** = portfolio ROI (capped at 10); **IT/R&D, Sales/Marketing, Operations** = the share of funded business value in that department's archetypes. The **OAS** is the average of the four. (Thresholds: ≥ 7 well balanced, ≥ 4 moderately balanced, otherwise heavily concentrated.)

---

## 6. Collaborative Reviews Storage

Separately, the **subjective** buy-in reviews (the Collaboration Workspace, distinct from the fact-based OAS) are persisted inside `data/department_reviews.json` using the following schema:

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
