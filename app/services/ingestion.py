import logging
import time
from datetime import datetime, timezone
from typing import Optional, Type

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Job, IngestionRun, SourceHealth
from app.schemas.job import IngestionResult, JobCreate
from app.sources.base import BaseJobSource
from app.sources.jobicy import JobicySource
from app.sources.remotive import RemotiveSource
from app.sources.mock_fallback import MockFallbackSource

logger = logging.getLogger(__name__)

SOURCE_REGISTRY: dict[str, Type[BaseJobSource]] = {
    "jobicy": JobicySource,
    "remotive": RemotiveSource,
    "mock_fallback": MockFallbackSource,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_existing_external_ids(db: Session, source: str, user_id: str = "default") -> set[str]:
    rows = db.query(Job.external_id).filter(Job.source == source, Job.user_id == user_id).all()
    return {row[0] for row in rows}


def get_or_create_source_health(db: Session, source_name: str) -> SourceHealth:
    health = db.query(SourceHealth).filter(SourceHealth.source == source_name).first()
    if not health:
        try:
            health = SourceHealth(
                source=source_name,
                health_state="HEALTHY",
                consecutive_failures=0,
            )
            db.add(health)
            db.commit()
            db.refresh(health)
        except Exception:
            db.rollback()
            health = db.query(SourceHealth).filter(SourceHealth.source == source_name).first()
    return health


def check_circuit_breaker(db: Session, source_name: str) -> tuple[bool, str]:
    """
    Checks if a source is circuit-broken.
    Returns (is_blocked, health_state).
    """
    health = get_or_create_source_health(db, source_name)
    if health.health_state in ("BLOCKED", "UNAVAILABLE"):
        # Check cooldown period
        last_event = health.last_failure or health.updated_at
        if last_event:
            # Ensure naive timezone handling compatibility
            if last_event.tzinfo is None:
                last_event = last_event.replace(tzinfo=timezone.utc)
            elapsed = (_now() - last_event).total_seconds()
            if elapsed >= settings.circuit_breaker_cooldown_seconds:
                logger.info(
                    "CIRCUIT_BREAKER_COOLDOWN_EXPIRED",
                    extra={"source": source_name, "elapsed": elapsed},
                )
                health.health_state = "DEGRADED"
                db.commit()
                return False, "DEGRADED"
        return True, health.health_state
    return False, health.health_state


def update_source_health(
    db: Session,
    source_name: str,
    success: bool,
    http_status: Optional[int] = None,
    latency: Optional[float] = None,
    error_msg: Optional[str] = None,
) -> SourceHealth:
    health = get_or_create_source_health(db, source_name)
    now = _now()

    if success:
        health.consecutive_failures = 0
        health.health_state = "HEALTHY"
        health.last_successful_run = now
        health.last_http_status = http_status
        health.last_response_latency = latency
    else:
        health.consecutive_failures += 1
        health.last_failure = now
        health.last_http_status = http_status
        health.last_response_latency = latency

        if http_status in (429, 401, 403):
            health.health_state = "BLOCKED"
        elif health.consecutive_failures >= settings.circuit_breaker_failure_threshold:
            health.health_state = "UNAVAILABLE"
        else:
            health.health_state = "DEGRADED"

    db.commit()
    db.refresh(health)
    return health


def get_historical_avg_jobs(db: Session, source_name: str, limit: int = 3) -> float:
    recent_runs = (
        db.query(IngestionRun)
        .filter(IngestionRun.source == source_name, IngestionRun.status == "SUCCESS")
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
        .all()
    )
    if not recent_runs:
        return 0.0
    return sum(r.jobs_found for r in recent_runs) / len(recent_runs)


def run_ingestion(
    db: Session,
    source_name: str = "jobicy",
    count: Optional[int] = None,
    allow_fallback: bool = True,
    user_id: str = "default",
) -> IngestionResult:
    start_time = time.monotonic()
    user_id = user_id or "default"

    # Circuit breaker check for requested source
    is_blocked, current_health = check_circuit_breaker(db, source_name)
    fallback_used = False
    target_source_name = source_name

    if is_blocked and allow_fallback:
        fallback_target = settings.fallback_source
        if fallback_target == source_name:
            fallback_target = "mock_fallback"
        logger.warning(
            "SOURCE_CIRCUIT_BREAKER_BLOCKED",
            extra={"source": source_name, "fallback": fallback_target, "state": current_health},
        )
        target_source_name = fallback_target
        fallback_used = True

    source_cls = SOURCE_REGISTRY.get(target_source_name)
    if source_cls is None:
        duration = round(time.monotonic() - start_time, 3)
        return IngestionResult(
            status="FAILED",
            source=target_source_name,
            user_id=user_id,
            jobs_found=0,
            jobs_inserted=0,
            jobs_skipped=0,
            run_id=-1,
            duration_seconds=duration,
            fallback_used=fallback_used,
            error_message=f"Unknown source: {target_source_name}",
        )

    run = IngestionRun(
        source=target_source_name,
        user_id=user_id,
        started_at=_now(),
        status="RUNNING",
        jobs_found=0,
        jobs_inserted=0,
        jobs_skipped=0,
        parse_failures=0,
        duplicate_count=0,
        retry_count=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(
        "INGESTION_STARTED",
        extra={"run_id": run.id, "source": target_source_name, "fallback_used": fallback_used},
    )

    source = source_cls(count=count) if count else source_cls()
    fetch_result = source.fetch()
    run.http_status = fetch_result.status_code
    run.retry_count = fetch_result.retry_count

    if not fetch_result.ok:
        status = "RATE_LIMITED" if fetch_result.rate_limited else "FAILED"
        duration = round(time.monotonic() - start_time, 3)
        run.completed_at = _now()
        run.status = status
        run.duration_seconds = duration
        run.error_message = fetch_result.error
        db.commit()

        update_source_health(
            db,
            source_name=target_source_name,
            success=False,
            http_status=fetch_result.status_code,
            latency=fetch_result.latency_seconds,
            error_msg=fetch_result.error,
        )

        logger.warning(
            "INGESTION_COMPLETED",
            extra={
                "run_id": run.id,
                "source": target_source_name,
                "status": status,
                "duration": duration,
            },
        )
        return IngestionResult(
            status=status,
            source=target_source_name,
            jobs_found=0,
            jobs_inserted=0,
            jobs_skipped=0,
            run_id=run.id,
            duration_seconds=duration,
            parse_failures=0,
            duplicate_count=0,
            http_status=fetch_result.status_code,
            retry_count=fetch_result.retry_count,
            fallback_used=fallback_used,
            error_message=fetch_result.error,
        )

    # Parse response body
    try:
        raw_jobs = source.parse(fetch_result.body)
    except Exception as e:
        msg = f"Parse failed: {e}"
        duration = round(time.monotonic() - start_time, 3)
        logger.error("PARSE_FAILED", extra={"run_id": run.id, "source": target_source_name, "error": msg})
        run.completed_at = _now()
        run.status = "FAILED"
        run.duration_seconds = duration
        run.error_message = msg
        db.commit()

        update_source_health(
            db,
            source_name=target_source_name,
            success=False,
            http_status=fetch_result.status_code,
            latency=fetch_result.latency_seconds,
            error_msg=msg,
        )

        return IngestionResult(
            status="FAILED",
            source=target_source_name,
            jobs_found=0,
            jobs_inserted=0,
            jobs_skipped=0,
            run_id=run.id,
            duration_seconds=duration,
            http_status=fetch_result.status_code,
            retry_count=fetch_result.retry_count,
            fallback_used=fallback_used,
            error_message=msg,
        )

    jobs_found = len(raw_jobs)
    run.jobs_found = jobs_found
    db.commit()

    # Schema anomaly checks
    schema_anomaly_detected = False
    schema_warning_msg = None
    historical_avg = get_historical_avg_jobs(db, target_source_name)

    if jobs_found == 0 and historical_avg > 0 and target_source_name != "mock_fallback":
        schema_anomaly_detected = True
        schema_warning_msg = "SCHEMA_WARNING: Endpoint returned 0 records (expected >0 based on history)"
        logger.warning("SCHEMA_ANOMALY_ZERO_RECORDS", extra={"source": target_source_name, "avg": historical_avg})
    elif jobs_found > 0 and historical_avg >= 10 and target_source_name != "mock_fallback":
        ratio = jobs_found / historical_avg
        if ratio < settings.min_expected_jobs_ratio:
            schema_anomaly_detected = True
            schema_warning_msg = f"SCHEMA_WARNING: Unusually large drop in jobs found ({jobs_found} vs avg {historical_avg:.1f})"
            logger.warning("SCHEMA_ANOMALY_RECORD_DROP", extra={"source": target_source_name, "found": jobs_found, "avg": historical_avg})

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
                extra={"run_id": run.id, "source": target_source_name, "error": str(e)[:200]},
            )
            continue

    existing_ids = _get_existing_external_ids(db, target_source_name, user_id=user_id)
    new_jobs: list[Job] = []
    skipped_duplicates = 0

    for job in valid_jobs:
        if job.external_id in existing_ids:
            skipped_duplicates += 1
            logger.info(
                "JOB_DUPLICATE",
                extra={"run_id": run.id, "source": target_source_name, "external_id": job.external_id},
            )
            continue
        db_job = Job(
            source=job.source,
            external_id=job.external_id,
            user_id=user_id,
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
                extra={"run_id": run.id, "source": target_source_name, "external_id": db_job.external_id},
            )

    inserted = len(new_jobs)
    skipped_total = skipped_duplicates + malformed

    # Status classification logic
    if schema_anomaly_detected:
        final_status = "PARTIAL" if inserted > 0 else "FAILED"
    elif malformed > 0 and inserted > 0:
        final_status = "PARTIAL"
    elif malformed > 0 and inserted == 0:
        final_status = "FAILED"
    elif inserted > 0:
        final_status = "SUCCESS"
    elif jobs_found == 0:
        logger.warning("INGESTION_EMPTY_RESPONSE", extra={"run_id": run.id, "source": target_source_name})
        final_status = "SUCCESS"
    elif skipped_duplicates > 0 and inserted == 0:
        final_status = "SUCCESS"
    else:
        final_status = "SUCCESS"

    duration = round(time.monotonic() - start_time, 3)
    error_msg = schema_warning_msg if schema_anomaly_detected else (None if final_status == "SUCCESS" else run.error_message)

    run.completed_at = _now()
    run.status = final_status
    run.jobs_inserted = inserted
    run.jobs_skipped = skipped_total
    run.parse_failures = malformed
    run.duplicate_count = skipped_duplicates
    run.duration_seconds = duration
    run.error_message = error_msg
    db.commit()
    db.refresh(run)

    # Update source health
    is_success = final_status in ("SUCCESS", "PARTIAL")
    update_source_health(
        db,
        source_name=target_source_name,
        success=is_success,
        http_status=fetch_result.status_code,
        latency=fetch_result.latency_seconds,
        error_msg=error_msg,
    )

    logger.info(
        "INGESTION_COMPLETED",
        extra={
            "run_id": run.id,
            "source": target_source_name,
            "status": final_status,
            "jobs_found": jobs_found,
            "jobs_inserted": inserted,
            "jobs_skipped": skipped_total,
            "malformed": malformed,
            "duration": duration,
        },
    )

    return IngestionResult(
        status=final_status,
        source=target_source_name,
        jobs_found=jobs_found,
        jobs_inserted=inserted,
        jobs_skipped=skipped_total,
        run_id=run.id,
        duration_seconds=duration,
        parse_failures=malformed,
        duplicate_count=skipped_duplicates,
        http_status=fetch_result.status_code,
        retry_count=fetch_result.retry_count,
        fallback_used=fallback_used,
        error_message=error_msg,
    )
