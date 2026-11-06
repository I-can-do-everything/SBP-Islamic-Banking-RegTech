"""Loads the rulebook and answers "what was this rule on date D?" (DEC-005)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Any

import yaml

from daleel.core.config import get_settings
from daleel.core.errors import InvalidInput


@dataclass(frozen=True)
class RuleVersion:
    rule_id: str
    title: str
    unit: str
    effective_from: date
    effective_to: date | None
    source: dict
    value: Decimal | None = None
    table: dict | None = None
    items: tuple | None = None
    notes: str | None = None

    @property
    def verification(self) -> str:
        return self.source.get("verification", "assumption")

    @property
    def is_assumption(self) -> bool:
        return self.verification == "assumption"

    def ref(self) -> dict:
        """A compact reference used in lineage and in the AI fact sheet."""
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "value": None if self.value is None else str(self.value),
            "unit": self.unit,
            "effective_from": self.effective_from.isoformat(),
            "source": self.source,
        }


@dataclass
class Rulebook:
    versions: dict[str, list[RuleVersion]] = field(default_factory=dict)

    def get(self, rule_id: str, as_of: date) -> RuleVersion:
        for version in self.versions.get(rule_id, []):
            if version.effective_from <= as_of and (
                version.effective_to is None or as_of <= version.effective_to
            ):
                return version
        raise InvalidInput(
            "rule_missing", f"No version of rule {rule_id} is in force on {as_of.isoformat()}."
        )

    def value(self, rule_id: str, as_of: date) -> Decimal:
        version = self.get(rule_id, as_of)
        if version.value is None:
            raise InvalidInput("rule_not_scalar", f"Rule {rule_id} is a table, not a single value.")
        return version.value

    def all_in_force(self, as_of: date) -> list[RuleVersion]:
        found = []
        for rule_id in self.versions:
            try:
                found.append(self.get(rule_id, as_of))
            except InvalidInput:
                continue
        return found


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _version(rule: dict, spec: dict) -> RuleVersion:
    table = spec.get("table", rule.get("table"))
    if isinstance(table, dict) and all(isinstance(v, str) for v in table.values()):
        table = {str(k): Decimal(v) for k, v in table.items()}
    raw_value = spec.get("value", rule.get("value"))
    items = spec.get("list", rule.get("list"))
    return RuleVersion(
        rule_id=rule["id"],
        title=rule["title"],
        unit=rule["unit"],
        effective_from=_to_date(spec.get("effective_from", rule.get("effective_from"))),
        effective_to=_to_date(spec.get("effective_to", rule.get("effective_to"))),
        source=spec.get("source", rule.get("source", {})),
        value=None if raw_value is None else Decimal(str(raw_value)),
        table=table,
        items=None if items is None else tuple(items),
        notes=rule.get("notes"),
    )


@lru_cache
def load_rulebook() -> Rulebook:
    path = get_settings().rulebook_dir / "rules.yaml"
    data = yaml.safe_load(path.read_text())
    book = Rulebook()
    for rule in data["rules"]:
        specs = rule.get("versions") or [rule]
        versions = [_version(rule, spec) for spec in specs]
        versions.sort(key=lambda v: v.effective_from)
        book.versions[rule["id"]] = versions
    return book
