from app.sources.jobicy import JobicySource


def test_normalize_employment_type_list():
    source = JobicySource(count=1)
    raw = {"id": 1, "jobTitle": "T", "companyName": "C", "jobType": ["Full-Time", "Contract"]}
    job = source.normalize(raw)
    assert job.employment_type == "Full-Time, Contract"


def test_normalize_geo_list():
    source = JobicySource(count=1)
    raw = {"id": 1, "jobTitle": "T", "companyName": "C", "jobGeo": ["USA", "Canada"]}
    job = source.normalize(raw)
    assert job.location == "USA, Canada"


def test_normalize_date_fallback():
    source = JobicySource(count=1)
    raw = {"id": 1, "jobTitle": "T", "companyName": "C", "pubDate": "2026-08-18T10:00:00"}
    job = source.normalize(raw)
    assert job.published_at is not None
