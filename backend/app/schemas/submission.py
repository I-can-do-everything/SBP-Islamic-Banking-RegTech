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


# AI commentary schema

class CommentaryResponse(BaseModel):
    submission_id: str
    commentary: str
    confidence_score: str
    hallucination_flags: List[str] = []
    source: str # ollama or fallback template
    generated_at: datetime



# Processing result schema
class ProcessingResult(BaseModel):
    """result returned immediately after running the pipeline"""
    submission_id: str
    status: str
    records_read: int
    detected_format: str
    accounts_normalised: int
    ratios_calculated: int
    validation_summary: Dict[str, int]
    reports: Dict[str, str]
    commentary_source: str
    warnings: List[str]
    processing_time_seconds: float


# Audit log schemas
class AuditLogEntry(BaseModel):
    """A single audit log record"""
    id: str
    occured_at: datetime
    username: Optional[str] = None
    role: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    institution_code: Optional[str] = None
    success: bool
    details: Optional[str] = None

class AuditLogList(BaseModel):
    """paginated audit log"""
    items: List[AuditLogEntry]
    total: int
    page: int
    page_size: int


# ratio schemas
class RatioResponse(BaseModel):
    "response for a calculated ratio"
    ratio_name: str
    ratio_value: str
    numerator: str
    denominator: str
    formula_applied: str
    breach_flag: bool
    regulatory_minimum: Optional[str] = None
    regulatory_maximum: Optional[str] = None
    sbp_circular_reference: Optional[str] = None

class RatiosList(BaseModel):
    """list of calculated ratios"""
    submission_id: str
    ratios: List[RatioResponse]


# validation schemas
class ValidationCheckResponse(BaseModel):
    """Response for a validation check"""
    validation_type: str
    check_name: str
    status: str
    field_path: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    details: Optional[str] = None
    sbp_circular_reference: Optional[str] = None


class ValidationSummary(BaseModel):
    """summary of validation results"""
    submission_id: str
    overall_status: str
    failed_count: int
    warning_count: int
    passed_count: int
    checks: List[ValidationCheckResponse]

    
# report schemas
class ReportInfo(BaseModel):
    """info about a generated report"""
    id: str
    report_format: str
    file_hash: str
    file_size_bytes: int
    generated_at: datetime
    download_expires_at: datetime
    download_url: Optional[str] = None

class ReportList(BaseModel):
    """available reports"""
    submission_id: str
    reports: List[ReportInfo]

class DownloadResponse(BaseModel):
    """response for download request"""
    download_url: str
    expires_at: datetime
    report_id: str



# pipleline progress schemas
class PipelineProgress(BaseModel):
    "progress event from processing pipeline"
    stage: str
    status: str
    message: Optional[str] = None
    details: Optional[dict] = None


class PipelineResult(BaseModel):
    """final result of the pipleline execution"""
    submission_id: str
    status: str
    reports: Dict[str, str]
    processing_time_seconds: float
    errors: List[str]
    warnings: List[str]

# user schemas
class UserCreate(BaseModel):
    """create a new user"""
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=15, description="Password minimum 8 characters")
    institution_code: str = Field(..., min_length=2, max_length=10)
    role: str = Field(default="UPLOADER", description="UPLOADER, REVIEWER, or ADMIN")


class UserLogin(BaseModel):
    """login req"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """response for auth token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    "user info response"
    id: str
    username: str
    email: str
    role: str
    institution_code: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)







    






    