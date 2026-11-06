"""Writes the synthetic bank as a messy, realistic export workbook.

Real core banking extracts are rarely clean. This writer reproduces the problems
found in the prototype audit (docs/02-bug-register.md) so the ingestion engine
must handle each one, and the demo can show the before and after:

- title rows above the header, blank rows, a repeated header row (page break)
  and a TOTAL row at the bottom
- T24 style dotted headers (GL.ACCOUNT.CODE) and Flexcube style names
- amounts as text with thousands separators, "-" for zero, a "DR" suffix,
  and one value in scientific notation (BUG-002, BUG-003)
- dates as dd/mm/yyyy (BUG-009)
- product and segment names spelled in several ways
- PDs written as "1.25%" or as fractions
- an unmapped new GL account (BUG-022)
- stressed scenario only: one unreadable cell (#REF!) that must be rejected,
  never turned into zero (BUG-004)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import xlsxwriter

from daleel.datagen.generator import INSTITUTION, Bundle, Scenario, build_trial_balance, generate
from daleel.metrics.credit import enrich_contracts
from daleel.rulebook.rulebook import load_rulebook

MODE_SPELLING = {
    "DIMINISHING_MUSHARAKAH": ["Diminishing Musharaka", "DM", "DIMINISHING MUSHARAKAH"],
    "MUSHARAKAH": ["Musharaka", "MUSHARAKAH"], "RUNNING_MUSHARAKAH": ["Running Musharakah", "RM"],
    "ISTISNA": ["Istisna", "ISTISNAA"], "MURABAHA": ["Murabaha", "MUR"], "IJARAH": ["Ijara", "IJA"],
    "TIJARAH": ["Tijarah", "TIJ"], "SALAM": ["Salam", "SAL"], "OTHER": ["Other"],
}
SEGMENT_SPELLING = {
    "CORPORATE": ["Corporate", "CORP"], "INFRASTRUCTURE": ["Infra"], "SME_MEDIUM": ["ME", "Medium Enterprise"],
    "SME_SMALL": ["SE", "Small Enterprise"], "HOUSING": ["Home Finance", "Housing"],
    "CONSUMER_AUTO": ["Auto Finance", "Auto"], "CONSUMER_PERSONAL": ["Personal"],
    "AGRI_PRODUCTION": ["Agri", "Agriculture"], "AGRI_DEVELOPMENT": ["Agri Development"],
}
EXPOSURE_SPELLING = {"CORPORATE": "CORP", "SME": "SME", "MORTGAGE": "HOUSING", "RETAIL": "RETAIL",
                     "SOVEREIGN_PKR": "GOP"}
DEP_PRODUCT = {"CURRENT": "CA", "SAVINGS": "SA", "TERM": "TD"}
DEP_BASIS = {"QARD": "Qard-e-Hasan", "MUDARABAH": "Mudaraba"}
DEP_SEGMENT = {"INDIVIDUAL": "Retail", "OTHER": "Corporate", "FI": "Bank", "PSE": "Public Sector",
               "PLC": "Public Limited"}
POOL_TYPE = {"GENERAL": "General Pool", "SPECIAL": "Special Pool", "SCF": "Standing Ceiling Facility",
             "OMO": "OMO Pool"}


def fmt_amount(value: Decimal) -> str:
    if value == 0:
        return "-"
    return f"{value:,.2f}"


def ddmmyyyy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def provisions_by_branch(bundle: Bundle) -> dict[str, Decimal]:
    """Run the real credit engine on the generated contracts, so the GL matches it."""
    sc = bundle.scenario
    con = duckdb.connect()
    con.execute("""CREATE TABLE fin (contract_id VARCHAR, portfolio VARCHAR, counterparty_type VARCHAR,
        outstanding DECIMAL(38,4), days_past_due INTEGER, collateral_fsv DECIMAL(38,4),
        pd_12m DECIMAL(18,10), pd_lifetime DECIMAL(18,10), lgd DECIMAL(18,10), branch_code VARCHAR)""")
    con.executemany("INSERT INTO fin VALUES (?,?,?,?,?,?,?,?,?,?)", [
        (r["contract_id"], r["portfolio"], r["counterparty_type"], r["outstanding"], r["days_past_due"],
         r["collateral_fsv"], None if r["pd_12m"] is None else Decimal(str(r["pd_12m"])),
         None if r["pd_lifetime"] is None else Decimal(str(r["pd_lifetime"])),
         Decimal(str(r["lgd"])), r["branch_code"]) for r in bundle.financing])
    enrich_contracts(con, "fin", load_rulebook(), sc.period_end)
    rows = con.execute(
        "SELECT branch_code, sum(provision_required) FROM contracts GROUP BY 1").fetchall()
    return {b: Decimal(v) for b, v in rows}


def build_sample(scenario: Scenario, out_path: Path) -> dict:
    bundle = generate(scenario)
    build_trial_balance(bundle, provisions_by_branch(bundle))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(str(out_path), {"strings_to_numbers": False})
    bold = wb.add_format({"bold": True})
    stressed = scenario.stressed
    planted: list[str] = []

    # INFO sheet (metadata a reporting officer usually puts on the first tab)
    ws = wb.add_worksheet("INFO")
    info = [("Institution", INSTITUTION), ("Report", "Monthly regulatory extract"),
            ("Period end", ddmmyyyy(scenario.period_end)), ("Period days", str(scenario.period_days)),
            ("Currency", "PKR"), ("Note", "Synthetic data for a fictional bank. Not real.")]
    for i, (k, v) in enumerate(info):
        ws.write(i, 0, k, bold)
        ws.write(i, 1, v)

    # Trial balance in T24 style
    ws = wb.add_worksheet("TB_EXPORT")
    ws.write(0, 0, INSTITUTION.upper(), bold)
    ws.write(1, 0, f"TRIAL BALANCE AS AT {ddmmyyyy(scenario.period_end)} (T24 GL EXTRACT)")
    header = ["CO.CODE", "GL.ACCOUNT.CODE", "ACCOUNT.DESC", "CCY", "DR.BAL", "CR.BAL"]
    row = 3
    ws.write_row(row, 0, header, bold)
    row += 1
    total_dr = total_cr = Decimal(0)
    for i, r in enumerate(bundle.trial_balance):
        if i == 180:  # page break in the export repeats the header
            ws.write_row(row, 0, header, bold)
            row += 1
            planted.append("Repeated header row in the trial balance (page break)")
        dr, cr = fmt_amount(r["debit"]), fmt_amount(r["credit"])
        if r["gl_code"] == "1300-001" and r["debit"] > 0:
            # Full precision scientific notation (an earlier 7 digit version lost 332.12 and the
            # trial balance check caught it: see docs/03-fix-log.md, FIX-003).
            dr = format(r["debit"].normalize(), "E")
            planted.append("Scientific notation amount (GoP Ijarah Sukuk)")
        if r["gl_code"] == "1700-001" and r["debit"] > 0:
            dr = f"{r['debit']:,.2f} DR"
            planted.append("Amount with a DR suffix")
        ws.write_row(row, 0, [r["branch_code"], r["gl_code"], r["gl_name"], r["currency"], dr, cr])
        total_dr += r["debit"]
        total_cr += r["credit"]
        row += 1
        if i == 260:
            row += 1  # a blank row in the middle
    ws.write_row(row + 1, 0, ["", "TOTAL", "", "", fmt_amount(total_dr), fmt_amount(total_cr)], bold)
    planted += ["Title rows above the header", "TOTAL row at the bottom",
                "Unmapped new GL account 1950-001 (export refinance)"]

    # Financing in Flexcube style
    ws = wb.add_worksheet("LD_PORTFOLIO")
    ws.write(0, 0, "LOANS AND FINANCING PORTFOLIO (FCUBS EXTRACT)", bold)
    header = ["CONTRACT_NO", "CUSTOMER_NO", "PRODUCT", "SEGMENT", "EXPOSURE_CLASS", "CCY", "OS_BALANCE",
              "DPD", "FSV", "PD12", "PD_LT", "LGD", "POOL", "BRANCH", "MATURITY"]
    ws.write_row(2, 0, header, bold)
    for i, r in enumerate(bundle.financing):
        spellings = MODE_SPELLING[r["mode"]]
        segments = SEGMENT_SPELLING[r["portfolio"]]
        pd12 = "" if r["pd_12m"] is None else f"{r['pd_12m'] * 100:.4f}%"
        pd_lt = "" if r["pd_lifetime"] is None else f"{r['pd_lifetime']:.6f}"
        ws.write_row(3 + i, 0, [
            r["contract_id"], r["customer_ref"], spellings[i % len(spellings)],
            segments[i % len(segments)], EXPOSURE_SPELLING[r["counterparty_type"]], r["currency"],
            fmt_amount(r["outstanding"]), str(r["days_past_due"]), fmt_amount(r["collateral_fsv"]),
            pd12, pd_lt, f"{r['lgd'] * 100:.2f}", r["pool_id"], r["branch_code"],
            ddmmyyyy(r["maturity_date"])])
    planted += ["Mixed spellings of modes and segments", "PDs as percentages and fractions",
                "LGD written as a percentage", "Dates as dd/mm/yyyy"]

    # Deposits
    ws = wb.add_worksheet("DEPOSIT_AVG")
    header = ["ACCOUNT_NO", "ACCOUNT_TYPE", "BASIS", "CUSTOMER_SEGMENT", "SLAB", "CCY", "AVG_BAL",
              "CLOSING_BAL", "PROFIT_ACCRUED", "POOL_CODE"]
    ws.write_row(0, 0, header, bold)
    for i, r in enumerate(bundle.deposits):
        avg = fmt_amount(r["average_balance"])
        if stressed and i == 4242:
            avg = "#REF!"
            planted.append("Unreadable cell (#REF!) in a deposit row")
        ws.write_row(1 + i, 0, [
            r["account_id"], DEP_PRODUCT[r["product"]], DEP_BASIS[r["contract"]],
            DEP_SEGMENT[r["depositor_type"]], r["tier"], r["currency"], avg,
            fmt_amount(r["closing_balance"]), fmt_amount(r["profit_paid"]), r["pool_id"] or ""])

    # Pools
    ws = wb.add_worksheet("POOL_MIS")
    header = ["POOL_CODE", "POOL_NAME", "TYPE", "CCY", "AVG_POOL_ASSETS", "FIXED_ASSETS", "GROSS_EARNINGS",
              "POOL_EXPENSES", "BANK_SHARE", "PER_TRANSFER", "PER_CLOSING", "IRR_TRANSFER", "IRR_CLOSING",
              "WEIGHTAGE_DATE", "FROM_DATE"]
    ws.write_row(0, 0, header, bold)
    for i, p in enumerate(bundle.pools):
        ws.write_row(1 + i, 0, [
            p["pool_id"], p["pool_name"], POOL_TYPE[p["pool_type"]], p["currency"],
            fmt_amount(p["average_assets"]), fmt_amount(p["fixed_assets_in_pool"]),
            fmt_amount(p["gross_income"]), fmt_amount(p["direct_expenses"]),
            f"{p['mudarib_share'] * 100:.0f}%", fmt_amount(p["per_contribution"]),
            fmt_amount(p["per_balance"]), fmt_amount(p["irr_contribution"]), fmt_amount(p["irr_balance"]),
            p["weightages_announced_on"].strftime("%d-%m-%Y"), ddmmyyyy(p["period_start"])])

    # Capital memo
    ws = wb.add_worksheet("CAPITAL_MEMO")
    ws.write_row(0, 0, ["LINE", "PKR"], bold)
    for i, c in enumerate(bundle.capital):
        ws.write_row(1 + i, 0, [c["item"], fmt_amount(c["amount"]) if c["item"] != "ECL_TRANSITION_YEAR"
                                else str(c["amount"])])
    wb.close()

    if stressed:
        planted += ["Savings tier S1 paid below 75% of WAGY", "Special pool Mudarib share above 50%",
                    "PER contribution above 2% of net income", "IRR contribution above 1%",
                    "Weightages announced with only one working day notice",
                    "Charity booked as income", "Provision held below the required amount",
                    "Higher NPF"]
    return {"path": str(out_path), "scenario": scenario.name, "planted": sorted(set(planted)),
            "counts": {"trial_balance": len(bundle.trial_balance), "financing": len(bundle.financing),
                       "deposits": len(bundle.deposits), "pools": len(bundle.pools)}}
