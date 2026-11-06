"""Synthetic data for the fictional Example Islamic Bank Ltd (EXIB).

Everything here is invented. No real bank, customer or account is described.
The data is built from the bottom up so that it behaves like a real bank:

1. financing contracts, deposit accounts and investment pools are generated
   with seeded random numbers (the same seed always gives the same bank)
2. the general ledger is then built from that detail, so the trial balance
   reconciles to the portfolio and deposits to the rupee, and balances exactly
   (unappropriated profit is the balancing figure, as in a real close)

Calibration (docs/07-guidelines-and-data.md section 2.2):
- financing mix by value follows SBP's Islamic Banking Bulletin (March 2026):
  Diminishing Musharakah 34%, Musharakah and Running Musharakah about 26%,
  Istisna 10%, Murabaha 9%, others about 21%
- deposits by value: current about 41%, savings about 36%, term about 23%
- most small accounts hold under Rs 50,000
- gross pool yields around the 12% policy rate, Mudarib share 50% on the
  general pool

Two scenarios:
- baseline: a healthy bank that passes the 75% rule narrowly
- stressed: planted problems for the demo (a savings tier below 75% of WAGY,
  a Mudarib share above 50%, PER contribution above 2%, late weightage notice,
  charity booked as income, a provision shortfall, higher NPF, one unreadable
  cell)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

import numpy as np

from daleel.core.money import D

INSTITUTION = "Example Islamic Bank Ltd"
SHORT = "EXIB"
TWO = Decimal("0.01")


@dataclass(frozen=True)
class Scenario:
    name: str = "baseline"
    seed: int = 20260930
    period_end: date = date(2026, 9, 30)
    period_days: int = 30
    n_contracts: int = 3000
    n_deposits: int = 30000
    n_branches: int = 25

    @property
    def stressed(self) -> bool:
        return self.name == "stressed"


@dataclass
class Bundle:
    scenario: Scenario
    financing: list[dict] = field(default_factory=list)
    deposits: list[dict] = field(default_factory=list)
    pools: list[dict] = field(default_factory=list)
    trial_balance: list[dict] = field(default_factory=list)
    capital: list[dict] = field(default_factory=list)
    planted: list[str] = field(default_factory=list)


def money(x: float | Decimal) -> Decimal:
    return D(x).quantize(TWO, rounding=ROUND_HALF_EVEN)


# Mode -> target share of financing value, GL code, and portfolio mix.
MODES = {
    "DIMINISHING_MUSHARAKAH": (0.340, "1420-001", {"HOUSING": 0.7, "CORPORATE": 0.3}),
    "MUSHARAKAH": (0.150, "1430-001", {"CORPORATE": 0.8, "INFRASTRUCTURE": 0.05, "SME_MEDIUM": 0.15}),
    "RUNNING_MUSHARAKAH": (0.107, "1431-001", {"CORPORATE": 0.7, "SME_MEDIUM": 0.3}),
    "ISTISNA": (0.101, "1440-001", {"CORPORATE": 0.6, "SME_SMALL": 0.2, "SME_MEDIUM": 0.2}),
    "MURABAHA": (0.092, "1400-001", {"CORPORATE": 0.5, "SME_SMALL": 0.2, "SME_MEDIUM": 0.1, "CONSUMER_PERSONAL": 0.2}),
    "IJARAH": (0.070, "1410-001", {"CONSUMER_AUTO": 0.8, "CORPORATE": 0.2}),
    "TIJARAH": (0.060, "1460-001", {"SME_SMALL": 0.5, "SME_MEDIUM": 0.5}),
    "SALAM": (0.030, "1450-001", {"AGRI_PRODUCTION": 0.8, "AGRI_DEVELOPMENT": 0.2}),
    "OTHER": (0.050, "1470-001", {"CONSUMER_PERSONAL": 0.5, "CORPORATE": 0.5}),
}
MEDIAN = {"CORPORATE": 120e6, "INFRASTRUCTURE": 600e6, "SME_MEDIUM": 25e6, "SME_SMALL": 4e6,
          "HOUSING": 9e6, "CONSUMER_AUTO": 3.5e6, "CONSUMER_PERSONAL": 0.6e6,
          "AGRI_PRODUCTION": 1.5e6, "AGRI_DEVELOPMENT": 3e6}
LGD = {"HOUSING": 0.25, "CONSUMER_AUTO": 0.35, "CORPORATE": 0.45, "INFRASTRUCTURE": 0.40,
       "SME_MEDIUM": 0.50, "SME_SMALL": 0.50, "CONSUMER_PERSONAL": 0.65,
       "AGRI_PRODUCTION": 0.50, "AGRI_DEVELOPMENT": 0.50}
FSV = {"HOUSING": 0.8, "CONSUMER_AUTO": 0.5, "CORPORATE": 0.4, "INFRASTRUCTURE": 0.5,
       "SME_MEDIUM": 0.3, "SME_SMALL": 0.3, "CONSUMER_PERSONAL": 0.0,
       "AGRI_PRODUCTION": 0.2, "AGRI_DEVELOPMENT": 0.2}
COUNTERPARTY = {"CORPORATE": "CORPORATE", "INFRASTRUCTURE": "CORPORATE", "SME_MEDIUM": "SME",
                "SME_SMALL": "SME", "HOUSING": "MORTGAGE", "CONSUMER_AUTO": "RETAIL",
                "CONSUMER_PERSONAL": "RETAIL", "AGRI_PRODUCTION": "RETAIL", "AGRI_DEVELOPMENT": "RETAIL"}

TOTAL_FINANCING = 78e9
DEPOSIT_TARGET = {"CURRENT": 61.5e9, "SAVINGS": 54.0e9, "TERM": 34.5e9}
GROSS_YIELD = {"GEN-PKR": 0.128, "SPL-CORP": 0.122, "SCF-01": 0.110, "OMO-01": 0.112}


def _branches(n: int) -> list[str]:
    return [f"PK{i:04d}" for i in range(1, n + 1)]


def generate(scenario: Scenario | None = None) -> Bundle:
    sc = scenario or Scenario()
    rng = np.random.default_rng(sc.seed + (7 if sc.stressed else 0))
    bundle = Bundle(sc)
    branches = _branches(sc.n_branches)
    _financing(sc, rng, branches, bundle)
    _deposits(sc, rng, branches, bundle)
    _pools(sc, bundle)
    _capital(sc, bundle)
    return bundle


def _financing(sc: Scenario, rng: np.random.Generator, branches: list[str], bundle: Bundle) -> None:
    names = list(MODES)
    count_weights = np.array([0.20, 0.10, 0.08, 0.08, 0.14, 0.18, 0.08, 0.08, 0.06])
    modes = rng.choice(names, size=sc.n_contracts, p=count_weights / count_weights.sum())
    rows = []
    bad = 2.0 if sc.stressed else 0.9
    for i, mode in enumerate(modes):
        mix = MODES[mode][2]
        portfolio = rng.choice(list(mix), p=np.array(list(mix.values())) / sum(mix.values()))
        amount = float(rng.lognormal(np.log(MEDIAN[portfolio]), 0.9))
        u = rng.random()
        cuts = np.cumsum([0.90, 0.045, 0.025 * bad, 0.012 * bad, 0.010 * bad, 0.008 * bad])
        cuts = cuts / cuts[-1]
        if u < cuts[0]:
            dpd = 0
        elif u < cuts[1]:
            dpd = int(rng.integers(1, 60))
        elif u < cuts[2]:
            dpd = int(rng.integers(60, 90))
        elif u < cuts[3]:
            dpd = int(rng.integers(90, 180))
        elif u < cuts[4]:
            dpd = int(rng.integers(180, 365))
        else:
            dpd = int(rng.integers(365, 900))
        pd12 = float(np.clip(rng.lognormal(np.log(0.012), 0.6), 0.002, 0.2))
        has_pd = rng.random() > 0.05  # 5% have no PD, so the default is used and flagged
        counterparty = COUNTERPARTY[portfolio]
        if portfolio == "CORPORATE" and rng.random() < 0.02:
            counterparty = "SOVEREIGN_PKR"  # GoP guaranteed public sector project
        rows.append({
            "contract_id": f"{SHORT}-F{i + 1:07d}",
            "customer_ref": f"C{int(rng.integers(10**8, 10**9))}",
            "mode": mode, "portfolio": portfolio, "counterparty_type": counterparty,
            "currency": "PKR", "_raw_amount": amount, "days_past_due": dpd,
            "_fsv_share": FSV[portfolio] * float(rng.uniform(0.8, 1.1)),
            "pd_12m": round(pd12, 6) if has_pd else None,
            "pd_lifetime": round(min(0.9, pd12 * float(rng.uniform(6, 12))), 6) if has_pd else None,
            "lgd": round(float(np.clip(LGD[portfolio] + rng.normal(0, 0.05), 0.1, 0.9)), 4),
            "pool_id": "SPL-CORP" if portfolio == "CORPORATE" and rng.random() < 0.15 else "GEN-PKR",
            "branch_code": branches[int(rng.integers(0, len(branches)))],
            "maturity_date": sc.period_end + timedelta(days=int(rng.integers(120, 15 * 365))),
        })
    # Rescale amounts per mode so the value mix matches the SBP bulletin.
    for mode, (share, _, _) in MODES.items():
        group = [r for r in rows if r["mode"] == mode]
        raw_total = sum(r["_raw_amount"] for r in group)
        factor = TOTAL_FINANCING * share / raw_total
        for r in group:
            r["outstanding"] = money(r["_raw_amount"] * factor)
            r["collateral_fsv"] = money(float(r["outstanding"]) * r["_fsv_share"])
            del r["_raw_amount"], r["_fsv_share"]
    bundle.financing = rows


def _deposits(sc: Scenario, rng: np.random.Generator, branches: list[str], bundle: Bundle) -> None:
    products = rng.choice(["CURRENT", "SAVINGS", "TERM"], size=sc.n_deposits, p=[0.50, 0.42, 0.08])
    types = rng.choice(["INDIVIDUAL", "OTHER", "FI", "PSE", "PLC"], size=sc.n_deposits,
                       p=[0.86, 0.09, 0.01, 0.02, 0.02])
    rows = []
    for i in range(sc.n_deposits):
        product, dtype = str(products[i]), str(types[i])
        if dtype == "INDIVIDUAL":
            avg = float(rng.lognormal(np.log(20_000), 1.7))
        else:
            avg = float(rng.lognormal(np.log(30e6), 1.5))
        rows.append({"account_id": f"{SHORT}-D{i + 1:08d}", "product": product,
                     "contract": "QARD" if product == "CURRENT" else "MUDARABAH",
                     "depositor_type": dtype, "currency": "PKR", "_avg": avg,
                     "_drift": float(rng.normal(0, 0.03)),
                     "branch_code": branches[int(rng.integers(0, len(branches)))]})
    for product, target in DEPOSIT_TARGET.items():
        group = [r for r in rows if r["product"] == product]
        factor = target / sum(r["_avg"] for r in group)
        for r in group:
            r["average_balance"] = money(r["_avg"] * factor)
            r["closing_balance"] = money(float(r["average_balance"]) * (1 + r["_drift"]))
            del r["_avg"], r["_drift"]
    # Profit rates (annual). The 75% test threshold works out at about 9.45%.
    savings_rates = {"S1": 0.0910 if sc.stressed else 0.0960, "S2": 0.0980, "S3": 0.1010}
    for r in rows:
        avg = float(r["average_balance"])
        if r["product"] == "CURRENT":
            r["tier"], rate, r["pool_id"] = "CA", 0.0, None
        elif r["product"] == "SAVINGS":
            r["tier"] = "S1" if avg < 1e6 else ("S2" if avg < 10e6 else "S3")
            rate = 0.065 if r["depositor_type"] in ("FI", "PSE", "PLC") else savings_rates[r["tier"]]
            r["pool_id"] = "GEN-PKR"
        else:
            r["tier"] = "T1Y" if avg >= 5e6 else "T3M"
            rate = 0.112 if r["tier"] == "T1Y" else 0.105
            r["pool_id"] = "SPL-CORP" if r["depositor_type"] in ("FI", "PSE", "PLC") else "GEN-PKR"
        r["profit_paid"] = money(avg * rate * sc.period_days / 365)
    bundle.deposits = rows


def _pools(sc: Scenario, bundle: Bundle) -> None:
    dep = bundle.deposits
    gen_funds = sum(float(r["average_balance"]) for r in dep if r["pool_id"] == "GEN-PKR")
    spl_funds = sum(float(r["average_balance"]) for r in dep if r["pool_id"] == "SPL-CORP")
    spec = [
        ("GEN-PKR", "General PKR Pool", "GENERAL", gen_funds * 1.08, 1.5e9, 0.50),
        ("SPL-CORP", "Special Corporate Pool", "SPECIAL", spl_funds * 1.02, 0.0, 0.55 if sc.stressed else 0.40),
        ("SCF-01", "Shariah Compliant Standing Ceiling Facility Pool", "SCF", 10e9, 0.0, 0.10),
        ("OMO-01", "Shariah Compliant OMO Pool", "OMO", 6e9, 0.0, 0.10),
    ]
    start = date(sc.period_end.year, sc.period_end.month, 1)
    announced = start - timedelta(days=1 if sc.stressed else 6)  # stressed: only one working day notice
    rows = []
    for pool_id, name, ptype, assets, fixed, mudarib in spec:
        gross = assets * GROSS_YIELD[pool_id] * sc.period_days / 365
        expenses = gross * 0.02
        net = gross - expenses
        per_rate = 0.026 if (sc.stressed and pool_id == "GEN-PKR") else (0.015 if ptype == "GENERAL" else 0.0)
        per_contribution = net * per_rate
        depositors_after_mudarib = (net - per_contribution) * (1 - mudarib)
        irr_rate = 0.013 if (sc.stressed and pool_id == "GEN-PKR") else (0.008 if ptype == "GENERAL" else 0.0)
        rows.append({
            "pool_id": pool_id, "pool_name": name, "pool_type": ptype, "currency": "PKR",
            "average_assets": money(assets), "fixed_assets_in_pool": money(fixed),
            "gross_income": money(gross), "direct_expenses": money(expenses),
            "mudarib_share": Decimal(str(mudarib)),
            "per_contribution": money(per_contribution),
            "per_balance": money(1.2e9 if ptype == "GENERAL" else 0),
            "irr_contribution": money(depositors_after_mudarib * irr_rate),
            "irr_balance": money(0.35e9 if ptype == "GENERAL" else 0),
            "weightages_announced_on": announced, "period_start": start,
        })
    bundle.pools = rows


def _capital(sc: Scenario, bundle: Bundle) -> None:
    bundle.capital = [
        {"item": "CET1_OTHER_DEDUCTIONS", "amount": money(0.3e9)},
        {"item": "AT1_INSTRUMENTS", "amount": money(0)},
        {"item": "MARKET_RISK_RWA", "amount": money(20e9 if sc.stressed else 6e9)},
        {"item": "OPERATIONAL_RISK_RWA", "amount": money(40e9 if sc.stressed else 22e9)},
        {"item": "OFF_BALANCE_EXPOSURE", "amount": money(12e9)},
        {"item": "NEW_STAGE12_PROVISIONS_NET_OF_TAX", "amount": money(0.4e9)},
        {"item": "ECL_TRANSITION_YEAR", "amount": Decimal("3")},
    ]


def build_trial_balance(bundle: Bundle, provision_required_by_branch: dict[str, Decimal]) -> None:
    """Build the GL from the detail. Called after provisions are computed by the engine."""
    sc = bundle.scenario
    branches = _branches(sc.n_branches)
    head = branches[0]
    tb: dict[tuple[str, str], list] = {}

    def post(gl: str, name: str, branch: str, amount: Decimal) -> None:
        """Positive amount is a debit, negative a credit."""
        key = (branch, gl)
        if key not in tb:
            tb[key] = [name, Decimal(0)]
        tb[key][1] += amount

    for r in bundle.financing:
        gl = MODES[r["mode"]][1]
        post(gl, f"{r['mode'].replace('_', ' ').title()} financing", r["branch_code"], r["outstanding"])
    # Banks usually hold well above the minimum (industry coverage is about 125%);
    # the stressed bank holds less than required.
    held_factor = Decimal("0.88") if sc.stressed else Decimal("1.40")
    for branch, required in provision_required_by_branch.items():
        post("1490-001", "Credit loss allowance", branch, -money(required * held_factor))
    dep_gl = {"CURRENT": ("2000-001", "Current accounts"), "SAVINGS": ("2100-001", "Savings accounts"),
              "TERM": ("2200-001", "Term deposits")}
    for r in bundle.deposits:
        gl, name = dep_gl[r["product"]]
        post(gl, name, r["branch_code"], -r["closing_balance"])

    total_fin = sum(r["outstanding"] for r in bundle.financing)
    total_dep = sum(r["closing_balance"] for r in bundle.deposits)
    per_balance = sum(p["per_balance"] for p in bundle.pools)
    irr_balance = sum(p["irr_balance"] for p in bundle.pools)
    profit_paid = sum(r["profit_paid"] for r in bundle.deposits)
    days = Decimal(sc.period_days) / Decimal(365)
    head_office = [
        ("1000-001", "Cash in hand and treasury balances", money(3.1e9)),
        ("1100-001", "Current account with SBP", money(float(total_dep) * 0.05)),
        ("1200-001", "Placements with financial institutions", money(3e9)),
        ("1350-001", "Corporate Sukuk", money(4e9)),
        ("1500-001", "Property and equipment", money(4e9)),
        ("1600-001", "Software and intangibles", money(0.4e9)),
        ("1700-001", "Advances, deposits and prepayments", money(3e9)),
        ("1800-001", "Shared premises (fixed and other)", money(1.2e9)),
        ("1950-001", "Export refinance facility (new product)", money(0.25e9)),
        ("2300-001", "Due to financial institutions", -money(6e9)),
        ("2400-001", "Subordinated Sukuk", -money(3e9)),
        ("2500-001", "PER, liability portion", -money(per_balance / 2)),
        ("2510-001", "Investment risk reserve", -money(irr_balance)),
        ("2600-001", "Charity payable", -money(15e6)),
        ("2700-001", "Other liabilities", -money(5e9)),
        ("3000-001", "Share capital", -money(10e9 if sc.stressed else 12e9)),
        ("3100-001", "Statutory reserve", -money(1.0e9 if sc.stressed else 2.5e9)),
        ("3200-001", "Other reserves", -money(0 if sc.stressed else 0.8e9)),
        ("3300-001", "PER, reserve portion", -money(per_balance / 2)),
        ("4000-001", "Profit on financing", -money(total_fin * Decimal("0.13") * days)),
        ("4200-001", "Fee and commission income", -money(0.3e9)),
        ("4300-001", "Charity received booked as income", -money(12e6 if sc.stressed else 0)),
        ("5000-001", "Profit expense on deposits", money(profit_paid)),
        ("5100-001", "Operating expenses", money(0.32e9)),
        ("5200-001", "Credit loss charge", money(0.06e9)),
    ]
    for gl, name, amount in head_office:
        if amount != 0:
            post(gl, name, head, amount)
    # Surplus funds are invested in GoP Ijarah Sukuk, so the Sukuk holding is the
    # balancing asset. Solve exactly: imbalance + sukuk - sukuk income - unappropriated = 0.
    imbalance = sum(v[1] for v in tb.values())
    unappropriated = Decimal(0.5e9 if sc.stressed else 1.6e9)
    k = Decimal("0.115") * days
    sukuk = money((unappropriated - imbalance) / (1 - k))
    sukuk_income = money(sukuk * k)
    post("1300-001", "GoP Ijarah Sukuk", head, sukuk)
    post("4100-001", "Profit on investments", head, -sukuk_income)
    rest = sum(v[1] for v in tb.values())
    post("3400-001", "Unappropriated profit", head, -rest)  # exact balancing figure, about the target
    bundle.trial_balance = [
        {"branch_code": branch, "gl_code": gl, "gl_name": name, "currency": "PKR",
         "debit": amount if amount > 0 else Decimal(0), "credit": -amount if amount < 0 else Decimal(0)}
        for (branch, gl), (name, amount) in sorted(tb.items())
    ]
