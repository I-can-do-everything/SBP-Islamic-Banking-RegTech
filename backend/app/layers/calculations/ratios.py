"""
Regulatory Calculation Functions

PURPOSE:
Calculate regulatory ratios for SBP reporting:
- NPF Ratio (Non-Performing Financing)
- CAR (Capital Adequacy Ratio)
- Pool Management ratios
- Provision requirements
- ECL (Expected Credit Loss)

OUTPUT FORMAT:
Each calculation function returns a structured result containing:
- ratio_name, ratio_value, numerator, denominator
- formula_applied (human-readable)
- input_accounts (list of RCOA codes used)
- regulatory_minimum/maximum if applicable
- breach_flag (threshold violation check)
- sbp_circular_reference

HOW TO ADD NEW CALCULATION:
1. Define calculation function following the pattern below
2. Use get_balance() to safely retrieve RCOA balances
3. Return CalculationResult dataclass
4. Register in CalculationService
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Any

from app.core.config import (
    CAR_MINIMUM,
    NPF_MAXIMUM,
    DPD_THRESHOLDS,
    PROVISION_RATES,
    PER_CAP_PERCENT,
    IRR_CAP_PERCENT,
    DEPOSITOR_SHARE_MIN,
)
from app.layers.normalisation import get_balance

@dataclass
class CalculationResult:
    """
    Standard output format for all calculations.

    This structure ensures:
    - Consistent audit trail across all calculations
    - Reproducibility of results
    - Clear regulatory linkage
    """
    ratio_name: str
    ratio_value: Decimal
    numerator: Decimal
    denominator: Decimal
    formula_applied: str
    input_accounts: List[str] = field(default_factory=list)
    regulatory_minimum: Optional[Decimal] = None
    regulatory_maximum: Optional[Decimal] = None
    breach_flag: bool = False
    sbp_circular_reference: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "retio_name": self.ratio_name,
            "ratio_value": str(self.ratio_value),
            "numerator": str(self.numerator),
            "denominator": str(self.denominator),
            "formula_applied": self.formula_applied,
            "input_accounts": self.input_accounts,
            "regulatory_minimum": str(self.regulatory_minimum),
            "regulatory_maximum": str(self.regulatory_maximum),
            "breach_flag": self.breach_flag,
            "sbp_circular_reference": self.sbp_circular_reference
        }
    
