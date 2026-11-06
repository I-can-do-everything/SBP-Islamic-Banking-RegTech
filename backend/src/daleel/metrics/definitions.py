"""Regulatory metric definitions.

Each function below is one number on the results screen. Every one records how
it was calculated (formula and explanation in plain words), what went in, and
the rules used. Units: percent values are stored as percentages (11.5 = 11.5%).

Sources for every threshold are in rulebook/rules.yaml and
docs/05-regulatory-verification.md.
"""

from __future__ import annotations

from decimal import Decimal

from daleel.core.money import HUNDRED, ZERO, pct, q_amount, q_ratio
from daleel.metrics.engine import Context, MetricResult, metric


def res(value: Decimal | None, status: str = "INFO", **kw) -> MetricResult:
    if value is not None and not isinstance(value, Decimal):
        value = Decimal(value)
    return MetricResult("", "", "", "", value, status, **kw)


def na(reason: str) -> MetricResult:
    return MetricResult("", "", "", "", None, "NOT_AVAILABLE", notes=[reason])


def money_table(columns: list[str], rows: list[tuple]) -> dict:
    return {"columns": columns, "rows": [[None if v is None else str(v) for v in r] for r in rows]}


def annualise(ctx: Context) -> Decimal:
    return Decimal(365) / Decimal(ctx.period_days)


# ------------------------------------------------------------------ balance sheet

@metric("bs.total_assets", "Balance sheet", "Total assets", "pkr")
def total_assets(ctx: Context) -> MetricResult:
    if not ctx.has("TRIAL_BALANCE"):
        return na("The trial balance was not supplied.")
    gross = ctx.scalar("SELECT sum(presented) FROM gold WHERE grp IN ('ASSETS', 'FINANCING') AND code <> 'A.PROV'")
    # The credit loss allowance is a contra asset (normally a credit balance), so it is deducted.
    prov = ctx.gold("A.PROV")
    return res(q_amount(gross - prov), formula="Assets + financing - credit loss allowance",
               explanation="Sum of all asset reporting codes, with the credit loss allowance deducted.")


@metric("bs.gross_financing_gl", "Balance sheet", "Gross financing per general ledger", "pkr")
def gross_financing_gl(ctx: Context) -> MetricResult:
    if not ctx.has("TRIAL_BALANCE"):
        return na("The trial balance was not supplied.")
    rows = ctx.con.execute("SELECT code, label, presented FROM gold WHERE grp = 'FINANCING' ORDER BY code").fetchall()
    return res(q_amount(ctx.gold_group("FINANCING")), formula="Sum of financing reporting codes",
               explanation="Total Islamic financing before provisions, from the general ledger.",
               table=money_table(["Code", "Label", "Amount (PKR)"], rows))


@metric("bs.total_deposits_gl", "Balance sheet", "Total deposits per general ledger", "pkr")
def total_deposits_gl(ctx: Context) -> MetricResult:
    if not ctx.has("TRIAL_BALANCE"):
        return na("The trial balance was not supplied.")
    return res(q_amount(ctx.gold_group("DEPOSITS")), formula="Current + savings + term deposits")


@metric("pl.net_profit_period", "Balance sheet", "Net profit for the period", "pkr")
def net_profit(ctx: Context) -> MetricResult:
    if not ctx.has("TRIAL_BALANCE"):
        return na("The trial balance was not supplied.")
    income, expense = ctx.gold_group("INCOME"), ctx.gold_group("EXPENSE")
    return res(q_amount(income - expense), formula="Income - expenses",
               inputs=[{"label": "Income", "value": str(income), "unit": "pkr"},
                       {"label": "Expenses", "value": str(expense), "unit": "pkr"}])


@metric("bs.equity", "Balance sheet", "Shareholders' equity including period profit", "pkr",
        deps=("pl.net_profit_period",))
def equity(ctx: Context) -> MetricResult:
    eq = ctx.gold_group("EQUITY")
    return res(q_amount(eq + ctx.value("pl.net_profit_period")),
               formula="Equity reporting codes + net profit for the period")


# ------------------------------------------------------------------ asset quality

