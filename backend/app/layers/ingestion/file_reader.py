"""
CBS File Reader Module

PURPOSE:
Parse CBS export files and extract GL trial balance data.

HANDLES:
- CSV files (T24, Flexcube, Generic)
- XLSX files (Excel exports)

RETURNS:
List of dictionaries with standardized keys for downstream processing.

HOW TO EXTEND:
1. Add new parsing function for new CBS format
2. Map to standard output columns: account_code, description, balance, date
3. Add parsing logic to read_file() function
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook
from app.core.config import CBSFormat
from app.layers.ingestion.format_detector import detect_format



def _parse_balance(value: Any) -> Optional[Decimal]:
    """
    Parse a balance value to Decimal with full precision.

    CRITICAL: Never use float() as an intermediate step!
    Direct string-to-Decimal preserves precision.

    SUPPORTED FORMATS:
    - Plain numbers: "1234567.89"
    - Numbers with commas: "1,234,567.89"
    - Parentheses for negative: "(1234567.89)"
    - Leading minus: "-1234567.89"
    - CR/DR suffixes: "1234567.89 CR"

    Returns None if value cannot be parsed.
    """
    if value is None:
        return None
    
    if isinstance(value, (int, Decimal)):
        return Decimal(str(value))
    
    str_value = str(value).strip()

    if not str_value or str_value in ('-', '0', 'N/A', 'NULL'):
        return Decimal('0')
    
    str_value = str_value.replace(',', '')

    is_negative = False
    if str_value.startswith('(') and str_value.endswith(')'):
        is_negative = True
        str_value = str_value[1:-1]

    # Handle CR/DR suffixes (Credit/Debit)
    # In accounting, CR often means negative (credit balance), DR positive (debit)
    # But convention varies, we'll interpret CR as credit (negative) for liabilities
    str_value_upper = str_value.upper()
    if str_value_upper.endswith(' CR'):
        str_value = str_value[:-3].strip()
        is_negative = True
    elif str_value_upper.endswith(' DR'):
        str_value = str_value[:-3].strip*()
        

    cleaned = ''
    has_decimal = False
    has_digit = False
    for char in str_value:
        if char.isdigit():
            cleaned += char
            has_digit = True
        elif char == '.' and not has_decimal:
            cleaned += char
            has_decimal = True
        elif char == '-' and not cleaned:
            is_negative = True

        
    if not has_digit:
        return Decimal('0')
    
    try: 
        result= Decimal(cleaned)
        if is_negative:
            result = -result
        return result
    except (InvalidOperation, ValueError):
        return None

    
        
    
    
