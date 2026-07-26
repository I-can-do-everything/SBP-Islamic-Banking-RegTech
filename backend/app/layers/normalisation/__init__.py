"""
Layer 2: Normalization Module

Transforms CBS account codes to SBP RCOA standard format with Decimal precision.

MAIN ENTRY POINT:
    from app.layers.normalization import NormalizationService, get_balance

    service = NormalizationService(db)
    normalized = await service.normalize(submission, file_bytes)
    balances = await service.get_normalized_balances(submission.id)

    # In calculations, use get_balance:
    murabaha = get_balance(balances, "3590-MUR")

EXPORTS:
- NormalizationService: Coordinates normalization process
- RCOAMapper: CBS to RCOA mapping logic
- get_balance: Safe balance lookup helper
"""

from app.layers.normalisation.service import get_balance
from app.layers.normalisation.mapper import RCOAMapper, MappingRule, aggregate_by_rcoa


__all__ = [
    "RCOAMapper",
    "MappingRule",
    "aggregate_by_rcoa",
    "get_balance"
]