@metric("aq.gross_financing", "Asset quality", "Gross financing (contract level)", "pkr",
        rules=("asset_quality.classification",))
def gross_financing(ctx: Context) -> MetricResult:
    if not ctx.has("FINANCING"):
        return na("The financing portfolio was not supplied.")
    rows = ctx.con.execute("""
        SELECT stage, count(*), sum(outstanding), sum(provision_required)
        FROM contracts GROUP BY stage ORDER BY stage""").fetchall()
    return res(q_amount(ctx.scalar("SELECT sum(outstanding) FROM contracts")),
               formula="Sum of outstanding on every financing contract",
               explanation="Every contract is classified by days past due using SBP's Annexure C bands "
                           "for its portfolio, which also sets its IFRS 9 stage.",
               table=money_table(["Stage", "Contracts", "Outstanding (PKR)", "Provision required (PKR)"], rows))


@metric("aq.npf_amount", "Asset quality", "Non performing financing", "pkr", deps=("aq.gross_financing",),
        rules=("asset_quality.classification",))
def npf_amount(ctx: Context) -> MetricResult:
    rows = ctx.con.execute("""
        SELECT portfolio, classification, count(*), sum(outstanding) FROM contracts
        WHERE stage = 3 GROUP BY 1, 2 ORDER BY 4 DESC""").fetchall()
    return res(q_amount(ctx.scalar("SELECT sum(outstanding) FROM contracts WHERE stage = 3")),
               formula="Sum of outstanding where the contract is in Stage 3 (substandard, doubtful or loss)",
               table=money_table(["Portfolio", "Classification", "Contracts", "Outstanding (PKR)"], rows))


@metric("aq.npf_ratio", "Asset quality", "NPF ratio", "percent",
        deps=("aq.npf_amount", "aq.gross_financing"), rules=("asset_quality.npf_alert",))
def npf_ratio(ctx: Context) -> MetricResult:
    value = q_ratio(pct(ctx.value("aq.npf_amount"), ctx.value("aq.gross_financing")))
    alert = ctx.rule("asset_quality.npf_alert").value
    status = "INFO" if value is None else ("WARNING" if value > alert else "PASS")
    return res(value, status, formula="Non performing financing / gross financing x 100",
               threshold={"type": "max", "value": str(alert), "kind": "internal alert"},
               explanation="SBP sets no single maximum NPF ratio. Daleel flags ratios above an internal "
                           "alert level so they get attention.")


@metric("aq.provision_required", "Asset quality", "Provision required", "pkr", deps=("aq.gross_financing",),
        rules=("asset_quality.pr_provision_rate", "asset_quality.stage3_floor", "asset_quality.default_lgd",
               "asset_quality.default_pd"))
def provision_required(ctx: Context) -> MetricResult:
    rows = ctx.con.execute("""
        SELECT stage, sum(ecl), sum(pr_required), sum(provision_required) FROM contracts
        GROUP BY stage ORDER BY stage""").fetchall()
    defaulted = ctx.scalar("SELECT count(*) FROM contracts WHERE pd_defaulted OR lgd_defaulted")
    notes = []
    if defaulted:
        notes.append(f"{defaulted} contracts had no PD or LGD from the bank; rulebook defaults were used.")
    return res(q_amount(ctx.scalar("SELECT sum(provision_required) FROM contracts")),
               formula="Stage 1 and 2: ECL. Stage 3: higher of ECL and the Prudential Regulations provision",
               explanation="ECL = PD x LGD x exposure. The PR provision is the classification rate applied to "
                           "outstanding less the forced sale value of collateral.",
               table=money_table(["Stage", "ECL (PKR)", "PR provision (PKR)", "Required (PKR)"], rows),
               notes=notes)


@metric("aq.ecl_stage12", "Asset quality", "Stage 1 and 2 ECL", "pkr", deps=("aq.gross_financing",))
def ecl_stage12(ctx: Context) -> MetricResult:
    return res(q_amount(ctx.scalar("SELECT sum(ecl) FROM contracts WHERE stage IN (1, 2)")),
               formula="Sum of ECL on Stage 1 and Stage 2 contracts")


