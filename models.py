"""Domain model for a project portfolio.

A Project carries one row per month of its lifetime. The four monthly inputs
are the KPIs the user defined:

- direct_cost      money spent that month on consultants, licenses, infra ...
- fte_count        number of full-time-equivalent people on the project
- fte_cost_monthly average loaded cost per FTE per month (currency / FTE / month)
- business_value   money generated that month (revenue, savings, risk reduction)

Everything else (cost, net profit, cumulative NP, break-even month) is derived.
Storing only the four inputs keeps the data file the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

import numpy as np
import pandas as pd


PROJECTS_META_CSV = "data/projects_meta.csv"
PROJECTS_MONTHLY_CSV = "data/projects_monthly.csv"


@dataclass
class Project:
    """One project's lifetime in monthly KPIs.

    The four arrays (direct_cost, fte_count, business_value) plus the scalar
    fte_cost_monthly are the only thing stored. All other KPIs (cost, net
    profit, cumulative net profit, break-even month, phase lengths) are
    computed from those inputs on demand by the properties below.

    All money values are in EUR; `month` indices are 1-based externally
    (month 1 = first month of the project) but the underlying numpy arrays
    are 0-indexed.
    """
    project_id: str
    name: str
    archetype: str
    duration_months: int
    fte_cost_monthly: float
    direct_cost: np.ndarray       # shape (duration_months,) — EUR / month
    fte_count: np.ndarray         # shape (duration_months,) — persons
    business_value: np.ndarray    # shape (duration_months,) — EUR / month

    # ---- derived series ------------------------------------------------

    @property
    def effort_cost(self) -> np.ndarray:
        """Per-month effort cost: fte_count[t] · fte_cost_monthly."""
        return self.fte_count * self.fte_cost_monthly

    @property
    def monthly_cost(self) -> np.ndarray:
        """Per-month total cost: direct_cost[t] + effort_cost[t]."""
        return self.direct_cost + self.effort_cost

    @property
    def monthly_net_profit(self) -> np.ndarray:
        """Per-month net profit: business_value[t] − monthly_cost[t]."""
        return self.business_value - self.monthly_cost

    @property
    def cumulative_net_profit(self) -> np.ndarray:
        """Running sum of monthly net profit; starts negative during cost phase."""
        return np.cumsum(self.monthly_net_profit)

    # ---- scalar KPIs ---------------------------------------------------

    @property
    def total_business_value(self) -> float:
        """Sum of business value across the lifetime (EUR)."""
        return float(self.business_value.sum())

    @property
    def total_direct_cost(self) -> float:
        """Sum of direct cost across the lifetime (EUR)."""
        return float(self.direct_cost.sum())

    @property
    def total_effort_cost(self) -> float:
        """Sum of effort cost across the lifetime (EUR)."""
        return float(self.effort_cost.sum())

    @property
    def total_cost(self) -> float:
        """Sum of monthly cost (direct + effort) across the lifetime (EUR)."""
        return float(self.monthly_cost.sum())

    @property
    def total_net_profit(self) -> float:
        """Sum of monthly net profit across the lifetime (EUR). Can be negative."""
        return float(self.monthly_net_profit.sum())

    @property
    def break_even_month(self) -> Optional[int]:
        """First 1-indexed month where cumulative NP turns ≥ 0, or None if never."""
        cum = self.cumulative_net_profit
        positive = np.where(cum >= 0)[0]
        if positive.size == 0:
            return None
        return int(positive[0] + 1)

    @property
    def cost_phase_months(self) -> int:
        """Months at the start where cumulative NP is still negative.

        If the project never breaks even this equals the full duration.
        """
        be = self.break_even_month
        return self.duration_months if be is None else be - 1

    @property
    def gain_phase_months(self) -> int:
        """Months from break-even to the end of the project (0 if never breaks even)."""
        return self.duration_months - self.cost_phase_months


# --------------------------------------------------------------------------
# Cost buffer (estimation contingency)
# --------------------------------------------------------------------------

def apply_cost_buffer(projects: list[Project], buffer: float) -> list[Project]:
    """Return copies of the projects with all costs inflated by `buffer` (e.g. 0.10 = +10%).

    Models an estimation/contingency reserve on top of the planned cost.
    Scaling both direct_cost and fte_cost_monthly by (1 + buffer) inflates the
    whole monthly cost curve uniformly, so net profit, break-even and totals all
    reflect the buffer automatically. Business value and FTE counts are untouched.
    The buffer is a view-time multiplier and is never persisted to the CSVs.
    """
    if not buffer:
        return projects
    factor = 1.0 + float(buffer)
    return [
        replace(p, direct_cost=p.direct_cost * factor, fte_cost_monthly=p.fte_cost_monthly * factor)
        for p in projects
    ]


# --------------------------------------------------------------------------
# Persistence: long-format CSVs, two files (metadata + monthly)
# --------------------------------------------------------------------------

def projects_to_dataframes(projects: list[Project]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a list of projects into the two long-format dataframes used on disk.

    Returns (meta_df, monthly_df). meta_df has one row per project; monthly_df
    has one row per (project_id, month).
    """
    meta_rows = []
    monthly_rows = []
    for p in projects:
        meta_rows.append({
            "project_id": p.project_id,
            "name": p.name,
            "archetype": p.archetype,
            "duration_months": p.duration_months,
            "fte_cost_monthly": p.fte_cost_monthly,
        })
        for m in range(p.duration_months):
            monthly_rows.append({
                "project_id": p.project_id,
                "month": m + 1,
                "direct_cost": float(p.direct_cost[m]),
                "fte_count": float(p.fte_count[m]),
                "business_value": float(p.business_value[m]),
            })
    return pd.DataFrame(meta_rows), pd.DataFrame(monthly_rows)


