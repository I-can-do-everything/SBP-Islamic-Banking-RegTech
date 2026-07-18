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

    
