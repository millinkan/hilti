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
                   weight_value: float = 0.75,
                   weight_speed: float = 0.25,
                   method: str = "Composite") -> list[ScoredProject]:
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

    speeds = np.array([
        max(0.0, 1.0 - (p.break_even_month - 1) / p.duration_months)
        if p.break_even_month is not None else 0.0
        for p in projects
    ])

    if method == "WSJF":
        composites = np.array([p.total_net_profit / max(1.0, p.duration_months) for p in projects])
    elif method == "ROI":
        composites = np.array([p.total_net_profit / max(1.0, p.total_cost) for p in projects])
    else:
        composites = w_value * value_norm + w_speed * speeds

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
