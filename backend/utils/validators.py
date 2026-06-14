from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List


class EntityExtractionRequest(BaseModel):
    query: str
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v


class IntentParsingResponse(BaseModel):
    intent: str
    entities: Dict[str, Optional[Any]]
    confidence: float


class FilterApplyRequest(BaseModel):
    query: str
    apply_filters: bool = True


class FilterResponse(BaseModel):
    filters: List[Dict[str, Any]]
    dax_generated: str
    status: str
    filter_count: int


class ErrorResponse(BaseModel):
    error: str
    status: str = "error"
    details: Optional[Dict[str, Any]] = None
