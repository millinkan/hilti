"""Generate a realistic portfolio of 100 projects for a Hilti-style company.

Each project belongs to one of eight archetypes that capture different
investment shapes a tool/construction-equipment company runs:

- Tool R&D                 long, FTE-heavy, plateau revenue after launch
- Software Platform        medium, accelerating value as adoption grows
- Manufacturing Process    short to medium, steady cost savings
- Marketing Campaign       short, sharp value spike, then decay
- Sustainability/Compliance long, mostly cost, modest steady value
- Training & Enablement    medium, slow productivity gains
- Supply Chain Optimization medium, strong steady savings
- Digital Transformation   long, S-curve adoption, large eventual value

Each archetype defines plausible ranges for duration, cost-phase share,
FTE staffing, direct cost magnitude, and the *shape* of the value curve
during the gain phase. Projects are not all winners: some archetypes
have realistic chances of failing to break even within their lifetime.

Run as a script to (re)generate data/projects_meta.csv and
data/projects_monthly.csv with 100 projects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from models import Project, save_projects


# Currency unit is EUR. Magnitudes calibrated for a company at Hilti's scale
# (multi-billion revenue): per-project totals run from a few hundred k EUR
# (training pilot) up to ~50 M EUR (digital transformation programme).
CURRENCY = "EUR"


# --------------------------------------------------------------------------
# Value-curve shapes (during the gain phase only)
# --------------------------------------------------------------------------

def _normalize(arr: np.ndarray) -> np.ndarray:
    s = arr.sum()
    return arr / s if s > 0 else arr


def shape_linear_ramp(n: int, rng: np.random.Generator) -> np.ndarray:
    """Linear ramp from 0 to peak — typical for adoption-driven savings."""
    return _normalize(np.linspace(0.2, 1.0, n))


def shape_accelerating(n: int, rng: np.random.Generator) -> np.ndarray:
    """Quadratic ramp — value compounds as the platform/process scales."""
    t = np.linspace(0, 1, n)
    return _normalize(0.1 + t ** 2)


def shape_plateau(n: int, rng: np.random.Generator) -> np.ndarray:
    """Quick ramp to a steady plateau — product launches, recurring savings."""
    ramp = max(1, int(round(n * rng.uniform(0.15, 0.30))))
    curve = np.ones(n)
    curve[:ramp] = np.linspace(0.2, 1.0, ramp)
    return _normalize(curve)


def shape_peak_decay(n: int, rng: np.random.Generator) -> np.ndarray:
    """Sharp peak then exponential decay — marketing campaigns."""
    t = np.arange(n)
    decay = rng.uniform(0.25, 0.50)
    curve = np.exp(-decay * t)
    # quick ramp up to the peak in the first 1-2 months
    if n >= 2:
        curve[0] *= 0.6
    return _normalize(curve)


def shape_s_curve(n: int, rng: np.random.Generator) -> np.ndarray:
    """S-curve adoption — slow start, fast middle, plateau."""
    t = np.linspace(-3, 3, n)
    curve = 1.0 / (1.0 + np.exp(-t))
    return _normalize(curve)


def shape_slow_steady(n: int, rng: np.random.Generator) -> np.ndarray:
    """Low, gradually rising curve — training/compliance value."""
    return _normalize(np.linspace(0.5, 1.0, n))


# --------------------------------------------------------------------------
# Archetype catalogue
# --------------------------------------------------------------------------

@dataclass
class Archetype:
    """Plausible parameter ranges for one category of project.

    Each archetype defines plausible bounds (uniform draws) for duration, cost-
    phase share, staffing, costs, and total value. `value_shape` is the
    function that distributes the total business value across the months of
    the gain phase. `failure_rate` is the probability that the project
    realises only a fraction of expected value (not a guarantee that it
    won't break even — depends on the magnitude of the cuts).
    """
    name: str
    weight: float                          # sampling weight in the portfolio
    duration_range: tuple[int, int]        # months
    cost_phase_share_range: tuple[float, float]
    fte_cost_phase_range: tuple[int, int]
    fte_gain_phase_range: tuple[int, int]
    direct_cost_phase_range: tuple[float, float]   # EUR / month during cost phase
    direct_gain_phase_range: tuple[float, float]   # EUR / month during gain phase
    fte_cost_monthly_range: tuple[float, float]    # loaded EUR / FTE / month
    total_value_range: tuple[float, float]         # total business value over gain phase
    value_shape: Callable[[int, np.random.Generator], np.ndarray]
    failure_rate: float                    # probability the project under-delivers

    def sample(self, rng: np.random.Generator) -> dict:
        """Draw one set of project parameters from the archetype's ranges."""
        return {
            "duration": int(rng.integers(*self.duration_range, endpoint=True)),
            "cost_share": float(rng.uniform(*self.cost_phase_share_range)),
            "fte_cost": int(rng.integers(*self.fte_cost_phase_range, endpoint=True)),
            "fte_gain": int(rng.integers(*self.fte_gain_phase_range, endpoint=True)),
            "dc_cost": float(rng.uniform(*self.direct_cost_phase_range)),
            "dc_gain": float(rng.uniform(*self.direct_gain_phase_range)),
            "fte_cost_monthly": float(rng.uniform(*self.fte_cost_monthly_range)),
            "total_value": float(rng.uniform(*self.total_value_range)),
            "fail": rng.random() < self.failure_rate,
        }


ARCHETYPES: list[Archetype] = [
    Archetype(
        name="Tool R&D",
        weight=0.18,
        duration_range=(18, 36),
        cost_phase_share_range=(0.55, 0.75),
        fte_cost_phase_range=(8, 18),
        fte_gain_phase_range=(2, 5),
        direct_cost_phase_range=(40_000, 150_000),
        direct_gain_phase_range=(5_000, 20_000),
        fte_cost_monthly_range=(11_000, 16_000),
        total_value_range=(8_000_000, 45_000_000),
        value_shape=shape_plateau,
        failure_rate=0.10,
    ),
    Archetype(
        name="Software Platform",
        weight=0.16,
        duration_range=(9, 24),
        cost_phase_share_range=(0.40, 0.60),
        fte_cost_phase_range=(4, 12),
        fte_gain_phase_range=(2, 6),
        direct_cost_phase_range=(20_000, 80_000),
        direct_gain_phase_range=(8_000, 30_000),
        fte_cost_monthly_range=(11_000, 17_000),
        total_value_range=(2_500_000, 18_000_000),
        value_shape=shape_accelerating,
        failure_rate=0.12,
    ),
    Archetype(
        name="Manufacturing Process Improvement",
        weight=0.14,
        duration_range=(4, 12),
        cost_phase_share_range=(0.25, 0.45),
        fte_cost_phase_range=(2, 6),
        fte_gain_phase_range=(0, 2),
        direct_cost_phase_range=(30_000, 120_000),
        direct_gain_phase_range=(2_000, 10_000),
        fte_cost_monthly_range=(10_000, 14_000),
        total_value_range=(1_000_000, 8_000_000),
        value_shape=shape_linear_ramp,
        failure_rate=0.05,
    ),
    Archetype(
        name="Marketing Campaign",
        weight=0.10,
        duration_range=(2, 6),
        cost_phase_share_range=(0.30, 0.55),
        fte_cost_phase_range=(1, 4),
        fte_gain_phase_range=(0, 2),
        direct_cost_phase_range=(80_000, 300_000),
        direct_gain_phase_range=(10_000, 50_000),
        fte_cost_monthly_range=(10_000, 14_000),
        total_value_range=(400_000, 4_500_000),
        value_shape=shape_peak_decay,
        failure_rate=0.20,
    ),
    Archetype(
        name="Sustainability / Compliance",
        weight=0.10,
        duration_range=(8, 24),
        cost_phase_share_range=(0.65, 0.90),
        fte_cost_phase_range=(2, 5),
        fte_gain_phase_range=(1, 3),
        direct_cost_phase_range=(20_000, 90_000),
        direct_gain_phase_range=(3_000, 15_000),
        fte_cost_monthly_range=(11_000, 15_000),
        total_value_range=(800_000, 5_500_000),
        value_shape=shape_slow_steady,
        failure_rate=0.18,
    ),
    Archetype(
        name="Training & Enablement",
        weight=0.10,
        duration_range=(3, 10),
        cost_phase_share_range=(0.30, 0.55),
        fte_cost_phase_range=(1, 4),
        fte_gain_phase_range=(0, 1),
        direct_cost_phase_range=(8_000, 40_000),
        direct_gain_phase_range=(1_000, 6_000),
        fte_cost_monthly_range=(9_000, 13_000),
        total_value_range=(300_000, 2_500_000),
        value_shape=shape_slow_steady,
        failure_rate=0.10,
    ),
    Archetype(
        name="Supply Chain Optimization",
        weight=0.12,
        duration_range=(6, 18),
        cost_phase_share_range=(0.35, 0.55),
        fte_cost_phase_range=(3, 8),
        fte_gain_phase_range=(1, 3),
        direct_cost_phase_range=(30_000, 120_000),
        direct_gain_phase_range=(5_000, 20_000),
        fte_cost_monthly_range=(11_000, 15_000),
        total_value_range=(2_000_000, 14_000_000),
        value_shape=shape_linear_ramp,
        failure_rate=0.08,
    ),
    Archetype(
        name="Digital Transformation",
        weight=0.10,
        duration_range=(18, 36),
        cost_phase_share_range=(0.50, 0.70),
        fte_cost_phase_range=(10, 25),
        fte_gain_phase_range=(3, 8),
        direct_cost_phase_range=(80_000, 300_000),
        direct_gain_phase_range=(15_000, 60_000),
        fte_cost_monthly_range=(12_000, 18_000),
        total_value_range=(10_000_000, 60_000_000),
        value_shape=shape_s_curve,
        failure_rate=0.15,
    ),
]


# --------------------------------------------------------------------------
# Project name pool — short, plausible, archetype-flavoured
# --------------------------------------------------------------------------

NAME_POOL = {
    "Tool R&D": [
        "Cordless Drill Gen-7", "Rotary Hammer Pro Line", "Diamond Coring System",
        "Battery Platform 2.0", "Measuring Laser X", "Anchor Setting Tool",
        "Heavy-Duty Saw Series", "Powder-Actuated Tool Refresh",
    ],
    "Software Platform": [
        "Fleet Management Portal", "On!Track Mobile Refresh", "Customer Self-Service Hub",
        "Quoting Engine v2", "BIM Integration Suite", "Field Service App",
        "Spare Parts Catalogue", "Predictive Maintenance Cloud",
    ],
    "Manufacturing Process Improvement": [
        "Schaan Line Automation", "Kaufering Quality Gate", "Casting Yield Boost",
        "Assembly Cell Redesign", "Packaging Throughput", "Heat Treatment Optimisation",
        "Surface Coating Upgrade", "PCB Test Automation",
    ],
    "Marketing Campaign": [
        "TE 6-A36 Launch Push", "Trade Show Munich '25", "Construction Pro Loyalty",
        "Battery Trade-In Drive", "EU Builders Campaign", "Digital Lead-Gen Sprint",
        "Influencer Roof Series", "Anchor System Awareness",
    ],
    "Sustainability / Compliance": [
        "Carbon Footprint Reporting", "REACH Compliance Refresh", "Recycled Plastics Pilot",
        "Solar Roof Schaan", "Energy Audit EU Plants", "Battery Take-Back Programme",
        "GDPR Data Pipeline", "Conflict Minerals Tracking",
    ],
    "Training & Enablement": [
        "Sales Academy Refresh", "Service Tech Certification", "Leadership Pipeline",
        "Digital Tools Onboarding", "Lean Six Sigma Wave 4", "BIM Training",
        "Compliance E-Learning", "Apprenticeship Programme",
    ],
    "Supply Chain Optimization": [
        "EU Warehouse Consolidation", "Inbound Carrier Rebid", "Vendor Managed Inventory",
        "S&OP Process Redesign", "Demand Forecasting AI", "Spare Parts Network",
        "Direct-Ship Programme", "Supplier Quality Portal",
    ],
    "Digital Transformation": [
        "ERP Migration EU", "Global CRM Rollout", "Connected Tools Platform",
        "Smart Factory Initiative", "Data Lake Foundation", "Field IoT Deployment",
        "AI Operations Platform", "Customer Data Unification",
    ],
}


# --------------------------------------------------------------------------
# Per-project synthesis
# --------------------------------------------------------------------------

def _synthesize_project(project_id: str,
                        archetype: Archetype,
                        rng: np.random.Generator,
                        duration_range: tuple[int, int] | None = None) -> Project:
    """Build the monthly arrays for one project given an archetype draw.

    `duration_range` (lo, hi) overrides the archetype's sampled duration with a
    uniform draw from that range. The total business value is scaled by the
    duration ratio so the per-month value intensity stays realistic — a Tool R&D
    programme compressed from 28 to 4 months keeps its monthly earning rate
    instead of cramming the full 28-month value into 4 months.
    """
    p = archetype.sample(rng)
    if duration_range is not None:
        lo, hi = duration_range
        new_n = int(rng.integers(lo, hi, endpoint=True))
        p["total_value"] *= new_n / p["duration"]
        p["duration"] = new_n
    n = p["duration"]
    cost_months = max(1, int(round(n * p["cost_share"])))
    cost_months = min(cost_months, n - 1) if n > 1 else cost_months
    gain_months = n - cost_months

    # FTE staffing: peak during cost phase, lower during gain phase, with mild noise
    fte = np.empty(n)
    fte[:cost_months] = p["fte_cost"] + rng.normal(0, 0.6, cost_months)
    if gain_months > 0:
        fte[cost_months:] = p["fte_gain"] + rng.normal(0, 0.4, gain_months)
    fte = np.clip(np.round(fte), 0, None)

    # Direct cost: high during cost phase, lower during gain phase, with noise
    direct = np.empty(n)
    direct[:cost_months] = p["dc_cost"] * rng.normal(1.0, 0.12, cost_months)
    if gain_months > 0:
        direct[cost_months:] = p["dc_gain"] * rng.normal(1.0, 0.18, gain_months)
    direct = np.clip(direct, 0, None)

    # Business value: zero during cost phase, archetype-shape during gain phase
    value = np.zeros(n)
    if gain_months > 0:
        shape = archetype.value_shape(gain_months, rng)
        total_value = p["total_value"]
        if p["fail"]:
            # A failing project realises only a fraction of expected value
            total_value *= rng.uniform(0.10, 0.45)
        # add per-month noise but keep total ~ unchanged
        noise = rng.normal(1.0, 0.08, gain_months)
        gain_curve = shape * total_value * noise
        gain_curve *= total_value / max(gain_curve.sum(), 1e-9)
        value[cost_months:] = np.clip(gain_curve, 0, None)

    # Pick a name; fall back to archetype + id if pool is exhausted-ish
    pool = NAME_POOL.get(archetype.name, [archetype.name])
    name = f"{rng.choice(pool)} ({project_id})"

    return Project(
        project_id=project_id,
        name=name,
        archetype=archetype.name,
        duration_months=n,
        fte_cost_monthly=p["fte_cost_monthly"],
        direct_cost=direct,
        fte_count=fte,
        business_value=value,
    )


def generate_projects(n_projects: int = 100, seed: int = 42,
                      duration_range: tuple[int, int] | None = None) -> list[Project]:
    """Generate a portfolio of `n_projects` projects, sampled across all archetypes.

    Reproducible: same `seed` always produces the same portfolio.
    `duration_range=(lo, hi)` forces every project's duration into that range
    (e.g. (1, 4) for a short-project portfolio); business value scales with the
    duration so monthly intensity stays realistic. With `duration_range=None`
    no extra random draws happen, so existing seeds keep producing exactly the
    same portfolios as before.
    """
    rng = np.random.default_rng(seed)
    weights = np.array([a.weight for a in ARCHETYPES])
    weights = weights / weights.sum()

    projects: list[Project] = []
    for i in range(1, n_projects + 1):
        archetype = ARCHETYPES[rng.choice(len(ARCHETYPES), p=weights)]
        projects.append(_synthesize_project(f"P-{i:04d}", archetype, rng, duration_range))
    return projects


if __name__ == "__main__":
    projects = generate_projects(n_projects=100, seed=42)
    save_projects(projects)
    total_np = sum(p.total_net_profit for p in projects)
    breakeven = sum(1 for p in projects if p.break_even_month is not None)
    print(f"Generated {len(projects)} projects")
    print(f"  archetypes: {sorted(set(p.archetype for p in projects))}")
    print(f"  duration:   {min(p.duration_months for p in projects)}-"
          f"{max(p.duration_months for p in projects)} months")
    print(f"  total NP:   {total_np:,.0f} {CURRENCY}")
    print(f"  break-even: {breakeven} of {len(projects)} projects reach it within lifetime")
    print(f"Wrote data/projects_meta.csv and data/projects_monthly.csv")
