from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class JobBase(BaseModel):
    source: str = Field(..., max_length=64)
    external_id: str = Field(..., max_length=128)
    user_id: Optional[str] = Field("default", max_length=128)
    title: Optional[str] = Field(None, max_length=512)
    company: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = Field(None, max_length=2048)
    employment_type: Optional[str] = Field(None, max_length=64)
    published_at: Optional[datetime] = None
    raw_data_hash: Optional[str] = Field(None, max_length=64)


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fetched_at: datetime
    created_at: datetime


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    user_id: Optional[str] = "default"
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    jobs_found: int
    jobs_inserted: int
    jobs_skipped: int
    duration_seconds: Optional[float] = None
    parse_failures: int = 0
    duplicate_count: int = 0
    http_status: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None


class IngestionResult(BaseModel):
    status: str
    source: str
    user_id: Optional[str] = "default"
    jobs_found: int
    jobs_inserted: int
    jobs_skipped: int
    run_id: int
    duration_seconds: Optional[float] = None
    parse_failures: int = 0
    duplicate_count: int = 0
    http_status: Optional[int] = None
    retry_count: int = 0
    fallback_used: bool = False
    error_message: Optional[str] = None


class SourceHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    health_state: str
    consecutive_failures: int
    last_successful_run: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_http_status: Optional[int] = None
    last_response_latency: Optional[float] = None
    updated_at: datetime


class StatsResponse(BaseModel):
    total_jobs: int
    latest_run_status: Optional[str] = None
    latest_run_inserted: int = 0
    latest_run_skipped: int = 0
    latest_run_at: Optional[datetime] = None
    primary_source_health: Optional[str] = None
    fallback_source_health: Optional[str] = None

