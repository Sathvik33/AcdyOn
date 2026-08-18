import json

import httpx
import respx


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_jobs_empty(client):
    res = client.get("/jobs")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_jobs_pagination(client):
    # insert via direct API call
    res = client.post("/ingestion/run?count=0")
    assert res.status_code in (200, 422)


def test_ingestion_run_endpoint(client):
    res = client.post("/ingestion/run")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["source"] == "jobicy"


def test_get_job_not_found(client):
    res = client.get("/jobs/999999")
    assert res.status_code == 404


def test_ingestion_runs_endpoint(client):
    res = client.get("/ingestion/runs")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_stats_endpoint(client):
    res = client.get("/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_jobs" in data
