import pytest
from datetime import datetime

from app.sources.jobicy import JobicySource


def sample_job():
    return {
        "id": 12345,
        "jobTitle": "Backend Engineer",
        "companyName": "Acme Corp",
        "jobGeo": "USA",
        "jobType": ["Full-Time"],
        "jobDescription": "<p>Build things.</p>",
        "pubDate": "2026-08-18T10:00:00+00:00",
        "url": "https://jobicy.com/jobs/12345-backend-engineer",
    }


def test_parse_valid_response():
    source = JobicySource(count=1)
    import json
    body = json.dumps({"jobs": [sample_job()]})
    jobs = source.parse(body)
    assert len(jobs) == 1
    assert jobs[0]["id"] == 12345


def test_parse_missing_jobs_key():
    source = JobicySource(count=1)
    import json
    body = json.dumps({"count": 0})
    with pytest.raises(ValueError, match="Missing 'jobs' key"):
        source.parse(body)


def test_parse_malformed_json():
    source = JobicySource(count=1)
    with pytest.raises(ValueError, match="Invalid JSON"):
        source.parse("not json")


def test_normalize_job():
    source = JobicySource(count=1)
    job = source.normalize(sample_job())
    assert job.source == "jobicy"
    assert job.external_id == "12345"
    assert job.title == "Backend Engineer"
    assert job.company == "Acme Corp"
    assert job.location == "USA"
    assert job.employment_type == "Full-Time"
    assert isinstance(job.published_at, datetime)
    assert job.raw_data_hash is not None


def test_normalize_job_without_id():
    source = JobicySource(count=1)
    raw = sample_job()
    raw.pop("id")
    raw["jobSlug"] = "12345-backend-engineer"
    job = source.normalize(raw)
    assert job.external_id == "12345-backend-engineer"


def test_normalize_invalid_record():
    source = JobicySource(count=1)
    with pytest.raises(ValueError):
        source.normalize({"title": "no id"})
