"""The metric graph engine (DEC-006).

A metric is a small function registered with @metric. It declares:
- the metrics it depends on (so the engine can run everything in the right order)
- the rules it uses (so their versions and SBP sources go into the lineage)

The engine runs metrics in dependency order (a topological sort) and stores each
result with its lineage: formula, input values, rule versions and source
references, and optional evidence rows. That lineage is what the interface shows
when someone clicks a number, and it is the only material the AI may talk about.

Status rule for assumptions (FIX-030, FIX-034): if a FAIL depends on a rule whose
verification is "assumption", the status is lowered to WARNING and a note says
why. A demo assumption must never be presented as a regulatory breach.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from graphlib import TopologicalSorter

import duckdb

from daleel.core.money import D
from daleel.rulebook.rulebook import Rulebook, RuleVersion

STATUSES = ("PASS", "WARNING", "FAIL", "INFO", "NOT_AVAILABLE")


@dataclass
class MetricResult:
    id: str
    category: str
    label: str
    unit: str  # percent | pkr | count | days | ratio
    value: Decimal | None
    status: str = "INFO"
    formula: str = ""
    explanation: str = ""
    threshold: dict | None = None
    inputs: list[dict] = field(default_factory=list)
    rules: list[dict] = field(default_factory=list)
    table: dict | None = None
    notes: list[str] = field(default_factory=list)
    sort_order: int = 0

    def detail(self) -> dict:
        return {"formula": self.formula, "explanation": self.explanation, "threshold": self.threshold,
                "inputs": self.inputs, "rules": self.rules, "table": self.table, "notes": self.notes}


@dataclass
class MetricSpec:
    id: str
    category: str
    label: str
    unit: str
    deps: tuple[str, ...]
    rules: tuple[str, ...]
    fn: Callable


REGISTRY: dict[str, MetricSpec] = {}


def metric(id: str, category: str, label: str, unit: str, deps: tuple[str, ...] = (),
           rules: tuple[str, ...] = ()):
    def register(fn: Callable) -> Callable:
        REGISTRY[id] = MetricSpec(id, category, label, unit, deps, rules, fn)
        return fn

    return register


class Context:
    """What a metric function can see: data tables, rules, and earlier results."""

    def __init__(self, con: duckdb.DuckDBPyConnection, book: Rulebook, as_of: date, period_days: int,
                 available: set[str]):
        self.con = con
        self.book = book
        self.as_of = as_of
        self.period_days = period_days
        self.available = available
        self.results: dict[str, MetricResult] = {}

    def rule(self, rule_id: str) -> RuleVersion:
        return self.book.get(rule_id, self.as_of)

    def value(self, metric_id: str) -> Decimal | None:
        return self.results[metric_id].value

    def scalar(self, sql: str, params: list | None = None) -> Decimal:
        row = self.con.execute(sql, params or []).fetchone()
        return D(row[0]) if row and row[0] is not None else Decimal(0)

    def gold(self, *codes: str) -> Decimal:
        placeholders = ",".join("?" for _ in codes)
        return self.scalar(f"SELECT sum(presented) FROM gold WHERE code IN ({placeholders})", list(codes))

    def gold_group(self, group: str) -> Decimal:
        return self.scalar("SELECT sum(presented) FROM gold WHERE grp = ?", [group])

    def memo(self, item: str) -> Decimal:
        if "CAPITAL" not in self.available:
            return Decimal(0)
        return self.scalar("SELECT sum(amount) FROM capital WHERE item = ?", [item])

    def has(self, *kinds: str) -> bool:
        return all(k in self.available for k in kinds)


def run_all(ctx: Context) -> list[MetricResult]:
    graph = {m.id: set(m.deps) for m in REGISTRY.values()}
    order = list(TopologicalSorter(graph).static_order())
    for position, metric_id in enumerate(order):
        spec = REGISTRY[metric_id]
        missing = [d for d in spec.deps if ctx.results.get(d) is None or
                   ctx.results[d].status == "NOT_AVAILABLE"]
        rules = [ctx.rule(r) for r in spec.rules]
        if missing:
            result = MetricResult(spec.id, spec.category, spec.label, spec.unit, None, "NOT_AVAILABLE",
                                  notes=[f"Needs {', '.join(missing)}, which could not be calculated."])
        else:
            result = spec.fn(ctx)
            result.id, result.category, result.label, result.unit = spec.id, spec.category, spec.label, spec.unit
        result.rules = [r.ref() for r in rules]
        result.inputs = [
            {"id": d, "label": ctx.results[d].label, "unit": ctx.results[d].unit,
             "value": None if ctx.results[d].value is None else str(ctx.results[d].value)}
            for d in spec.deps if d in ctx.results
        ] + result.inputs
        if result.status == "FAIL" and any(r.is_assumption for r in rules):
            result.status = "WARNING"
            result.notes.append("Shown as a warning, not a breach: the threshold is a Daleel demo "
                                "assumption, not a verified SBP limit.")
        result.sort_order = position
        ctx.results[metric_id] = result
    return list(ctx.results.values())
