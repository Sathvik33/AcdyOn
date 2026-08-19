from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Job, IngestionRun, SourceHealth
from app.schemas.job import (
    JobListResponse,
    JobResponse,
    IngestionRunResponse,
    IngestionResult,
    SourceHealthResponse,
    StatsResponse,
)
from app.services.ingestion import (
    run_ingestion,
    get_or_create_source_health,
    SOURCE_REGISTRY,
)

router = APIRouter()


@router.get("/health", response_model=dict)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(func.now())
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    search: Optional[str] = Query(None, description="Search in title or company"),
    source: Optional[str] = Query(None, description="Filter by source"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if source:
        query = query.filter(Job.source == source)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Job.title.ilike(like), Job.company.ilike(like)))

    total = query.count()
    items = (
        query.order_by(Job.published_at.desc().nullslast(), Job.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.get("/ingestion/runs", response_model=list[IngestionRunResponse])
def list_ingestion_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [IngestionRunResponse.model_validate(r) for r in runs]


@router.post("/ingestion/run", response_model=IngestionResult)
def trigger_ingestion(
    source: str = Query("jobicy", description="Source to ingest from"),
    count: Optional[int] = Query(None, ge=1, le=200, description="Number of jobs to fetch"),
    allow_fallback: bool = Query(True, description="Enable automatic fallback if primary is blocked"),
    db: Session = Depends(get_db),
):
    result = run_ingestion(db, source_name=source, count=count, allow_fallback=allow_fallback)
    return result


@router.get("/sources/health", response_model=list[SourceHealthResponse])
def list_source_health(db: Session = Depends(get_db)):
    # Ensure registered sources have DB health records initialized
    for src in SOURCE_REGISTRY.keys():
        get_or_create_source_health(db, src)
    records = db.query(SourceHealth).order_by(SourceHealth.source.asc()).all()
    return [SourceHealthResponse.model_validate(r) for r in records]


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total_jobs = db.query(Job).count()
    latest_run = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .first()
    )

    primary_h = get_or_create_source_health(db, settings.primary_source)
    fallback_h = get_or_create_source_health(db, settings.fallback_source)

    if latest_run:
        return StatsResponse(
            total_jobs=total_jobs,
            latest_run_status=latest_run.status,
            latest_run_inserted=latest_run.jobs_inserted,
            latest_run_skipped=latest_run.jobs_skipped,
            latest_run_at=latest_run.started_at,
            primary_source_health=primary_h.health_state,
            fallback_source_health=fallback_h.health_state,
        )
    return StatsResponse(
        total_jobs=total_jobs,
        primary_source_health=primary_h.health_state,
        fallback_source_health=fallback_h.health_state,
    )
