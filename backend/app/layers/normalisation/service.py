"""
Normalization Service Module

PURPOSE:
Coordinates the normalization of CBS data to RCOA format:
1. Load mapping configuration for institution
2. Apply mappings to each CBS account
3. Aggregate by RCOA code
4. Store normalized records

OUTPUT:
Each submission produces normalized_data records with:
- RCOA account code and description
- Balance in full precision
- Mapping rule applied
- Mapping version used

HOW TO EXTEND:
- Add support for multiple currencies
- Add validation for RCOA code validity
- Track unmapped codes for reporting
"""

import uuid
from datetime import datetime
from decimal import Decimal 
from typing import List, Dict, Tuple, Any

from app.layers.normalisation.mapper import RCOAMapper, aggregate_by_rcoa
from app.layers.ingestion.file_reader import read_file


def get_balance(
        balances: Dict[str, Decimal],
        rcoa_code: str,
        default: Decimal = None
) -> Decimal:
    """
    Helper function to safely get a balance from dictionary.

    USAGE in calculations:
        from app.layers.normalization import get_balance

        murabaha = get_balance(balances, "3590-MUR")  # Returns 0 if not found
        capital = get_balance(balances, "1100-PUC", Decimal("1000000"))  # Default if missing

    NOTE:
    This is the 'g' function mentioned in the specifications.
    Named get_balance() for clarity.
    """
    if default is None:
        default = Decimal
    return balances.get(rcoa_code, default)