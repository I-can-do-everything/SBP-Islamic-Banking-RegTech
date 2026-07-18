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


# Environment loading
# # Resolve candidate .env locations relative to THIS FILE so behaviour is
# identical no matter what the current working directory is (bare `uvicorn`
# from backend/, Docker with WORKDIR=/app, or PYTHONPATH tricks).
#
# backend/app/core/config.py -> parents[0]=core [1]=app [2]=backend [3]=repo root
_THIS_FILE = Path(__file__).resolve()
_BACKEND_DIR = _THIS_FILE.parents[2]
_REPO_ROOT = _THIS_FILE.parents[3] if len(_THIS_FILE.parents) > 3 else _BACKEND_DIR

for _candidate in (
    _BACKEND_DIR / ".env",
    _REPO_ROOT / ".env",
    Path.cwd() / ".env",
):
    if _candidate.exists():
        load_dotenv(_candidate, override=False)
        break



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


# Application settings.
class Settings(BaseSettings):
    """
    Application settings loaded for env variables.

    Security Architecture:
    - all secrets are optional with empty defaults for failsafe mechanism
    - Production deployments MUST set these via environment
    - Settings are cached via @lru_cache for performance

    Extensibility:
    - add new settings for external integrations (for example, I might connect it to DAP4 API)
    - add feature flags for progressive rollout of new calculations.
    """

    # Application
    APP_NAME: str = "SBP Islamic Regulatory Reporting System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT : str = "development"

    # DBs : Supabase PostgreSQL
    # pre-populated in the hosted env
    DATABASE_URL: str = ""
    DB_ECHO: bool = False




    # Supabase (alternatively use direct connection)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = "" 


    # Security
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_HOURS: int = 24


    # File storage
    RAW_UPLOAD_DIR: str = "uploads/raw"
    REPORT_DIR: str = "uploads/reports"
    MAX_FILE_SIZE_MB: int = 50

    # Download Tokens
    DOWNLOAD_TOKEN_EXPIRE_MINUTES: int = 30

    # Default accounts seeded on first startup if the users table is empty.
    # Change these (or the seeded accounts' passwords, after login) before
    # any real deployment: they are intentionally obvious placeholders.
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "ChangeMe123!"
    DEFAULT_DEMO_USERNAME: str = "meezan_officer"
    DEFAULT_DEMO_PASSWORD: str = "ChangeMe123!"
    DEFAULT_DEMO_INSTITUTION: str = "MEEZ"
    REPORT_RETENTION_HOURS: int = 24


    # Ollama Configuration
    # Local-only for data sovereignty compliance
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_TEMPERATURE: float = 0.0  # MUST be 0.0 for deterministic output
    OLLAMA_KEEP_ALIVE: str = "-1"  # Keep model loaded in memory


    # SBP Circular monitor
    CIRCULAR_CHECK_INTERVAL: int = 6
    SBP_BPRD_URL: str = "https://www.sbp.org.pk/bprd/"
    SBP_IFPD_URL: str = "https://www.sbp.org.pk/ifpd/"


    # Rate Limiting
    MAX_UPLOADS_PER_HOUR: int = 10
    MAX_DOWNLOADS_PER_HOUR: int = 20
    MAX_AUTH_ATTEMPTS_PER_10MIN: int = 5


    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure that the secret key is changed from default in production"""
        if v == "change-this-in-production-use-openssl-rand-hex-32":
            import warnings
            warnings.warn("Using default SECRET_KEY. MUST change in production!")
        return v
    
@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings accessor.

    USAGE:
        from app.core.config import get_settings
        settings = get_settings()

    WHY CACHE:
    - Settings are read from environment on first call
    - Subsequent calls return cached instance
    - Prevents repeated file I/O and env parsing
    """
    return Settings()