@metric("aq.provision_held", "Asset quality", "Provision held (credit loss allowance)", "pkr")
def provision_held(ctx: Context) -> MetricResult:
    if not ctx.has("TRIAL_BALANCE"):
        return na("The trial balance was not supplied.")
    return res(q_amount(ctx.gold("A.PROV")), formula="Credit loss allowance per general ledger")


@metric("aq.provision_gap", "Asset quality", "Provision surplus or shortfall", "pkr",
        deps=("aq.provision_held", "aq.provision_required"), rules=("asset_quality.stage3_floor",))
def provision_gap(ctx: Context) -> MetricResult:
    gap = ctx.value("aq.provision_held") - ctx.value("aq.provision_required")
    status = "FAIL" if gap < 0 else "PASS"
    return res(q_amount(gap), status, formula="Provision held - provision required",
               threshold={"type": "min", "value": "0"},
               explanation="A negative figure means the bank holds less than the required provision.")


@metric("aq.coverage", "Asset quality", "Provision coverage of NPF", "percent",
        deps=("aq.provision_held", "aq.npf_amount"))
def coverage(ctx: Context) -> MetricResult:
    return res(q_ratio(pct(ctx.value("aq.provision_held"), ctx.value("aq.npf_amount"))),
               formula="Provision held / non performing financing x 100")


# ------------------------------------------------------------------ capital

@metric("cap.cet1", "Capital", "Common Equity Tier 1 capital", "pkr", deps=("bs.equity", "aq.gross_financing"),
        rules=("capital.ecl_transition_addback",))
def cet1(ctx: Context) -> MetricResult:
    equity_value = ctx.value("bs.equity")
    intangibles = ctx.gold("A.INTANG")
    other = ctx.memo("CET1_OTHER_DEDUCTIONS")
    year = int(ctx.memo("ECL_TRANSITION_YEAR"))
    table = ctx.rule("capital.ecl_transition_addback").table
    share = table.get(str(year), Decimal(0)) / HUNDRED if year else Decimal(0)
    addback = q_amount(ctx.memo("NEW_STAGE12_PROVISIONS_NET_OF_TAX") * share)
    value = equity_value - intangibles - other + addback
    return res(q_amount(value),
               formula="Equity - intangibles - other CET1 deductions + IFRS 9 transitional add back",
               explanation=f"Transition year {year or 'none'}: {share * 100:.0f}% of new Stage 1 and 2 "
                           "provisions are added back, per SBP's IFRS 9 Annexure B.",
               inputs=[{"label": "Intangibles deducted", "value": str(intangibles), "unit": "pkr"},
                       {"label": "Other CET1 deductions", "value": str(other), "unit": "pkr"},
                       {"label": "Transitional add back", "value": str(addback), "unit": "pkr"}])


@metric("cap.tier1", "Capital", "Tier 1 capital", "pkr", deps=("cap.cet1",))
def tier1(ctx: Context) -> MetricResult:
    at1 = ctx.memo("AT1_INSTRUMENTS")
    return res(q_amount(ctx.value("cap.cet1") + at1), formula="CET1 + Additional Tier 1",
               inputs=[{"label": "Additional Tier 1", "value": str(at1), "unit": "pkr"}])


@metric("cap.credit_rwa", "Capital", "Credit risk weighted assets", "pkr", deps=("aq.gross_financing",),
        rules=("capital.risk_weights",))
def credit_rwa(ctx: Context) -> MetricResult:
    weights = ctx.rule("capital.risk_weights").table
    case = " ".join(f"WHEN '{k}' THEN CAST('{v / 100}' AS DECIMAL(18,10))" for k, v in weights.items())
    fin = ctx.con.execute(f"""
        SELECT rw_class, sum(outstanding - CASE WHEN stage = 3 THEN provision_required ELSE 0 END),
               sum((outstanding - CASE WHEN stage = 3 THEN provision_required ELSE 0 END) * CASE rw_class {case} END)
        FROM contracts GROUP BY 1 ORDER BY 3 DESC""").fetchall()
    gl = ctx.con.execute(f"""
        SELECT rw, sum(presented), sum(presented * CASE rw {case} END) FROM gold
        WHERE rw IS NOT NULL GROUP BY 1 ORDER BY 3 DESC""").fetchall() if ctx.has("TRIAL_BALANCE") else []
    rows = [("Financing: " + r[0], r[1], r[2]) for r in fin] + [("Other assets: " + r[0], r[1], r[2]) for r in gl]
    total = sum((Decimal(r[2]) for r in rows), ZERO)
    return res(q_amount(total), formula="Sum of (exposure x risk weight); financing net of specific provisions",
               explanation="Standardised approach. Stage 3 financing is shown net of its specific provision "
                           "and weighted as past due.",
               table=money_table(["Exposure class", "Exposure (PKR)", "RWA (PKR)"],
                                 [(a, q_amount(Decimal(b)), q_amount(Decimal(c))) for a, b, c in rows]))


