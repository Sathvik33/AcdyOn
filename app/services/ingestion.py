import logging
from datetime import datetime, timezone
from typing import Optional, Type

from sqlalchemy.orm import Session

from app.db.models import Job, IngestionRun
from app.schemas.job import IngestionResult, JobCreate
from app.sources.base import BaseJobSource
from app.sources.jobicy import JobicySource
from app.sources.mock_fallback import MockFallbackSource

logger = logging.getLogger(__name__)


SOURCE_REGISTRY: dict[str, Type[BaseJobSource]] = {
    "jobicy": JobicySource,
    "mock_fallback": MockFallbackSource,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_existing_external_ids(db: Session, source: str) -> set[str]:
    rows = db.query(Job.external_id).filter(Job.source == source).all()
    return {row[0] for row in rows}


def run_ingestion(db: Session, source_name: str = "jobicy", count: Optional[int] = None) -> IngestionResult:
    source_cls = SOURCE_REGISTRY.get(source_name)
    if source_cls is None:
        return IngestionResult(
            status="FAILED",
            source=source_name,
            jobs_found=0,
            jobs_inserted=0,
            jobs_skipped=0,
            run_id=-1,
            error_message=f"Unknown source: {source_name}",
        )

    run = IngestionRun(
        source=source_name,
        started_at=_now(),
        status="RUNNING",
        jobs_found=0,
        jobs_inserted=0,
        jobs_skipped=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info("INGESTION_STARTED", extra={"run_id": run.id, "source": source_name})

    source = source_cls(count=count) if count else source_cls()

    fetch_result = source.fetch()
    if not fetch_result.ok:
        status = "RATE_LIMITED" if fetch_result.rate_limited else "FAILED"
        run.completed_at = _now()
        run.status = status
        run.error_message = fetch_result.error
        db.commit()
        logger.warning(
            "INGESTION_COMPLETED",
            extra={
                "run_id": run.id,
                "source": source_name,
                "status": status,
                "jobs_found": 0,
                "jobs_inserted": 0,
                "jobs_skipped": 0,
            },
        )
        return IngestionResult(
            status=status,
            source=source_name,
            jobs_found=0,
            jobs_inserted=0,
            jobs_skipped=0,
            run_id=run.id,
            error_message=fetch_result.error,
        )

    try:
        raw_jobs = source.parse(fetch_result.body)
    except Exception as e:
        msg = f"Parse failed: {e}"
        logger.error("PARSE_FAILED", extra={"run_id": run.id, "source": source_name, "error": msg})
        run.completed_at = _now()
        run.status = "FAILED"
        run.error_message = msg
        db.commit()
        return IngestionResult(
            status="FAILED",
            source=source_name,
            jobs_found=0,
            jobs_inserted=0,
            jobs_skipped=0,
            run_id=run.id,
            error_message=msg,
        )

    jobs_found = len(raw_jobs)
    run.jobs_found = jobs_found
    db.commit()

    valid_jobs: list[JobCreate] = []
    malformed = 0

    for raw in raw_jobs:
        try:
            job = source.normalize(raw)
            valid_jobs.append(job)
        except Exception as e:
            malformed += 1
            logger.warning(
                "JOB_NORMALIZE_FAILED",
                extra={"run_id": run.id, "source": source_name, "error": str(e)[:200]},
            )
            continue

    existing_ids = _get_existing_external_ids(db, source_name)
    new_jobs: list[Job] = []
    skipped = 0

    for job in valid_jobs:
        if job.external_id in existing_ids:
            skipped += 1
            logger.info(
                "JOB_DUPLICATE",
                extra={"run_id": run.id, "source": source_name, "external_id": job.external_id},
            )
            continue
        db_job = Job(
            source=job.source,
            external_id=job.external_id,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            url=job.url,
            employment_type=job.employment_type,
            published_at=job.published_at,
            raw_data_hash=job.raw_data_hash,
            fetched_at=_now(),
        )
        new_jobs.append(db_job)
        existing_ids.add(job.external_id)

    if new_jobs:
        db.bulk_save_objects(new_jobs)
        db.commit()
        for db_job in new_jobs:
            logger.info(
                "JOB_INSERTED",
                extra={"run_id": run.id, "source": source_name, "external_id": db_job.external_id},
            )

    inserted = len(new_jobs)
    skipped_total = skipped + malformed

    # Status logic
    if malformed > 0 and inserted > 0:
        final_status = "PARTIAL"
    elif malformed > 0 and inserted == 0:
        final_status = "FAILED"
    elif inserted > 0:
        final_status = "SUCCESS"
    elif jobs_found == 0:
        logger.warning("INGESTION_EMPTY_RESPONSE", extra={"run_id": run.id, "source": source_name})
        final_status = "SUCCESS"  # fetch succeeded but source had no jobs; logged
    elif skipped > 0 and inserted == 0:
        final_status = "SUCCESS"  # all jobs already known
    else:
        final_status = "SUCCESS"

    run.completed_at = _now()
    run.status = final_status
    run.jobs_inserted = inserted
    run.jobs_skipped = skipped_total
    run.error_message = None if final_status == "SUCCESS" else run.error_message
    db.commit()
    db.refresh(run)

    logger.info(
        "INGESTION_COMPLETED",
        extra={
            "run_id": run.id,
            "source": source_name,
            "status": final_status,
            "jobs_found": jobs_found,
            "jobs_inserted": inserted,
            "jobs_skipped": skipped_total,
            "malformed": malformed,
        },
    )

    return IngestionResult(
        status=final_status,
        source=source_name,
        jobs_found=jobs_found,
        jobs_inserted=inserted,
        jobs_skipped=skipped_total,
        run_id=run.id,
    )