# =============================================================================
# REGULATORY CONSTANTS - Add new SBP requirements here
#
# VERIFICATION STATUS (research conducted via public web
# search, not a licensed compliance/legal/Shariah review):
#
#   VERIFIED against public sources:
#     - CAR_MINIMUM = 11.5% matches SBP's published Basel III CAR requirement
#       and is independently corroborated by listed Islamic banks' disclosed
#       financials (e.g. Dubai Islamic Bank Pakistan Ltd, FY2023 disclosures).
#     - DEPOSITOR_SHARE_MIN = 75% reflects SBP's Nov 2024 instruction that
#       IBIs pay depositors at least 75% of the weighted average gross yield
#       of their investment pools (reported via Business Recorder, Nov 2024,
#       amending "Instructions for Profit & Loss Distribution and Pool
#       Management for IBIs", IBD Circular No. 03 of 2012, as amended).
#
#   PLAUSIBLE BUT NOT INDEPENDENTLY CONFIRMED at this exact figure:
#     - NPF_MAXIMUM, the DPD_THRESHOLDS day-counts, and PROVISION_RATES follow
#       the well-documented SBP asset classification pattern (OAEM /
#       Substandard / Doubtful / Loss with escalating provisioning), but the
#       *exact* day-thresholds differ across SBP's various Prudential
#       Regulation categories (Corporate/Commercial, SME, Agriculture,
#       Microfinance each have their own numbered regulation and slightly
#       different day-counts) and change on amendment. Confirm the values
#       below against the specific PR category and current circular that
#       applies to the institution before any real regulatory filing.
#     - PER_CAP_PERCENT / IRR_CAP_PERCENT: SBP's framework (IBD Circular
#       No. 03 of 2012, as amended) caps the *Mudarib's fee* for managing
#       PER/IRR funds at 10% of the return earned on those funds, and caps
#       IRR *contributions* at up to 1% of distributable pool profit - it
#       does not itself mandate a single economy-wide PER/IRR-to-pool-income
#       ratio for every bank. Individual banks set their own PER/IRR policy
#       (e.g. one major bank's public policy caps PER at 30% of Islamic
#       Banking Equity) within SBP's framework and Shariah Board approval.
#       Treat these two constants as indicative thresholds for this
#       prototype's ratio display, not a verified universal SBP limit.
#
#   NOT FOUND / LIKELY FABRICATED:
#     - The original codebase cited specific circular numbers (e.g.
#       "BSD-1 Circular 01/2025", "IBD Circular 02/2019", "IFPD Circular
#       08/2024", "IFPD Circular 09/2024") that could not be located in any
#       public SBP source. "IFPD" in particular does not appear to be a real
#       SBP department code (real ones include IBD, BPRD, BSD, SMEFD,
#       AC&MFD). These looked like plausible-sounding but invented
#       citations, consistent with an AI-generated first draft. They have
#       been replaced below with honest, non-specific framework references.
# =============================================================================


REGULATORY_DISCLAIMER = (
    "Ratios, thresholds and circular references in this report are generated "
    "by a prototype system for illustrative purposes. They have not been "
    "certified by a licensed compliance officer, lawyer, or Shariah advisor, "
    "and must be independently verified against SBP's current consolidated "
    "Prudential Regulations and circulars before regulatory use."
)

CAR_MINIMUM = Decimal("11.5")  # Percentage


NPF_MAXIMUM = Decimal("7.0")  # Percentage


DPD_THRESHOLDS = {
    "PERFORMING": 0,
    "OAEM": 1,      # Other Assets Especially Mentioned (watch list)
    "SUBSTANDARD": 91,   # 25% provision required
    "DOUBTFUL": 181,     # 50% provision required
    "LOSS": 366        # 100% provision required
}

# Provision rates per NPF classification
PROVISION_RATES = {
    "PERFORMING": Decimal("0"),
    "OAEM": Decimal("0"),
    "SUBSTANDARD": Decimal("0.25"),
    "DOUBTFUL": Decimal("0.50"),
    "LOSS": Decimal("1.00")
}

# Pool Management parameters, indicative for this prototype; see note above
# for what SBP's IBD Circular No. 03 of 2012 (as amended) actually caps.
PER_CAP_PERCENT = Decimal("20.0")  # Profit Equalisation Reserve max (indicative)
IRR_CAP_PERCENT = Decimal("10.0")  # Investment Risk Reserve max (indicative)
DEPOSITOR_SHARE_MIN = Decimal("75.0")  # Verified: SBP min. 75% of pool gross yield (Nov 2024)


# RCOA Code Ranges for Islamic Banking Products
# ADD NEW CODES: When SBP introduces new Islamic product categories
RCOA_RANGES = {
    # Financing Assets (3590 series)
    "MURABAHA": "3590-MUR",
    "IJARAH": "3590-IJA",
    "DIMINISHING_MUSHARAKAH": "3590-DM",
    "SALAM": "3590-SAL",
    "ISTISNA": "3590-IST",

    # Pool Liabilities (2150 series)
    "MUDARABAH_DEPOSITS": "2150-MUD",
    "WAKALA_DEPOSITS": "2150-WAK",

    # Capital Accounts
    "PAID_UP_CAPITAL": "1100-PUC",
    "STATUTORY_RESERVES": "1200-SR",
    "RETAINED_EARNINGS": "1300-RE",

    # Non-Performing Financing
    "NPF_MURABAHA": "3595-MUR-NPF",
    "NPF_IJARAH": "3595-IJA-NPF",
    "NPF_DM": "3595-DM-NPF",
}

# DFS File Structure - confirm current format circular with SBP offsite supervision/BPRD
DFS_VERSION = "BSD1-01-2025"
DFS_RECORD_TYPES = {
    "HEADER": "HDR",
    "DATA": "DAT",
    "TRAILER": "TRL",
}