@metric("cap.tier2", "Capital", "Tier 2 capital", "pkr", deps=("cap.credit_rwa", "aq.ecl_stage12"),
        rules=("capital.tier2_provision_cap",))
def tier2(ctx: Context) -> MetricResult:
    sukuk = ctx.gold("L.SUKUK_SUB")
    cap_rate = ctx.rule("capital.tier2_provision_cap").value / HUNDRED
    cap = q_amount(ctx.value("cap.credit_rwa") * cap_rate)
    general = min(ctx.value("aq.ecl_stage12"), cap)
    return res(q_amount(sukuk + general),
               formula="Subordinated Sukuk + Stage 1 and 2 provisions (capped at 1.25% of credit RWA)",
               inputs=[{"label": "Subordinated Sukuk", "value": str(sukuk), "unit": "pkr"},
                       {"label": "Provisions admitted", "value": str(general), "unit": "pkr"},
                       {"label": "Cap (1.25% of credit RWA)", "value": str(cap), "unit": "pkr"}])


@metric("cap.total_rwa", "Capital", "Total risk weighted assets", "pkr", deps=("cap.credit_rwa",))
def total_rwa(ctx: Context) -> MetricResult:
    market, oper = ctx.memo("MARKET_RISK_RWA"), ctx.memo("OPERATIONAL_RISK_RWA")
    notes = [] if ctx.has("CAPITAL") else ["Capital memo not supplied: market and operational risk RWA are zero."]
    return res(q_amount(ctx.value("cap.credit_rwa") + market + oper),
               formula="Credit RWA + market risk RWA + operational risk RWA",
               inputs=[{"label": "Market risk RWA", "value": str(market), "unit": "pkr"},
                       {"label": "Operational risk RWA", "value": str(oper), "unit": "pkr"}], notes=notes)


def _ratio_status(value: Decimal | None, minimum: Decimal, buffer: Decimal | None = None) -> str:
    if value is None:
        return "INFO"
    if value < minimum:
        return "FAIL"
    if buffer is not None and value < minimum + buffer:
        return "WARNING"
    return "PASS"


@metric("cap.cet1_ratio", "Capital", "CET1 ratio", "percent", deps=("cap.cet1", "cap.total_rwa"),
        rules=("capital.cet1_min", "capital.ccb"))
def cet1_ratio(ctx: Context) -> MetricResult:
    value = q_ratio(pct(ctx.value("cap.cet1"), ctx.value("cap.total_rwa")))
    minimum, ccb = ctx.rule("capital.cet1_min").value, ctx.rule("capital.ccb").value
    return res(value, _ratio_status(value, minimum, ccb), formula="CET1 / total RWA x 100",
               threshold={"type": "min", "value": str(minimum), "buffer": str(ccb)},
               explanation="Below the minimum is a breach. Between the minimum and minimum plus the capital "
                           "conservation buffer, distributions are restricted.")


@metric("cap.tier1_ratio", "Capital", "Tier 1 ratio", "percent", deps=("cap.tier1", "cap.total_rwa"),
        rules=("capital.tier1_min",))
def tier1_ratio(ctx: Context) -> MetricResult:
    value = q_ratio(pct(ctx.value("cap.tier1"), ctx.value("cap.total_rwa")))
    minimum = ctx.rule("capital.tier1_min").value
    return res(value, _ratio_status(value, minimum), formula="Tier 1 / total RWA x 100",
               threshold={"type": "min", "value": str(minimum)})


