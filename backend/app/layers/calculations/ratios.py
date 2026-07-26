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



# Pool Management Calculations

def calculate_pool_ratios(balances: Dict[str, Decimal]) -> List[CalculationResult]:
    """
    Calculate Pool Management ratios for Islamic banks.

    POOL STRUCTURE:
    - Depositors provide funds via Mudarabah/Wakala deposits
    - Bank deploys funds into Shariah-compliant financing
    - Profit is distributed between depositors and bank

    KEY RATIOS:
    1. Gross Pool Income
    2. PER (Profit Equalisation Reserve) - max 20% of gross
    3. IRR (Investment Risk Reserve) - max 10% of depositor share
    4. Depositor Share Ratio - min 50%
    5. Declared Profit Rate

    REFERENCES:
    IBD Circular No. 03 of 2012, Pool Management Instructions, as amended
    """
    results = []

    # pool income components
    murabaha_income = get_balance(balances, "4100-MUR-INC")
    ijarah_income = get_balance(balances, "4100-IJA-INC")
    dm_income = get_balance(balances, "4100-DM-INC", Decimal("0"))

    gross_pool_income = murabaha_income + ijarah_income + dm_income

    # Depositor funds
    mudarabah_deposits = get_balance(balances, "2150-MUD")
    wakala_deposits = get_balance(balances, "2150-WAK")
    total_deposits = mudarabah_deposits + wakala_deposits

    # PER (Profit Equalisation Reserve)
    per_balance = get_balance(balances, "2500-PER", Decimal("0"))
    per_ratio = (per_balance / gross_pool_income * 100) if gross_pool_income > 0 else Decimal("0")

    results.append(CalculationResult(
        ratio_name="PER_RATIO",
        ratio_value=per_ratio.quantize(Decimal("0.00000001")),
        numerator=per_balance,
        denominator=gross_pool_income,
        formula_applied="PER Balance / Gross Pool Income × 100",
        input_accounts=["2500-PER", "4100-MUR-INC", "4100-IJA-INC"],
        regulatory_minimum=None,
        regulatory_maximum=PER_CAP_PERCENT,
        breach_flag=per_ratio > PER_CAP_PERCENT,
        sbp_circular_reference="IBD Circular No. 03 of 2012, Pool Management Instructions, as amended",
    ))

    # IRR (Investment Risk Reserve)
    irr_balance = get_balance(balances, "2501-IRR", Decimal("0"))
    depositor_share = gross_pool_income * Decimal("0.50")  # Minimum 50% to depositors
    irr_ratio = (irr_balance / depositor_share * 100) if depositor_share > 0 else Decimal("0")

    results.append(CalculationResult(
        ratio_name="IRR_RATIO",
        ratio_value=irr_ratio.quantize(Decimal("0.00000001")),
        numerator=irr_balance,
        denominator=depositor_share,
        formula_applied="IRR Balance / Depositor Share × 100",
        input_accounts=["2501-IRR", "2150-MUD", "2150-WAK"],
        regulatory_minimum=None,
        regulatory_maximum=IRR_CAP_PERCENT,
        breach_flag=irr_ratio > IRR_CAP_PERCENT,
        sbp_circular_reference="IBD Circular No. 03 of 2012, Pool Management Instructions, as amended",
    ))

    # Depositor Share Ratio
    # Net distributable income = Gross - PER - IRR
    net_distributable_income = gross_pool_income - per_balance - irr_balance
    actual_depositor_share = net_distributable_income * Decimal("0.55")  # Example: 55% to depositors

    depositor_share_ratio = (actual_depositor_share / net_distributable_income * 100) if net_distributable_income > 0 else Decimal("0")

    results.append(CalculationResult(
        ratio_name="DEPOSITOR_SHARE_RATIO",
        ratio_value=depositor_share_ratio.quantize(Decimal("0.00000001")),
        numerator=actual_depositor_share,
        denominator=net_distributable_income,
        formula_applied="Depositor Share / Net Distributable Income × 100",
        input_accounts=["2150-MUD", "2150-WAK", "2500-PER", "2501-IRR"],
        regulatory_minimum=DEPOSITOR_SHARE_MIN,
        regulatory_maximum=None,
        breach_flag=depositor_share_ratio < DEPOSITOR_SHARE_MIN,
        sbp_circular_reference="IBD Circular No. 03 of 2012, Pool Management Instructions, as amended",
    ))

    # Declared Profit Rate (annualized)
    # DPR = (Depositor Share / Average Deposits) × (365/days in period) × 100
    # Simplified: assume monthly period (30 days)
    if total_deposits > 0:
        dpr = (actual_depositor_share / total_deposits) * Decimal("12") * Decimal("100")
    else:
        dpr = Decimal("0")

    results.append(CalculationResult(
        ratio_name="DECLARED_PROFIT_RATE",
        ratio_value=dpr.quantize(Decimal("0.00000001")),
        numerator=actual_depositor_share,
        denominator=total_deposits,
        formula_applied="(Depositor Share / Average Deposits) × 12 × 100 (Annualized)",
        input_accounts=["2150-MUD", "2150-WAK", "4100-MUR-INC", "4100-IJA-INC"],
        regulatory_minimum=None,
        regulatory_maximum=None,
        breach_flag=False,  # No threshold, but should not be negative
        sbp_circular_reference="IBD Circular No. 03 of 2012, Pool Management Instructions, as amended",
    ))

    return results