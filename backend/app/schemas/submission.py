"""
Pydantic Schemas for API request/response validation

Contract between frontend and backend
- Input validation
- Output serialisation
- Documentation generation

To extend:
- add new schemas for new endpoints
- optional for optional fields
- field decriptions for openapi docs
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field



#submission schemas

class SubmissionCreate(BaseModel):
    """request to create a new submission"""
    institution_code: str = Field(..., min_length=2, max_length=10, description="Bank institution code")
    reporting_period_start: datetime = Field(..., description="Start of reporting period")
    reporting_period_end: datetime = Field(..., description="End of reporting period")
    uploaded_by: str = Field(..., description="User who uploaded the file")


class SubmissionResponse(BaseModel):
    """response after creating a submission"""
    id: str
    institution_code: str
    reporting_period_start: datetime
    reporting_period_end: datetime
    file_hash: str
    original_filename: str
    cbs_format: str
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionDetail(SubmissionResponse):
    """Detailed submission information with processing results"""
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    File_size_bytes: int

class SubmissionList(BaseModel):
    """Paginated list of Submissions"""
    items: List[SubmissionResponse]
    total: int
    page: int
    page_size: int


class SubmissionStats(BaseModel):
    """Aggregate Dashboard stats across all submissions"""
    total: int
    received: int
    processing: int
    complete: int
    failed: int
    success_rate: float
    breach_count: int



# Normalised balance schemas

class NormalisedBalanceResponse(BaseModel):
    """A single aggregated RCOA balance for a submission"""
    rcoa_account_code: str
    rcoa_account_description: Optional[str] = None
    balance: str
    currency: str = "PKR"
    mapping_rule: Optional[str] = None
    source_codes: Optional[str] = None

class BalancesList(BaseModel):
    """List of normalised balances for a submission"""
    submission_id: str
    balances: List[NormalisedBalanceResponse]

    


    