@metric("cap.car", "Capital", "Capital adequacy ratio (CAR)", "percent",
        deps=("cap.tier1", "cap.tier2", "cap.total_rwa"),
        rules=("capital.total_min_ex_buffer", "capital.ccb"))
def car(ctx: Context) -> MetricResult:
    total = ctx.value("cap.tier1") + ctx.value("cap.tier2")
    value = q_ratio(pct(total, ctx.value("cap.total_rwa")))
    minimum, ccb = ctx.rule("capital.total_min_ex_buffer").value, ctx.rule("capital.ccb").value
    return res(value, _ratio_status(value, minimum, ccb), formula="(Tier 1 + Tier 2) / total RWA x 100",
               threshold={"type": "min", "value": str(minimum), "buffer": str(ccb),
                          "with_buffer": str(minimum + ccb)},
               inputs=[{"label": "Total capital", "value": str(q_amount(total)), "unit": "pkr"}],
               explanation="Minimum total capital ratio plus the capital conservation buffer gives the "
                           "headline requirement.")


@metric("cap.leverage", "Capital", "Leverage ratio", "percent", deps=("cap.tier1", "bs.total_assets"),
        rules=("capital.leverage_min",))
def leverage(ctx: Context) -> MetricResult:
    off = ctx.memo("OFF_BALANCE_EXPOSURE")
    exposure = ctx.value("bs.total_assets") + off
    value = q_ratio(pct(ctx.value("cap.tier1"), exposure))
    minimum = ctx.rule("capital.leverage_min").value
    return res(value, _ratio_status(value, minimum), formula="Tier 1 / (total assets + off balance sheet exposure) x 100",
               threshold={"type": "min", "value": str(minimum)},
               inputs=[{"label": "Off balance sheet exposure", "value": str(off), "unit": "pkr"}])


# ------------------------------------------------------------------ pools

def _yield_rows(ctx: Context) -> list[tuple]:
    excluded = ctx.rule("pools.wagy_excluded_pool_types").items
    drop_fixed = ctx.rule("pools.wagy_excludes_fixed_assets").value == 1
    assets = "average_assets - coalesce(fixed_assets_in_pool, 0)" if drop_fixed else "average_assets"
    factor = annualise(ctx)
    rows = ctx.con.execute(f"""
        SELECT pool_id, pool_type, gross_income, {assets} AS assets,
               pool_type IN ({','.join("'" + e + "'" for e in excluded)}) AS excluded
        FROM pools ORDER BY pool_id""").fetchall()
    out = []
    for pool_id, ptype, income, assets_value, excluded_flag in rows:
        y = pct(Decimal(income), Decimal(assets_value))
        out.append((pool_id, ptype, Decimal(income), Decimal(assets_value),
                    None if y is None else q_ratio(y * factor), bool(excluded_flag)))
    return out


@metric("pool.wagy", "Profit distribution", "Weighted average gross yield of pools (annualised)", "percent",
        rules=("pools.wagy_excluded_pool_types", "pools.wagy_excludes_fixed_assets"))
def wagy(ctx: Context) -> MetricResult:
    if not ctx.has("POOLS"):
        return na("Pool data was not supplied.")
    rows = _yield_rows(ctx)
    eligible = [r for r in rows if not r[5]]
    income = sum((r[2] for r in eligible), ZERO)
    assets = sum((r[3] for r in eligible), ZERO)
    value = pct(income, assets)
    value = None if value is None else q_ratio(value * annualise(ctx))
    return res(value, formula="Sum of eligible pool gross income / sum of eligible average pool assets, "
                              "annualised (365 / days in period)",
               explanation="Weighting each pool's yield by its assets is the same as dividing total income by "
                           "total assets. Standing ceiling facility and OMO pools are left out, as IFPD "
                           "Circular No. 09 of 2024 requires.",
               table=money_table(["Pool", "Type", "Gross income (PKR)", "Average assets (PKR)",
                                  "Gross yield % (annualised)", "Excluded"],
                                 [(a, b, c, d, e, "yes" if f else "no") for a, b, c, d, e, f in rows]))


