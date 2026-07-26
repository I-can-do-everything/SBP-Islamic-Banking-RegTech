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
from __future__ import annotations

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


# CAR (Capital Adequacy Ratio) Calculation
def calculate_car(balances: Dict[str, Decimal]) ->CalculationResult:
    """
    Calculate Capital Adequacy Ratio for Islamic banks.

    FORMULA:
    CAR = (Tier 1 Capital + Tier 2 Capital) / Risk Weighted Assets × 100

    TIER 1 CAPITAL (for Islamic banks):
    - Paid-up capital
    - Statutory reserves
    - Retained earnings
    - Less: Regulatory deductions (goodwill, intangibles, etc.)

    TIER 2 CAPITAL:
    - Subordinated Sukuk (Islamic bonds)
    - Revaluation reserves (up to 45% of unrealized gains)
    - General provision (up to 1.25% of RWA)

    RISK WEIGHTED ASSETS:
    Sum of (asset balance × risk weight) for all assets.

    RISK WEIGHTS (Islamic banking specific):
    - GoP Ijarah Sukuk: 0% (sovereign, PKR-denominated)
    - Murabaha receivables: 100% for unrated corporates
    - Ijarah assets: 100% for asset class
    - Mudarabah investments: Higher due to equity-like nature

    REGULATORY MINIMUM:
    11.5% per SBP CAELS guidelines.

    REFERENCE:
    SBP BPRD Basel III Capital Adequacy framework (confirm current circular)
    """

    # Tier 1 Capital components
    paid_up_capital = get_balance(balances, "1100-PUC")
    statutory_reserves = get_balance(balances, "1200-SR")
    retained_earnings = get_balance(balances, "1300-RE")

    # Regulatory deductions (simplified for prototype)
    # In production, would calculate goodwill, intangibles, etc.
    regulatory_deductions = Decimal("0")

    tier_1_capital = paid_up_capital + statutory_reserves + retained_earnings - regulatory_deductions

    # Tier 2 Capital (simplified)
    # Subordinated sukuk would be a specific RCOA code
    subordinated_sukuk = get_balance(balances, "1400-SUKUK", Decimal("0"))
    general_provision = get_balance(balances, "1500-GP", Decimal("0"))

    tier_2_capital = subordinated_sukuk + general_provision

    # Total Capital
    total_capital = tier_1_capital + tier_2_capital

    # Risk Weighted Assets calculation (simplified)
    # In production, would calculate RWA for each asset class
    # For prototype: Assume 100% risk weight for financing assets
    financing_codes = ["3590-MUR", "3590-IJA", "3590-DM", "3590-SAL", "3590-IST"]
    total_financing = sum(get_balance(balances, code) for code in financing_codes)

    # Add cash and government securities (0% risk weight)
    # to get total assets, then calculate RWA
    cash = get_balance(balances, "1000-CASH", Decimal("0"))  # 0% weight
    government_sukuk = get_balance(balances, "2100-GOS", Decimal("0"))  # 0% weight (sovereign)

    # Simplified RWA calculation:
    # RWA = Financing (100%) + Other assets calculated with weights
    rwa = total_financing  # Assuming 100% risk weight for simplicity

    # Calculate CAR
    if rwa == 0:
        car_value = Decimal("0")
    else: 
        car_value = (total_capital / rwa) * Decimal("100")

    # check breach
    breach = car_value < CAR_MINIMUM

    input_accounts = [
        "1100-PUC", "1200-SR", "1300-RE",
        "1400-SUKUK", "1500-GP",
        "3590-MUR", "3590-IJA", "3590-DM", "3590-SAL", "3590-IST"
    ]

    formula = f"({paid_up_capital} + {statutory_reserves} + {retained_earnings}) / {rwa} × 100"

    return CalculationResult(
        ratio_name="CAR",
        ratio_value=car_value.quantize(Decimal("0.00000001")),
        numerator=total_capital,
        denominator=rwa,
        formula_applied=f"Tier1({tier_1_capital}) + Tier2({tier_2_capital}) / RWA({rwa}) × 100",
        input_accounts=input_accounts,
        regulatory_minimum=CAR_MINIMUM,
        regulatory_maximum=None,
        breach_flag=breach,
        sbp_circular_reference="SBP BPRD Basel III Capital Adequacy framework", # need to confirm current BPRD circular number
    )
