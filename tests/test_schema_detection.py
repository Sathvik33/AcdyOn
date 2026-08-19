import respx
from httpx import Response
from app.services.ingestion import run_ingestion
from app.db.models import IngestionRun
from datetime import datetime, timezone


@respx.mock
def test_schema_anomaly_zero_records_detection(db_session):
    # Seed historical successful runs for jobicy
    for _ in range(3):
        db_session.add(
            IngestionRun(
                source="jobicy",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                status="SUCCESS",
                jobs_found=50,
                jobs_inserted=50,
                jobs_skipped=0,
            )
        )
    db_session.commit()

    # Now mock an HTTP 200 with zero jobs returned
    respx.get("https://jobicy.com/api/v2/remote-jobs?count=50").mock(
        return_value=Response(200, json={"jobs": []})
    )

    result = run_ingestion(db_session, source_name="jobicy", allow_fallback=False)
    assert result.status in ("PARTIAL", "FAILED")
    assert result.jobs_found == 0
    assert "SCHEMA_WARNING" in result.error_message