@metric("pool.savings_min_rate", "Profit distribution", "Minimum savings profit rate (75% of WAGY)", "percent",
        deps=("pool.wagy",), rules=("pools.savings_min_share_of_wagy",))
def savings_min(ctx: Context) -> MetricResult:
    share = ctx.rule("pools.savings_min_share_of_wagy").value / HUNDRED
    return res(q_ratio(ctx.value("pool.wagy") * share), formula="Weighted average gross yield x 75%")


@metric("pool.savings_lowest_rate", "Profit distribution", "Lowest savings tier profit rate (eligible depositors)",
        "percent", deps=("pool.savings_min_rate",), rules=("pools.excluded_depositor_types",
                                                           "pools.savings_min_share_of_wagy"))
def savings_lowest(ctx: Context) -> MetricResult:
    if not ctx.has("DEPOSITS"):
        return na("Deposit data was not supplied.")
    excluded = ctx.rule("pools.excluded_depositor_types").items
    factor = annualise(ctx)
    rows = ctx.con.execute(f"""
        SELECT coalesce(tier, 'ALL') AS tier, count(*), sum(average_balance), sum(profit_paid)
        FROM deposits WHERE product = 'SAVINGS' AND currency = 'PKR'
          AND depositor_type NOT IN ({','.join("'" + e + "'" for e in excluded)})
        GROUP BY 1 ORDER BY 1""").fetchall()
    minimum = ctx.value("pool.savings_min_rate")
    table, lowest = [], None
    for tier, n, avg, profit in rows:
        rate = pct(Decimal(profit), Decimal(avg))
        rate = None if rate is None else q_ratio(rate * factor)
        table.append((tier, n, avg, profit, rate, "below" if rate is not None and rate < minimum else "ok"))
        if rate is not None and (lowest is None or rate < lowest):
            lowest = rate
    status = "INFO" if lowest is None else ("FAIL" if lowest < minimum else "PASS")
    below_accounts = ctx.scalar(f"""
        SELECT count(*) FROM deposits WHERE product = 'SAVINGS' AND currency = 'PKR' AND average_balance > 0
          AND depositor_type NOT IN ({','.join("'" + e + "'" for e in excluded)})
          AND profit_paid / average_balance * 100 * {factor} < {minimum}""")
    return res(lowest, status, formula="Profit paid / average balance x 365 / days, per savings tier; lowest tier",
               threshold={"type": "min", "value": str(minimum), "source_metric": "pool.savings_min_rate"},
               explanation="PKR savings deposits of individuals and other eligible depositors must earn at least "
                           "75% of the weighted average gross yield. Deposits of financial institutions, public "
                           "sector enterprises and public limited companies are excluded.",
               table=money_table(["Tier", "Accounts", "Average balance (PKR)", "Profit paid (PKR)",
                                  "Rate % (annualised)", "Against minimum"], table),
               inputs=[{"label": "Eligible accounts below the minimum rate", "value": str(below_accounts),
                        "unit": "count"}])


@metric("pool.mudarib_share_max", "Profit distribution", "Highest Mudarib share across pools", "percent",
        rules=("pools.mudarib_share_max",))
def mudarib(ctx: Context) -> MetricResult:
    if not ctx.has("POOLS"):
        return na("Pool data was not supplied.")
    rows = ctx.con.execute("SELECT pool_id, pool_type, mudarib_share * 100 FROM pools ORDER BY 3 DESC").fetchall()
    limit = ctx.rule("pools.mudarib_share_max").value
    top = q_ratio(Decimal(rows[0][2]))
    return res(top, "FAIL" if top > limit else "PASS", formula="Maximum of each pool's Mudarib share",
               threshold={"type": "max", "value": str(limit)},
               table=money_table(["Pool", "Type", "Mudarib share %"], rows))


@metric("pool.per_contribution_max", "Profit distribution", "Highest PER contribution as % of pool net income",
        "percent", rules=("pools.per_monthly_contribution_max",))
