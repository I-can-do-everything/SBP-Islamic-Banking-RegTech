"""The fact sheet: the only material the AI is allowed to talk about.

Each fact has an id (F1, F2 ...), a label, a status, and a display string that
the APP renders. The model never receives a digit to copy: it refers to numbers
with placeholders such as {F3}, and the app substitutes the engine's value
afterwards. A model that cannot write a number cannot get one wrong.

Comparisons are precomputed too ("above the minimum by {F7}"), so the model
never has to do arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from daleel.core.money import q_amount


def display(value: Decimal | None, unit: str) -> str:
    if value is None:
        return "not available"
    if unit == "percent":
        return f"{value:.2f}%"
    if unit == "pkr":
        v = q_amount(value)
        if abs(v) >= Decimal("1e9"):
            return f"PKR {v / Decimal('1e9'):,.2f} billion"
        if abs(v) >= Decimal("1e6"):
            return f"PKR {v / Decimal('1e6'):,.2f} million"
        return f"PKR {v:,.2f}"
    if unit == "days":
        return f"{value:.0f} working days"
    if unit == "count":
        return f"{value:,.0f}"
    return f"{value}"


@dataclass
class Fact:
    id: str
    label: str
    display: str
    status: str
    kind: str  # metric | threshold | gap | check
    ref: str  # metric or check id
    category: str
    note: str = ""

    def for_model(self) -> dict:
        """What the model sees: no numbers, only meaning."""
        return {"id": self.id, "label": self.label, "status": self.status, "kind": self.kind,
                "category": self.category, **({"note": self.note} if self.note else {})}


@dataclass
class FactSheet:
    facts: list[Fact] = field(default_factory=list)

    def add(self, **kw) -> Fact:
        fact = Fact(id=f"F{len(self.facts) + 1}", **kw)
        self.facts.append(fact)
        return fact

    def by_id(self) -> dict[str, Fact]:
        return {f.id: f for f in self.facts}


SKIP_INFO = {"bs.gross_financing_gl", "bs.total_deposits_gl", "aq.ecl_stage12", "cap.credit_rwa",
             "cap.tier1", "cap.tier2", "cap.cet1", "cap.total_rwa", "bs.total_assets", "pl.net_profit_period",
             "bs.equity", "aq.gross_financing", "aq.npf_amount", "aq.provision_required", "aq.provision_held"}


def _gap_text(gap: Decimal, unit: str) -> str:
    text = display(abs(gap), unit)
    return text.replace("%", " percentage points") if unit == "percent" else text


def composite(m: dict) -> str:
    """One readable phrase per metric: value, limit and distance, all from the engine."""
    value = None if m["value"] is None else Decimal(m["value"])
    unit = m["unit"]
    shown = display(value, unit)
    threshold = (m.get("detail") or {}).get("threshold") or {}
    if value is None:
        return shown
    if m["id"] == "aq.provision_gap":
        return f"a shortfall of {display(-value, unit)}" if value < 0 else f"a surplus of {shown}"
    if not threshold.get("value"):
        return shown
    limit = Decimal(threshold["value"])
    if threshold.get("type") == "min":
        if threshold.get("buffer"):
            with_buffer = limit + Decimal(threshold["buffer"])
            if value < limit:
                return f"{shown}, {_gap_text(limit - value, unit)} below the {display(limit, unit)} minimum"
            if value < with_buffer:
                return (f"{shown}, above the {display(limit, unit)} minimum but "
                        f"{_gap_text(with_buffer - value, unit)} short of the {display(with_buffer, unit)} "
                        "level that includes the capital conservation buffer")
            return f"{shown}, {_gap_text(value - with_buffer, unit)} above the {display(with_buffer, unit)} requirement"
        word = "below" if value < limit else "above"
        return f"{shown}, {_gap_text(value - limit, unit)} {word} the {display(limit, unit)} minimum"
    word = "above" if value > limit else "within"
    if word == "within":
        return f"{shown}, within the {display(limit, unit)} maximum"
    return f"{shown}, {_gap_text(value - limit, unit)} above the {display(limit, unit)} maximum"


def _check_display(c: dict) -> str:
    ev = c.get("evidence") or {}
    if c["id"] == "shariah.charity_not_income":
        return display(Decimal(ev.get("charity_as_income", "0")), "pkr") + " of charity booked as income"
    if c["id"] == "recon.deposits":
        diffs = [abs(Decimal(line["difference"])) for line in ev.get("lines", [])]
        return "a difference of " + display(max(diffs) if diffs else Decimal(0), "pkr")
    if c["id"] == "integrity.rejected_rows":
        return f"{sum(ev.get('rejected', {}).values())} row(s) left out"
    if c["id"] == "integrity.unmapped":
        total = sum((abs(Decimal(a["signed_amount"])) for a in ev.get("accounts", [])), Decimal(0))
        return f"{len(ev.get('accounts', []))} account(s) totalling {display(total, 'pkr')}"
    return c["status"].lower()


def build_fact_sheet(metrics: list[dict], checks: list[dict]) -> FactSheet:
    sheet = FactSheet()
    for m in metrics:
        if m["status"] == "NOT_AVAILABLE" or m["id"] in SKIP_INFO:
            continue
        sheet.add(label=m["label"], display=composite(m), status=m["status"], kind="metric", ref=m["id"],
                  category=m["category"])
    for c in checks:
        if c["status"] == "PASS" and not c["id"].startswith("recon"):
            continue
        sheet.add(label=c["label"], display=_check_display(c), status=c["status"], kind="check",
                  ref=c["id"], category=c["category"], note=_check_note(c))
    return sheet
def _check_note(check: dict) -> str:
    """A short description without digits (digits stay out of the model's input)."""
    words = {"integrity.unmapped": "one or more GL accounts have no mapping",
             "integrity.rejected_rows": "some rows could not be read and were excluded",
             "recon.deposits": "deposit accounts do not agree to the ledger" if check["status"] != "PASS"
             else "deposit accounts agree to the ledger",
             "recon.financing": "financing contracts do not agree to the ledger" if check["status"] != "PASS"
             else "financing contracts agree to the ledger",
             "shariah.charity_not_income": "charity has been booked as income",
             "integrity.tb_balanced": "the trial balance does not balance",
             "data.default_parameters": "some contracts used default PD or LGD values",
             "shariah.qard_no_profit": "profit shown on Qard accounts",
             "integrity.abnormal_balances": "some balances sit on their abnormal side"}
    return words.get(check["id"], check["label"].lower())
