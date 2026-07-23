"""
Layer 1: Ingestion Module

Accepts CBS export files, validates format, computes hash, and stores securely.

MAIN ENTRY POINT:
    from app.layers.ingestion.file_reader import read_file


    # Read file for processing
    records, format = read_file(file_bytes, filename)

EXPORTS:
- read_file: Parse CBS file into account records
- detect_format: Determine CBS format from file content
- compute_hash: SHA-256 for chain of custody
"""

from app.layers.ingestion.file_reader import read_file
from app.layers.ingestion.format_detector import (
    detect_format,
    validate_file_size,
    compute_hash,
    CBSFormat,
)

__all__ = [
    "read_file",
    "detect_format",
    "validate_file_size",
    "compute_hash",
    "CBSFormat",
]