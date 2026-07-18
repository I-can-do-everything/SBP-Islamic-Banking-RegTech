"""
Core configuration for Pakistani Islamic Bank Regulatory Reporting.
"""

import os 
from enum import Enum 
from decimal import Decimal 
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv



# The idea is to first establish some sort of states which will help track the submission status.
class SubmissionStatus(str, Enum):
    """
    Decided Transitions:
    - Recieved: File uploaded, hash computed, awaiting processing
    - Processing: Active pipeline execution (normalising, calculating, validating)
    - Complete: All layers finished, reports generated successfully
    - Failed: One of more layers failed. Debugging required.

    More intermediate states can be added like the middle processing validating, generating,
    and so on.
    Every state transition should be logged for audit.
    """

    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# Now, there are some core banking system export formats.
# Format detection sounds like a reasonable next step.

class CBSFormat(str, Enum):
    """
    Formats:
    - T24: Temenos T24 is apparently the most common system used in Pakistani Islamic Banks.
    - FLEXCUBE: Oracle Flexcube, widely used as well.
    - GENERIC_CSV: Standard CSV with configurable column mapping.

    There will eventually be more CBS added, somethings to note right now would be:
    - There is a data ingestion layer and it'll have the format detector functions for every CBS, meaning a new
    CBS means a new function will have to be created.
    - Similarly, a column mapping in the mappings file will be created.
    """

    T24 = "T24"
    FLEXCUBE = "FLEXCUBE"
    GENERIC_CSV = "GENERIC_CSV"
    UNKNOWN = "UNKNOWN"


# The banks perform certain validation checks on normalised data.
# My knowledge and the code for this needs updating as I sense some unclarity.

class ValidationCheckType(str, Enum):
    """
    Each type corresponds to a different regulatory requirement:
    - CROSS_RETURN: Numbers appearing in multiple places must match.
    - DFS_FORMAT: Regulatory submission file structure/format compliance
    - SHARIAH: Islamic banking specific compliance checks.
    - BREACH: Regulatory threshold violations.
    - IFRS9: ECL stage consistency (expected credit loss staging)
    """
    CROSS_RETURN = "CROSS_RETURN"
    DFS_FORMAT = "DFS_FORMAT"
    IFRS9 = "IFRS9"
    SHARIAH = "SHARIAH"
    BREACH = "BREACH"

# Just like the submission states, it would be a consistent practise if the validations had states too.

class ValidationStatus(str, Enum):
    """
    Semantics:
    - PASS: Check Succeeded, no action needed.
    - FAIL: Check failed, submission cannot proceed.
    - WARNING: Check passed but got flagged for attention.

    When to use WARNING:
    - CAR ratio at exactly 11.5% (min threshold)
    - NPF approaching 7% limit
    - PER approaching 20% cap

    One drastic thing to note is that this information is surface level,
    meaning I got it from sources that could be verified further just for the
    sake of building the system and getting the logics down.
    That goes for pretty much everything. These will be verified and tweaked as per
    up to date information.
    """
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