def save_projects(projects: list[Project],
                  meta_path: str = PROJECTS_META_CSV,
                  monthly_path: str = PROJECTS_MONTHLY_CSV) -> None:
    """Write the portfolio to the two CSV files (overwrite existing)."""
    import os
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    meta_df, monthly_df = projects_to_dataframes(projects)
    meta_df.to_csv(meta_path, index=False)
    monthly_df.to_csv(monthly_path, index=False)


def load_projects(meta_path: str = PROJECTS_META_CSV,
                  monthly_path: str = PROJECTS_MONTHLY_CSV) -> list[Project]:
    """Read both CSVs and return one Project per row in meta_df."""
    meta_df = pd.read_csv(meta_path)
    monthly_df = pd.read_csv(monthly_path).sort_values(["project_id", "month"])

    projects: list[Project] = []
    for _, meta in meta_df.iterrows():
        rows = monthly_df[monthly_df["project_id"] == meta["project_id"]]
        projects.append(Project(
            project_id=str(meta["project_id"]),
            name=str(meta["name"]),
            archetype=str(meta["archetype"]),
            duration_months=int(meta["duration_months"]),
            fte_cost_monthly=float(meta["fte_cost_monthly"]),
            direct_cost=rows["direct_cost"].to_numpy(),
            fte_count=rows["fte_count"].to_numpy(),
            business_value=rows["business_value"].to_numpy(),
        ))
    return projects


def append_project(project: Project,
                   meta_path: str = PROJECTS_META_CSV,
                   monthly_path: str = PROJECTS_MONTHLY_CSV) -> None:
    """Append a single project to the existing CSVs (read-modify-write)."""
    existing = load_projects(meta_path, monthly_path)
    existing.append(project)
    save_projects(existing, meta_path, monthly_path)


# --------------------------------------------------------------------------
# Convenience: long-format dataframe with derived monthly columns
# --------------------------------------------------------------------------

def build_monthly_long_df(projects: list[Project]) -> pd.DataFrame:
    """Returns a long-format dataframe with all derived monthly KPIs.

    Columns: project_id, name, archetype, month, direct_cost, fte_count,
    effort_cost, monthly_cost, business_value, monthly_net_profit,
    cumulative_net_profit
    """
    frames = []
    for p in projects:
        frames.append(pd.DataFrame({
            "project_id": p.project_id,
            "name": p.name,
            "archetype": p.archetype,
            "month": np.arange(1, p.duration_months + 1),
            "direct_cost": p.direct_cost,
            "fte_count": p.fte_count,
            "effort_cost": p.effort_cost,
            "monthly_cost": p.monthly_cost,
            "business_value": p.business_value,
            "monthly_net_profit": p.monthly_net_profit,
            "cumulative_net_profit": p.cumulative_net_profit,
        }))
    return pd.concat(frames, ignore_index=True)
