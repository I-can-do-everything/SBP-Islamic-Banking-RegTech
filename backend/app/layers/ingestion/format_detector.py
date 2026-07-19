"""
CBS format detection module

This is meant to detect which core banking system exported
a given filed based on the patterns in the file headers
and structure.

Supported formats as of this build:
- T24
- FLEXCUBE
- GENERIC_CSV
"""

from typing import Tuple, Optional, Dict, List
from io import BytesIO
import csv 
import struct 
import zipfile

from app.core.config import CBSFormat

EXPECTED_HEADERS: Dict[CBSFormat, List[List[str]]] = {
    CBSFormat.T24: [
        ["GL_ACCOUNT_CODE", "DR_BAL", "CR_BAL", "PERIOD"],
        ["ACCOUNT_CODE", "DEBIT_BAL", "CREDIT_BAL", "PERIOD"],  # Alternate T24 export
    ],
    CBSFormat.FLEXCUBE: [
        ["ACCOUNT_NO", "DR_AMT", "CR_AMT", "VALUE_DATE"],
        ["AC_NO", "DEBIT_AMOUNT", "CREDIT_AMOUNT", "DATE"],
    ],
    CBSFormat.GENERIC_CSV: [
        ["account_code", "balance", "description"],
        ["account", "amount", "name"],
    ],
}

def _detect_xlsx(file_bytes: bytes) -> bool:
    """
    XLSX files are ZIP archives with specific magic bytes and structure.
    We check both the ZIP signature and presence of required entries.

    SECURITY:
    Malformed XLSX files could exploit ZIP library bugs.
    This check rejects obviously invalid files early.
    """
    try:
        # ZIP files start with PK signature (0x50 0x4B)
        if file_bytes[:2] != b'PK':
            return False
        # Try to open as ZIP and check for XLSX structure
        with zipfile.ZipFile(BytesIO(file_bytes), 'r') as zf:
            # XLSX files contain [Content_Types].xml at root
            return '[Content_Types.xml]' in zf.namelist()
    except (zipfile.BadZipFile, Exception):
        return False
    

def _detect_csv(file_bytes: bytes, sample_lines: int = 5) -> Tuple[bool, Optional[List[str]]]:
    """
    Detect if file is a valid CSV and extract first row headers.

    ENCODING DETECTION:
    CBS exports may use different encodings. We try common ones:
    - UTF-8: Modern systems
    - Windows-1252: Legacy Windows systems
    - Latin-1: Fallback

    Returns:
        Tuple of (is_csv, headers_list or None)
    """

    encodings = ['utf-8-sig', 'utf-8', 'windows-1252', 'latin-1']

    for encoding in encodings:
        try:
            content = file_bytes.decode(encoding)
            lines = content.strip().split('\n')[:sample_lines]

            if not lines:
                continue

            # Parse first line as CSV
            reader = csv.reader([lines[0]])
            headers = next(reader, None)

            if headers and len(headers) >=2:
                # clean headers
                headers = [h.strip() for h in headers]
                return True, headers
        
        except (UnicodeDecodeError, csv.Error):
            continue
    return False, None




def detect_format(file_bytes: bytes, filename: str) -> Tuple[CBSFormat, Optional[List[str]]]:
     """
    Detect the CBS format of an uploaded file.

    DETECTION STRATEGY:
    1. Check file extension for .xlsx vs .csv
    2. Validate file structure matches extension
    3. Extract headers and match against known patterns
    4. Return detected format for downstream processing

    Args:
        file_bytes: Raw file content
        filename: Original filename for extension check

    Returns:
        Tuple of (detected_format, headers_list)
        headers_list is None for XLSX (read later with openpyxl)

    USAGE:
        format, headers = detect_format(file_bytes, "GL_Export.csv")
        if format == CBSFormat.UNKNOWN:
            raise ValueError("Unknown CBS format")
    """
     filename_lower = filename.lower()

     # check for xlsx
     if filename_lower.endswith('.xlsx'):
         if _detect_xlsx(file_bytes):
             return CBSFormat.GENERIC_CSV, None # Will read with openpyxl later
         raise ValueError("File claims to be XLSX but is not a valid Excel file")
     
     # check for csv
     if filename_lower.endswith('.csv') or filename_lower.endswith('.txt'):
         is_csv, headers = _detect_csv(file_bytes)
         if not is_csv:
             raise ValueError("File is not a valid CSV")
         
         # match headers against known formats
         for cbs_format, header_patterns in EXPECTED_HEADERS.items():
             if cbs_format == CBSFormat.GENERIC_CSV:
                 continue
             
             for pattern in header_patterns:
                 headers_upper = {h.upper() for h in headers}
                 pattern_upper = {p.upper() for p in pattern}

                 matches = sum(1 for p in pattern_upper if p in headers_upper)
                 if matches >= 3:
                     return cbs_format, headers
                
         return CBSFormat.GENERIC_CSV, headers
     
     raise ValueError(f"Unsupported file type: {filename}")
         
    
def validate_file_size(file_bytes: bytes, max_size_mb: int) -> None:
    """
    Validate file size is within limits.

    Security Reason:
    Large files can cause memory exhaustion or processing delays.
    T24 GL extracts for medium banks are typically < 10MB.
    """
    file_size = len(file_bytes)
    max_bytes = max_size_mb * 1024 * 1024

    if file_size > max_bytes:
        raise ValueError(
            f"File size ({file_size / (1024*1024):.1f} MB) exceeds "
            f"maximum allowed ({max_size_mb} MB)"
        )
    


def compute_hash(file_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of file for chain of custody.

    This hash is the cryptographic fingerprint that ties
    all downstream calculations to this specific input file.

    USAGE:
        file_hash = compute_hash(file_bytes)
        # Store in raw_submissions.file_hash
        # Include in DFS file and PDF audit section
    """
    import hashlib
    return hashlib.sha256(file_bytes).hexdigest()