def per_contribution(ctx: Context) -> MetricResult:
    if not ctx.has("POOLS"):
        return na("Pool data was not supplied.")
    rows = ctx.con.execute("""SELECT pool_id, gross_income - coalesce(direct_expenses, 0), per_contribution
                              FROM pools ORDER BY pool_id""").fetchall()
    table, top = [], ZERO
    for pool_id, net, per in rows:
        share = pct(Decimal(per), Decimal(net)) or ZERO
        table.append((pool_id, net, per, q_ratio(share)))
        top = max(top, share)
    limit = ctx.rule("pools.per_monthly_contribution_max").value
    return res(q_ratio(top), "FAIL" if top > limit else "PASS",
               formula="PER contribution / (gross income - direct expenses) x 100, highest pool",
               threshold={"type": "max", "value": str(limit)},
               table=money_table(["Pool", "Net income (PKR)", "PER contribution (PKR)", "Share %"], table))


@metric("pool.per_balance_to_equity", "Profit distribution", "PER balance as % of equity", "percent",
        deps=("bs.equity",), rules=("pools.per_balance_max_of_equity",))
def per_balance(ctx: Context) -> MetricResult:
    if not ctx.has("POOLS"):
        return na("Pool data was not supplied.")
    balance = ctx.scalar("SELECT sum(per_balance) FROM pools")
    value = q_ratio(pct(balance, ctx.value("bs.equity")))
    limit = ctx.rule("pools.per_balance_max_of_equity").value
    return res(value, "INFO" if value is None else ("FAIL" if value > limit else "PASS"),
               formula="Total PER balance / equity x 100", threshold={"type": "max", "value": str(limit)},
               inputs=[{"label": "PER balance", "value": str(balance), "unit": "pkr"}])


@metric("pool.irr_contribution_max", "Profit distribution",
        "Highest IRR contribution as % of depositors' profit after Mudarib share", "percent",
        rules=("pools.irr_contribution_max",))
def irr_contribution(ctx: Context) -> MetricResult:
    if not ctx.has("POOLS"):
        return na("Pool data was not supplied.")
    rows = ctx.con.execute("""
        SELECT pool_id, (gross_income - coalesce(direct_expenses, 0) - coalesce(per_contribution, 0))
                        * (1 - mudarib_share), irr_contribution FROM pools ORDER BY pool_id""").fetchall()
    table, top = [], ZERO
    for pool_id, depositors, irr in rows:
        share = pct(Decimal(irr), Decimal(depositors)) or ZERO
        table.append((pool_id, q_amount(Decimal(depositors)), irr, q_ratio(share)))
        top = max(top, share)
    limit = ctx.rule("pools.irr_contribution_max").value
    return res(q_ratio(top), "FAIL" if top > limit else "PASS",
               formula="IRR contribution / ((net income - PER contribution) x (1 - Mudarib share)) x 100",
               threshold={"type": "max", "value": str(limit)},
               table=money_table(["Pool", "Depositors' profit after Mudarib (PKR)", "IRR contribution (PKR)",
                                  "Share %"], table))


@metric("pool.weightage_notice", "Profit distribution", "Shortest weightage notice (working days)", "days",
        rules=("pools.weightage_notice_working_days",))
def weightage_notice(ctx: Context) -> MetricResult:
    if not ctx.has("POOLS"):
        return na("Pool data was not supplied.")
    rows = ctx.con.execute("""
        SELECT pool_id, weightages_announced_on, period_start FROM pools
        WHERE weightages_announced_on IS NOT NULL AND period_start IS NOT NULL ORDER BY pool_id""").fetchall()
    if not rows:
        return na("Announcement dates were not supplied.")
    table, low = [], None
    for pool_id, announced, start in rows:
        # Working days strictly between announcement and period start (Saturday and Sunday are off).
        days = sum(1 for n in range(1, (start - announced).days)
                   if (announced.toordinal() + n) % 7 not in (6, 0))
        table.append((pool_id, announced, start, days))
        low = days if low is None else min(low, days)
    limit = ctx.rule("pools.weightage_notice_working_days").value
    return res(Decimal(low), "FAIL" if low < limit else "PASS",
               formula="Working days between the announcement date and the first day of the period",
               threshold={"type": "min", "value": str(limit)},
               table=money_table(["Pool", "Announced on", "Period starts", "Working days"], table),
               notes=["Public holidays are not taken into account."])
