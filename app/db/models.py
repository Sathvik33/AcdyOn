from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(64), nullable=False, index=True)
    external_id = Column(String(128), nullable=False, index=True)
    title = Column(String(512), nullable=True, index=True)
    company = Column(String(255), nullable=True, index=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(2048), nullable=True)
    employment_type = Column(String(64), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_data_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(64), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, index=True)
    jobs_found = Column(Integer, nullable=False, default=0)
    jobs_inserted = Column(Integer, nullable=False, default=0)
    jobs_skipped = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=True)
    parse_failures = Column(Integer, nullable=False, default=0)
    duplicate_count = Column(Integer, nullable=False, default=0)
    http_status = Column(Integer, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)


class SourceHealth(Base):
    __tablename__ = "source_health"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(64), nullable=False, unique=True, index=True)
    health_state = Column(String(32), nullable=False, default="HEALTHY", index=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_successful_run = Column(DateTime(timezone=True), nullable=True)
    last_failure = Column(DateTime(timezone=True), nullable=True)
    last_http_status = Column(Integer, nullable=True)
    last_response_latency = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

