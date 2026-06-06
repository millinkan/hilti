"""Rank a portfolio of projects by a composite score.

Two components feed the score:

1. Total net profit over the project lifetime.
   - "How much value does this project add to the company?"
   - Min-max normalised across the portfolio so values land in [0, 1].

2. Speed score: how quickly the project starts generating positive value.
   - speed = max(0, 1 - break_even_month / duration_months)
   - 1.0 = breaks even on month 1 (best); 0.0 = never breaks even.
   - Already in [0, 1], no further normalisation needed.

Composite = w_value * value_norm + w_speed * speed
The user controls the two weights from the UI. Defaults 0.75 / 0.25
give clear primacy to total profit while still preferring faster
break-even when two projects have similar total profit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from models import Project


@dataclass
class ScoredProject:
    """A project together with its scoring components and final rank.

    `value_norm` is the project's total NP min-max-normalised across the
    portfolio (so 0 = worst total NP, 1 = best). `speed_score` is in [0, 1].
    `composite_score` is the weighted combination used for ranking.
    """
    project: Project
    total_net_profit: float
    value_norm: float
    break_even_month: int | None
    speed_score: float
    composite_score: float
    rank: int


def _min_max(values: np.ndarray) -> np.ndarray:
    """Min-max normalise to [0, 1]. Returns 0.5 for every entry if all values are equal."""
    lo, hi = values.min(), values.max()
    if hi - lo < 1e-9:
        return np.full_like(values, 0.5, dtype=float)
    return (values - lo) / (hi - lo)


def score_projects(projects: list[Project],
                   weight_value: float = 0.5,
                   weight_speed: float = 0.5,
                   method: str = "Composite",
                   discount_rate: float = 0.10,
                   reinvest_rate: float = 0.30) -> list[ScoredProject]:
    """Compute the composite score for every project and return them ranked."""
    if not projects:
        return []

    # weights are normalised so the user can set any positive numbers
    w_total = weight_value + weight_speed
    if w_total <= 0:
        raise ValueError("Both weights cannot be zero.")
    w_value, w_speed = weight_value / w_total, weight_speed / w_total

    totals = np.array([p.total_net_profit for p in projects])
    value_norm = _min_max(totals)

    # Break-even speed via the time value of money: a project that turns profitable
    # in month 6 is discounted far less than one that does so in month 20, so EARLY
    # break-even scores higher in absolute time. (Previously this divided by each
    # project's OWN duration, which made long, slow programmes look deceptively
    # "fast" and is why Composite under-valued quick payback.) Normalised to [0, 1].
    r_m = (1.0 + discount_rate) ** (1.0 / 12.0) - 1.0
    disc_factor = np.array([
        1.0 / (1.0 + r_m) ** (p.break_even_month if p.break_even_month is not None
                              else p.duration_months + 1)
        for p in projects
    ])
    speeds = _min_max(disc_factor)

    if method in ("Value Creation Rating", "Hilti Value Creation Rating", "WSJF"):
        # Hilti's official Value Creation Rating: Net Profit / Duration
        # ( = (Business Value - Costs) / Duration ). "WSJF" kept as an alias
        # for backward compatibility with older saved selections.
        composites = np.array([p.total_net_profit / max(1.0, p.duration_months) for p in projects])
    elif method == "ROI":
        composites = np.array([p.total_net_profit / max(1.0, p.total_cost) for p in projects])
    else:
        # Composite = "Capital Velocity": discounted net profit per CHF invested, at the
        # REINVESTMENT rate. It uses each project's real monthly profit profile (unlike
        # Value Creation Rating's uniform "/ duration") AND discounts by absolute time
        # (unlike ROI, which ignores timing). A higher reinvest_rate weights quick payback
        # more heavily — money back sooner can be reinvested into the next projects sooner.
        r_re = (1.0 + reinvest_rate) ** (1.0 / 12.0) - 1.0
        composites = np.array([
            float((p.monthly_net_profit / (1.0 + r_re) ** np.arange(1, p.duration_months + 1)).sum())
            / max(1.0, p.total_cost)
            for p in projects
        ])

    # Rank: highest composite first; stable tie-breaker on total NP
    order = np.lexsort((-totals, -composites))

    ranked: list[ScoredProject] = []
    for rank_idx, i in enumerate(order, start=1):
        p = projects[i]
        ranked.append(ScoredProject(
            project=p,
            total_net_profit=float(totals[i]),
            value_norm=float(value_norm[i]),
            break_even_month=p.break_even_month,
            speed_score=float(speeds[i]),
            composite_score=float(composites[i]),
            rank=rank_idx,
        ))
    return ranked


def ranked_to_dataframe(ranked: list[ScoredProject]) -> pd.DataFrame:
    """Flatten a list of ScoredProject into a dataframe (one row per project)."""
    return pd.DataFrame([{
        "rank": r.rank,
        "project_id": r.project.project_id,
        "name": r.project.name,
        "archetype": r.project.archetype,
        "duration_months": r.project.duration_months,
        "total_business_value": r.project.total_business_value,
        "total_cost": r.project.total_cost,
        "total_net_profit": r.total_net_profit,
        "break_even_month": r.break_even_month,
        "value_score": r.value_norm,
        "speed_score": r.speed_score,
        "composite_score": r.composite_score,
    } for r in ranked])


@dataclass
class ScheduledProject:
    """A scored project scheduled to start at a specific month."""
    scored: ScoredProject
    start_month: int  # 1-indexed

    @property
    def end_month(self) -> int:
        return self.start_month + self.scored.project.duration_months - 1


def schedule_portfolio(
    ranked: list[ScoredProject],
    mode: str = "Sequential",
    budget: float | None = None,
    max_concurrency: int | None = None,
    parallel_spending: float | None = None
) -> list[ScheduledProject]:
    """Greedy scheduler respecting total budget, monthly spending, and concurrency limits."""
    from collections import defaultdict
    
    scheduled = []
    total_spent = 0.0
    
    active_projects = defaultdict(int)
    monthly_spending = defaultdict(float)
    
    current_seq_month = 1
    
    for r in ranked:
        proj = r.project
        
        # Check if the project itself can ever be scheduled under parallel_spending limit
        if mode == "Parallel" and parallel_spending is not None:
            if any(c > parallel_spending for c in proj.monthly_cost):
                continue
        
        if budget is not None and (total_spent + proj.total_cost) > budget:
            continue
            
        total_spent += proj.total_cost
        
        if mode == "Sequential":
            start_m = current_seq_month
            scheduled.append(ScheduledProject(scored=r, start_month=start_m))
            current_seq_month += proj.duration_months
        else:
            m = 1
            while True:
                can_schedule = True
                for offset in range(proj.duration_months):
                    check_m = m + offset
                    if max_concurrency is not None and active_projects[check_m] >= max_concurrency:
                        can_schedule = False
                        break
                    if parallel_spending is not None and (monthly_spending[check_m] + proj.monthly_cost[offset]) > parallel_spending:
                        can_schedule = False
                        break
                
                if can_schedule:
                    break
                m += 1
                
            scheduled.append(ScheduledProject(scored=r, start_month=m))
            for offset in range(proj.duration_months):
                active_projects[m + offset] += 1
                monthly_spending[m + offset] += float(proj.monthly_cost[offset])

    return scheduled


def build_global_timeline(scheduled: list[ScheduledProject]) -> pd.DataFrame:
    """Aggregate monthly KPIs across the global portfolio timeline."""
    if not scheduled:
        return pd.DataFrame(columns=["Month", "Total Cost", "Cumulative Cost", "Business Value", "Net Profit", "Cumulative Net Profit", "FTE Count"])
        
    max_month = max(s.end_month for s in scheduled)
    
    global_cost = np.zeros(max_month)
    global_value = np.zeros(max_month)
    global_fte = np.zeros(max_month)
    
    for s in scheduled:
        start_idx = s.start_month - 1
        end_idx = s.end_month
        
        global_cost[start_idx:end_idx] += s.scored.project.monthly_cost
        global_value[start_idx:end_idx] += s.scored.project.business_value
        global_fte[start_idx:end_idx] += s.scored.project.fte_count
        
    net_profit = global_value - global_cost
    cum_net_profit = np.cumsum(net_profit)
    cum_cost = np.cumsum(global_cost)
    
    return pd.DataFrame({
        "Month": np.arange(1, max_month + 1),
        "Total Cost": global_cost,
        "Cumulative Cost": cum_cost,
        "Business Value": global_value,
        "Net Profit": net_profit,
        "Cumulative Net Profit": cum_net_profit,
        "FTE Count": global_fte
    })


def simulate_reinvestment(projects_in_order: list[Project],
                          start_capital: float,
                          horizon: int) -> dict:
    """Capital-recycling simulation: returns are reinvested into the next projects.

    Walks month by month. Each month, capital is committed to the next projects in
    priority order (a project starts once free capital covers its total cost); the
    started projects then return their business value over their gain phase, which
    replenishes the capital pool and lets it fund further projects sooner. This is
    the "make money fast, reinvest, repeat" objective: a priority order that frees
    capital quickly compounds into more capital within the horizon.

    Returns the monthly capital trajectory, the number of projects funded, and the
    final capital.
    """
    capital = float(start_capital)
    horizon = max(1, int(horizon))
    trajectory = np.empty(horizon)
    active: list[tuple[Project, int]] = []
    bi = 0
    n = len(projects_in_order)
    for t in range(1, horizon + 1):
        # commit capital to the next projects while it is available
        while bi < n and capital >= projects_in_order[bi].total_cost:
            capital -= projects_in_order[bi].total_cost
            active.append((projects_in_order[bi], t))
            bi += 1
        # receive this month's business value from active projects
        for p, start in active:
            local = t - start
            if 0 <= local < p.duration_months:
                capital += float(p.business_value[local])
        trajectory[t - 1] = capital
    return {
        "months": np.arange(1, horizon + 1),
        "capital": trajectory,
        "funded": bi,
        "final_capital": float(trajectory[-1]),
        "start_capital": float(start_capital),
    }


# --------------------------------------------------------------------------
# Risk & robustness analysis
# --------------------------------------------------------------------------

def simulate_portfolio_profit(projects: list[Project],
                              n_iter: int = 1000,
                              bv_std: float = 0.20,
                              cost_std: float = 0.10,
                              seed: int | None = None) -> np.ndarray:
    """Monte-Carlo the total net profit of a *portfolio* (sum over all given projects).

    Each project's monthly business value and cost are independently perturbed by
    Gaussian noise (mean 1, given relative std). Returns an array of length n_iter
    with the simulated total portfolio net profit per iteration.
    """
    rng = np.random.default_rng(seed)
    total = np.zeros(n_iter)
    for p in projects:
        dur = p.duration_months
        noise_bv = rng.normal(1.0, bv_std, (n_iter, dur))
        noise_cost = rng.normal(1.0, cost_std, (n_iter, dur))
        total += (p.business_value * noise_bv).sum(axis=1)
        total -= (p.monthly_cost * noise_cost).sum(axis=1)
    return total


def sensitivity_tornado(projects: list[Project], pct: float = 0.10) -> tuple[float, list[dict]]:
    """One-at-a-time sensitivity of total portfolio net profit to each driver.

    Scales one driver (Business Value, Direct Cost, or FTE/Effort Cost) by ±pct
    while holding the others fixed, and records the resulting total portfolio NP.
    Returns (base_np, rows) where each row has driver, low_np, high_np and the
    absolute swing, sorted by swing descending (largest driver first).
    """
    total_bv = sum(p.total_business_value for p in projects)
    total_direct = sum(p.total_direct_cost for p in projects)
    total_effort = sum(p.total_effort_cost for p in projects)
    base_np = total_bv - (total_direct + total_effort)

    drivers = {
        "Business Value": lambda f: f * total_bv - (total_direct + total_effort),
        "Direct Cost":    lambda f: total_bv - (f * total_direct + total_effort),
        "FTE / Effort Cost": lambda f: total_bv - (total_direct + f * total_effort),
    }
    rows = []
    for name, fn in drivers.items():
        np_minus, np_plus = fn(1.0 - pct), fn(1.0 + pct)
        rows.append({
            "driver": name,
            "low_np": min(np_minus, np_plus),
            "high_np": max(np_minus, np_plus),
            "swing": abs(np_plus - np_minus),
        })
    rows.sort(key=lambda r: r["swing"], reverse=True)
    return base_np, rows


def simulate_rank_stability(projects: list[Project],
                            n_iter: int = 500,
                            bv_std: float = 0.20,
                            cost_std: float = 0.10,
                            weight_value: float = 0.5,
                            weight_speed: float = 0.5,
                            method: str = "Composite",
                            top_n: int = 10,
                            discount_rate: float = 0.10,
                            reinvest_rate: float = 0.30,
                            seed: int | None = None) -> dict:
    """Measure how stable the ranking is when the inputs are perturbed.

    Perturbs every project's monthly business value and cost with Gaussian noise,
    recomputes the chosen ranking method `n_iter` times, and reports how much the
    ranks move. Returns per-project rank statistics plus two headline robustness
    measures: average Spearman rank correlation vs. the base ranking, and the
    average fraction of the base Top-N that stays in the Top-N under noise.
    """
    n = len(projects)
    durations = np.array([p.duration_months for p in projects], dtype=float)
    r_re = (1.0 + reinvest_rate) ** (1.0 / 12.0) - 1.0

    def _scores_from(total_np, total_cost, total_npv):
        """Vectorised scoring over (n_projects, n_cols) matrices."""
        if method in ("Value Creation Rating", "Hilti Value Creation Rating", "WSJF"):
            return total_np / np.maximum(1.0, durations)[:, None]
        if method == "ROI":
            return total_np / np.maximum(1.0, total_cost)
        # Composite = Capital Velocity: discounted net profit per CHF invested.
        return total_npv / np.maximum(1.0, total_cost)

    def _ranks(scores):
        """Rank 1 = highest score, per column. Vectorised double-argsort."""
        order = np.argsort(-scores, axis=0)
        rank_values = np.tile(np.arange(1, scores.shape[0] + 1)[:, None], (1, scores.shape[1]))
        ranks = np.empty_like(order)
        np.put_along_axis(ranks, order, rank_values, axis=0)
        return ranks.astype(float)

    # --- base (noise-free) ranking --------------------------------------
    base_np = np.array([[p.total_net_profit] for p in projects], dtype=float)
    base_cost = np.array([[p.total_cost] for p in projects], dtype=float)
    base_npv = np.array([[float((p.monthly_net_profit /
                                 (1.0 + r_re) ** np.arange(1, p.duration_months + 1)).sum())]
                         for p in projects], dtype=float)
    base_ranks = _ranks(_scores_from(base_np, base_cost, base_npv))[:, 0]

    # --- perturbed simulations ------------------------------------------
    rng = np.random.default_rng(seed)
    total_np = np.zeros((n, n_iter))
    total_cost = np.zeros((n, n_iter))
    total_npv = np.zeros((n, n_iter))
    for i, p in enumerate(projects):
        dur = p.duration_months
        noise_bv = rng.normal(1.0, bv_std, (n_iter, dur))
        noise_cost = rng.normal(1.0, cost_std, (n_iter, dur))
        sim_cost = p.monthly_cost * noise_cost
        monthly_np = p.business_value * noise_bv - sim_cost
        total_np[i] = monthly_np.sum(axis=1)
        total_cost[i] = sim_cost.sum(axis=1)
        total_npv[i] = (monthly_np / (1.0 + r_re) ** np.arange(1, dur + 1)).sum(axis=1)

    ranks = _ranks(_scores_from(total_np, total_cost, total_npv))

    # --- robustness summary measures ------------------------------------
    br = base_ranks - base_ranks.mean()
    rf = ranks - ranks.mean(axis=0)
    num = (rf * br[:, None]).sum(axis=0)
    den = np.sqrt((rf ** 2).sum(axis=0) * (br ** 2).sum())
    spearman = np.where(den > 0, num / den, 0.0)

    base_top_idx = np.where(base_ranks <= top_n)[0]
    in_top = ranks <= top_n
    retention = in_top[base_top_idx, :].mean(axis=0) if base_top_idx.size else np.zeros(n_iter)

    return {
        "project_ids": [p.project_id for p in projects],
        "project_names": [p.name for p in projects],
        "base_rank": base_ranks,
        "rank_mean": ranks.mean(axis=1),
        "rank_p10": np.percentile(ranks, 10, axis=1),
        "rank_p90": np.percentile(ranks, 90, axis=1),
        "rank_best": ranks.min(axis=1),
        "rank_worst": ranks.max(axis=1),
        "spearman_mean": float(spearman.mean()),
        "topN_retention": float(retention.mean()),
        "top_n": top_n,
    }
