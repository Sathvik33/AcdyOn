import json

import httpx
import respx
from sqlalchemy.orm import Session

from app.db.models import Job, IngestionRun
from app.services.ingestion import run_ingestion


def sample_jobicy_response():
    return {
        "jobCount": 2,
        "jobs": [
            {
                "id": 111,
                "jobTitle": "Python Engineer",
                "companyName": "Co A",
                "jobGeo": "Remote",
                "jobType": ["Full-Time"],
                "jobDescription": "<p>Code.</p>",
                "pubDate": "2026-08-18T10:00:00+00:00",
                "url": "https://jobicy.com/jobs/111",
            },
            {
                "id": 222,
                "jobTitle": "Data Engineer",
                "companyName": "Co B",
                "jobGeo": "USA",
                "jobType": ["Contract"],
                "jobDescription": "<p>Data.</p>",
                "pubDate": "2026-08-18T11:00:00+00:00",
                "url": "https://jobicy.com/jobs/222",
            },
        ],
    }


@respx.mock
def test_successful_ingestion(respx_mock, db_session: Session):
    respx_mock.get("https://jobicy.com/api/v2/remote-jobs?count=50").mock(
        return_value=httpx.Response(200, text=json.dumps(sample_jobicy_response()))
    )
    result = run_ingestion(db_session, source_name="jobicy")
    assert result.status == "SUCCESS"
    assert result.jobs_found == 2
    assert result.jobs_inserted == 2
    assert result.jobs_skipped == 0
    assert db_session.query(Job).count() == 2


@respx.mock
def test_duplicate_detection(respx_mock, db_session: Session):
    respx_mock.get("https://jobicy.com/api/v2/remote-jobs?count=50").mock(
        return_value=httpx.Response(200, text=json.dumps(sample_jobicy_response()))
    )
    run_ingestion(db_session, source_name="jobicy")
    result = run_ingestion(db_session, source_name="jobicy")
    assert result.status == "SUCCESS"
    assert result.jobs_inserted == 0
    assert result.jobs_skipped == 2
    assert db_session.query(Job).count() == 2


@respx.mock
def test_partial_ingestion(respx_mock, db_session: Session):
    payload = sample_jobicy_response()
    payload["jobs"].append({"id": 333, "jobTitle": "Bad"})  # missing company ok, but keep valid
    payload["jobs"].append({"broken": "no id"})  # malformed
    respx_mock.get("https://jobicy.com/api/v2/remote-jobs?count=50").mock(
        return_value=httpx.Response(200, text=json.dumps(payload))
    )
    result = run_ingestion(db_session, source_name="jobicy")
    assert result.status == "PARTIAL"
    assert result.jobs_found == 4
    assert result.jobs_inserted == 3
    assert result.jobs_skipped == 1


@respx.mock
def test_failed_ingestion_on_rate_limit(respx_mock, db_session: Session):
    respx_mock.get("https://jobicy.com/api/v2/remote-jobs?count=50").mock(
        return_value=httpx.Response(429, text="rate limit")
    )
    result = run_ingestion(db_session, source_name="jobicy")
    assert result.status == "RATE_LIMITED"
    assert result.jobs_found == 0


@respx.mock
def test_failed_ingestion_on_500(respx_mock, db_session: Session):
    respx_mock.get("https://jobicy.com/api/v2/remote-jobs?count=50").mock(
        return_value=httpx.Response(500, text="err")
    )
    result = run_ingestion(db_session, source_name="jobicy")
    assert result.status == "FAILED"
    assert result.jobs_found == 0


def test_failed_ingestion_unknown_source(db_session: Session):
    result = run_ingestion(db_session, source_name="unknown")
    assert result.status == "FAILED"
    assert "Unknown source" in result.error_message


def test_database_insertion(db_session: Session):
    job = Job(
        source="jobicy",
        external_id="999",
        title="Test Job",
        company="Test Co",
        location="Remote",
        description="<p>Desc</p>",
        url="https://example.com/999",
        employment_type="Full-Time",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    assert job.id is not None
    assert db_session.query(Job).filter(Job.external_id == "999").first() is not None
