"""
Database models - simplified for Supabase REST API.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from __future__ import annotations


# Raw Submissions
class RawSubmission:
    id: uuid.UUID
    institution_code: str
    reporting_period_start: datetime
    reporting_period_end: datetime
    file_hash: str
    file_path: str
    original_filename: str
    file_size_bytes: int
    cbs_format: str
    dfs_version: str
    status: str
    uploaded_by: str
    uploaded_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


    @classmethod
    def from_dict(cls, data: dict) -> RawSubmission:
        return cls(**data)
    
    def to_dict(self) -> dict:
        return {
                "id": str(self.id) if hasattr(self, 'id') else None,
                "institution_code": self.institution_code,
                "reporting_period_start": self.reporting_period_start.isoformat() if isinstance(self.reporting_period_start, datetime) else self.reporting_period_start,
                "reporting_period_end": self.reporting_period_end.isoformat() if isinstance(self.reporting_period_end, datetime) else self.reporting_period_end,
                "file_hash": self.file_hash,
                "file_path": self.file_path,
                "original_filename": self.original_filename,
                "file_size_bytes": self.file_size_bytes,
                "cbs_format": self.cbs_format,
                "dfs_version": self.dfs_version,
                "status": self.status,
                "uploaded_by": self.uploaded_by,
                "uploaded_at": self.uploaded_at.isoformat() if isinstance(self.uploaded_at, datetime) else self.uploaded_at,
                "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
                "processing_completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
                "error_message": self.error_message,
            }

