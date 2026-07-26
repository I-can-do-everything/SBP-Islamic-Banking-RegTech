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
    
# NPF ratio calculation

def calculate_npf_ratio(balances: Dict[str, Decimal]) -> CalculationResult:
    """
    Calculate Non-Performing Financing Ratio.

    FORMULA:
    NPF Ratio = (Total NPF Balances / Total Gross Financing) × 100

    NPF includes:
    - NPF Murabaha
    - NPF Ijarah
    - NPF Diminishing Musharakah
    - NPF Salam
    - NPF Istisna

    Total Financing includes all financing products (performing + non-performing).

    REGULATORY THRESHOLD:
    Maximum 7% per SBP CAELS guidelines.
    Above this threshold triggers enhanced supervision.

    REFERENCE:
    SBP Prudential Regulations R-8, Classification & Provisioning (confirm exact PR category)
    """

    # NPF account codes
    npf_codes = [
        "3595-MUR-NPF",  # NPF Murabaha
        "3595-IJA-NPF",  # NPF Ijarah
        "3595-DM-NPF",   # NPF Diminishing Musharakah
        "3595-SAL-NPF",  # NPF Salam (if applicable)
        "3595-IST-NPF",  # NPF Istisna (if applicable)
    ]

    # gross financing account codes (performing + non-performing)
    financing_codes = [
        "3590-MUR",  # Murabaha Financing
        "3590-IJA",  # Ijarah Financing
        "3590-DM",   # Diminishing Musharakah
        "3590-SAL",  # Salam
        "3590-IST",  # Istisna
    ]

    # calculate total NPF
    total_npf = sum(
        get_balance(balances, code)for code in npf_codes
    )

    # calculate total gorss financing (inlcuding NPF)
    total_financing = sum(
        get_balance(balances, code) for code in financing_codes
    )

    # calculate ratio with division by 0 handled
    if total_financing == 0:
        ratio_value = Decimal('0')
    else:
        ratio_value = (total_npf / total_financing) * Decimal("100")


    # check breach
    breach = ratio_value > NPF_MAXIMUM

    # build formula for audit
    formula = f"({ ' + '.join(npf_codes[:3]) }...) / ({ ' + '.join(financing_codes[:3]) }...) × 100"

    return CalculationResult(
        ratio_name="NPF_RATIO"
    )
