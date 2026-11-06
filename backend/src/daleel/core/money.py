"""Exact money arithmetic (DEC-007).

Rules used everywhere in Daleel:
- Money is a `Decimal`, never a `float`.
- Calculations run with 38 significant digits and banker's rounding
  (ROUND_HALF_EVEN), which does not bias totals upwards.
- Stored amounts keep 4 decimal places. Rounding for display happens only at
  the edge (API and reports), never in the middle of a calculation.
"""

from __future__ import annotations

import decimal
from decimal import Decimal

CONTEXT = decimal.Context(prec=38, rounding=decimal.ROUND_HALF_EVEN)
decimal.setcontext(CONTEXT)

ZERO = Decimal(0)
ONE = Decimal(1)
HUNDRED = Decimal(100)
AMOUNT_PLACES = Decimal("0.0001")
RATIO_PLACES = Decimal("0.000001")


def D(value: object) -> Decimal:
    """Convert a value to Decimal without passing through float.

    Floats are converted through their shortest text form (repr), which is the
    number a person would have typed, not the binary approximation.
    """
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return ZERO
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value))


def safe_div(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    """Divide, returning None (not zero) when the denominator is zero.

    A ratio with no denominator is undefined. Reporting it as 0 would look like
    a real (and often alarming) number, which is exactly the kind of silent
    error this project avoids.
    """
    if denominator == 0:
        return None
    return numerator / denominator


def pct(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    ratio = safe_div(numerator, denominator)
    return None if ratio is None else ratio * HUNDRED


def q_amount(value: Decimal) -> Decimal:
    return value.quantize(AMOUNT_PLACES)


def q_ratio(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.quantize(RATIO_PLACES)


def to_str(value: Decimal | None) -> str | None:
    """Serialise for JSON. Amounts travel as strings so no precision is lost."""
    if value is None:
        return None
    return format(value.normalize() if value == value.to_integral() else value, "f")
