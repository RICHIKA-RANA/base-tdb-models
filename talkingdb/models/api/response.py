from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: Optional[str] = Field(None, description="Field that caused the error, if applicable")
    message: str = Field(..., description="Human-readable error message")


class ErrorResponse(BaseModel):
    error_code: str = Field(..., description="Machine-readable error code (e.g., UNSUPPORTED_FILE_TYPE)")
    message: str = Field(..., description="Human-readable error summary")
    details: Optional[List[ErrorDetail]] = Field(None, description="Additional error details")
    supported_types: Optional[List[str]] = Field(None, description="Supported file types, included for type errors")
    max_file_size_mb: Optional[int] = Field(None, description="Maximum allowed file size in MB, included for size errors")
