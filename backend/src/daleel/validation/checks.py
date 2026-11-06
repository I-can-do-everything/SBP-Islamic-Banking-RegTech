"""Validation checks: integrity, reconciliation and Shariah rules.

Metrics answer "what is the number". Checks answer "can the numbers be
trusted, and were the rules followed". Each check returns PASS, WARNING, FAIL
or INFO with a plain message and the evidence behind it.

Reconciliation matters most in real regulatory reporting: the contract level
portfolio must add up to the financing accounts in the general ledger, and the
deposit accounts to the deposit accounts. A difference usually means a missing
branch, a missing product or a broken extract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import duckdb

from daleel.core.money import ZERO, D, pct, q_amount
from daleel.datasets.schemas import SCHEMAS
from daleel.mapping.mapper import MappingReport
from daleel.rulebook.rulebook import Rulebook

MODE_TO_CODE = {"MURABAHA": "A.FIN_MUR", "IJARAH": "A.FIN_IJA", "DIMINISHING_MUSHARAKAH": "A.FIN_DM",
                "MUSHARAKAH": "A.FIN_MUSH", "RUNNING_MUSHARAKAH": "A.FIN_MUSH", "ISTISNA": "A.FIN_IST",
                "SALAM": "A.FIN_SAL", "TIJARAH": "A.FIN_TIJ", "OTHER": "A.FIN_OTH"}
PRODUCT_TO_CODE = {"CURRENT": "L.DEP_CUR", "SAVINGS": "L.DEP_SAV", "TERM": "L.DEP_TERM"}


@dataclass
class Check:
    id: str
    category: str
    label: str
    status: str
    message: str
    evidence: dict = field(default_factory=dict)
    rule_refs: list[dict] = field(default_factory=list)


def _fmt(value: Decimal) -> str:
    return f"{q_amount(value):,.2f}"


def run_checks(con: duckdb.DuckDBPyConnection, book: Rulebook, as_of: date, available: set[str],
               mapping: MappingReport | None, ingestion: dict) -> list[Check]:
    checks: list[Check] = []
    tol_rule = book.get("integrity.reconciliation_tolerance", as_of)
    tol = tol_rule.value

    missing = [k for k in SCHEMAS if k not in available]
    checks.append(Check(
        "integrity.datasets", "Data integrity", "All datasets supplied",
        "PASS" if not missing else "WARNING",
        "All five datasets were found." if not missing else
        f"Missing: {', '.join(missing)}. Metrics that need them are shown as not available.",
        {"missing": missing}))

    rejected = {k: v["rejected_count"] for k, v in ingestion.get("datasets", {}).items() if v["rejected_count"]}
    checks.append(Check(
        "integrity.rejected_rows", "Data integrity", "Every row could be read",
        "PASS" if not rejected else "WARNING",
        "No rows were rejected." if not rejected else
        "Some rows could not be read and were left out (never counted as zero): " +
        ", ".join(f"{k} {n}" for k, n in rejected.items()) + ".",
        {"rejected": rejected,
         "samples": {k: v["rejects_sample"][:5] for k, v in ingestion.get("datasets", {}).items()
                     if v["rejected_count"]}}))

    if "TRIAL_BALANCE" in available:
        dr, cr = con.execute("SELECT sum(debit), sum(credit) FROM trial_balance").fetchone()
        diff = D(dr) - D(cr)
        checks.append(Check(
            "integrity.tb_balanced", "Data integrity", "Trial balance balances",
            "PASS" if diff == 0 else "FAIL",
            f"Total debits equal total credits ({_fmt(D(dr))})." if diff == 0 else
            f"Debits exceed credits by {_fmt(diff)}. A trial balance that does not balance cannot be used.",
            {"debits": str(dr), "credits": str(cr), "difference": str(diff)}))

        assets = con.execute("SELECT sum(presented) FROM gold WHERE grp IN ('ASSETS','FINANCING')").fetchone()[0]
        mat_rule = book.get("integrity.unmapped_material_share", as_of)
        unmapped_total = sum((abs(D(u["signed_amount"])) for u in mapping.unmapped), ZERO)
        share = pct(unmapped_total, D(assets)) or ZERO
        if not mapping.unmapped:
            status, message = "PASS", "Every GL account is mapped to a reporting code."
        else:
            status = "FAIL" if share > mat_rule.value else "WARNING"
            message = (f"{len(mapping.unmapped)} GL account(s) totalling {_fmt(unmapped_total)} have no mapping "
                       f"({share:.3f}% of assets) and are left out of every ratio until mapped.")
        checks.append(Check("integrity.unmapped", "Data integrity", "Every GL account is mapped", status, message,
                            {"accounts": mapping.unmapped[:20], "share_of_assets_pct": str(share)},
                            [mat_rule.ref()]))
        if mapping.overlaps:
            checks.append(Check("integrity.mapping_overlap", "Data integrity", "Mapping rules do not overlap",
                                "WARNING", f"{len(mapping.overlaps)} account(s) match more than one rule; "
                                "the first rule was used.", {"overlaps": mapping.overlaps[:20]}))
        checks.append(Check(
            "integrity.abnormal_balances", "Data integrity", "Balances sit on their normal side",
            "PASS" if not mapping.abnormal else "WARNING",
            "Every reporting code sits on its normal side." if not mapping.abnormal else
            f"{len(mapping.abnormal)} reporting code(s) are on their abnormal side and need review.",
            {"codes": mapping.abnormal}))

    if {"TRIAL_BALANCE", "FINANCING"} <= available:
        rows = con.execute("SELECT mode, sum(outstanding) FROM contracts GROUP BY 1").fetchall()
        by_code: dict[str, Decimal] = {}
        for mode, amount in rows:
            by_code[MODE_TO_CODE[mode]] = by_code.get(MODE_TO_CODE[mode], ZERO) + D(amount)
        lines, worst = [], ZERO
        for code, label, gl in con.execute(
                "SELECT code, label, presented FROM gold WHERE grp = 'FINANCING' ORDER BY code").fetchall():
            tape = by_code.get(code, ZERO)
            diff = tape - D(gl)
            worst = max(worst, abs(diff))
            lines.append({"code": code, "label": label, "portfolio": str(tape), "ledger": str(gl), "difference": str(diff)})
        checks.append(Check(
            "recon.financing", "Reconciliation", "Financing portfolio agrees to the general ledger",
            "PASS" if worst <= tol else "FAIL",
            "Contract level financing agrees to the ledger for every mode." if worst <= tol else
            f"The portfolio and the ledger differ by up to {_fmt(worst)} for a mode.",
            {"lines": lines}, [tol_rule.ref()]))

    if {"TRIAL_BALANCE", "DEPOSITS"} <= available:
        rows = dict(con.execute("SELECT product, sum(closing_balance) FROM deposits GROUP BY 1").fetchall())
        lines, worst = [], ZERO
        for product, code in PRODUCT_TO_CODE.items():
            detail = D(rows.get(product, 0))
            gl = D(con.execute("SELECT presented FROM gold WHERE code = ?", [code]).fetchone()[0])
            diff = detail - gl
            worst = max(worst, abs(diff))
            lines.append({"product": product, "code": code, "accounts": str(detail), "ledger": str(gl),
                          "difference": str(diff)})
        rejected_deposits = rejected.get("DEPOSITS", 0)
        message = ("Deposit accounts agree to the ledger for every product." if worst <= tol else
                   f"Deposit accounts and the ledger differ by up to {_fmt(worst)}." +
                   (f" {rejected_deposits} rejected deposit row(s) are the likely cause." if rejected_deposits else ""))
        checks.append(Check("recon.deposits", "Reconciliation", "Deposits agree to the general ledger",
                            "PASS" if worst <= tol else "FAIL", message, {"lines": lines}, [tol_rule.ref()]))

    if "TRIAL_BALANCE" in available:
        rule = book.get("shariah.charity_not_income", as_of)
        charity = D(con.execute("SELECT presented FROM gold WHERE code = 'I.CHARITY'").fetchone()[0])
        checks.append(Check(
            "shariah.charity_not_income", "Shariah", "Charity is not recognised as income",
            "PASS" if charity == 0 else "FAIL",
            "No charity is booked as income." if charity == 0 else
            f"{_fmt(charity)} of charity is booked as income. It belongs in the charity payable account.",
            {"charity_as_income": str(charity)}, [rule.ref()]))

    if "DEPOSITS" in available:
        bad = con.execute("""SELECT count(*), sum(profit_paid) FROM deposits
                             WHERE contract = 'QARD' AND profit_paid > 0""").fetchone()
        checks.append(Check(
            "shariah.qard_no_profit", "Shariah", "No profit is paid on Qard (current) accounts",
            "PASS" if not bad[0] else "FAIL",
            "Qard based current accounts earn no profit, as Qard requires." if not bad[0] else
            f"{bad[0]} Qard account(s) show profit of {_fmt(D(bad[1]))}. A Qard (loan) cannot carry a return.",
            {"accounts": bad[0]},
            [{"rule_id": "shariah.qard_principle", "title": "A Qard may not carry any return to the lender",
              "source": {"ref": "CON-046", "doc": "Shariah principle of Qard", "verification": "principle"}}]))
        untagged = con.execute("""SELECT count(*) FROM deposits
                                  WHERE contract = 'MUDARABAH' AND (pool_id IS NULL OR pool_id = '')""").fetchone()[0]
        checks.append(Check(
            "shariah.pool_tagging", "Shariah", "Every Mudarabah deposit is assigned to a pool",
            "PASS" if not untagged else "WARNING",
            "Every Mudarabah deposit is tagged to a pool." if not untagged else
            f"{untagged} Mudarabah deposit(s) have no pool; IBD Circular No. 03 of 2012 requires the pool to be "
            "identified when the deposit is accepted.", {"untagged": untagged}))

    if "FINANCING" in available:
        defaulted = con.execute("SELECT count(*) FROM contracts WHERE pd_defaulted OR lgd_defaulted").fetchone()[0]
        total = con.execute("SELECT count(*) FROM contracts").fetchone()[0]
        checks.append(Check(
            "data.default_parameters", "Data integrity", "Every contract has its own PD and LGD",
            "PASS" if not defaulted else "INFO",
            "Every contract carries the bank's own PD and LGD." if not defaulted else
            f"{defaulted} of {total} contracts had no PD or LGD; rulebook defaults were used and labelled.",
            {"contracts": defaulted}))
    return checks
