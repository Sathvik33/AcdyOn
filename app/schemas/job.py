from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class JobBase(BaseModel):
    source: str = Field(..., max_length=64)
    external_id: str = Field(..., max_length=128)
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
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    jobs_found: int
    jobs_inserted: int
    jobs_skipped: int
    error_message: Optional[str] = None


class IngestionResult(BaseModel):
    status: str
    source: str
    jobs_found: int
    jobs_inserted: int
    jobs_skipped: int
    run_id: int
    error_message: Optional[str] = None


class StatsResponse(BaseModel):
    total_jobs: int
    latest_run_status: Optional[str] = None
    latest_run_inserted: int = 0
    latest_run_skipped: int = 0
    latest_run_at: Optional[datetime] = None
