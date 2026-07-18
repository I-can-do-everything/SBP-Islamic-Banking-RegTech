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








