import respx
from httpx import Response
from app.services.ingestion import run_ingestion, get_or_create_source_health, check_circuit_breaker


@respx.mock
def test_source_health_transitions_on_429(db_session):
    respx.get("https://jobicy.com/api/v2/remote-jobs?count=50").mock(
        return_value=Response(429, text="Rate Limited", headers={"Retry-After": "10"})
    )

    result = run_ingestion(db_session, source_name="jobicy", allow_fallback=False)
    assert result.status == "RATE_LIMITED"
    assert result.http_status == 429

    health = get_or_create_source_health(db_session, "jobicy")
    assert health.health_state == "BLOCKED"
    assert health.last_http_status == 429


@respx.mock
def test_circuit_breaker_activates_fallback(db_session):
    # Set jobicy health state to BLOCKED in database
    health = get_or_create_source_health(db_session, "jobicy")
    health.health_state = "BLOCKED"
    db_session.commit()

    # Verify circuit breaker flags jobicy as blocked
    is_blocked, state = check_circuit_breaker(db_session, "jobicy")
    assert is_blocked is True
    assert state == "BLOCKED"

    # Trigger ingestion with allow_fallback=True (should use configured fallback 'remotive')
    respx.get("https://remotive.com/api/remote-jobs?limit=50").mock(
        return_value=Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "remotive-101",
                        "title": "Fallback Dev",
                        "company_name": "Fallback Inc",
                        "candidate_required_location": "Remote",
                        "description": "Fallback job description",
                        "url": "https://remotive.com/job/101",
                        "job_type": "full_time",
                        "publication_date": "2026-08-19T12:00:00",
                    }
                ]
            },
        )
    )

    result = run_ingestion(db_session, source_name="jobicy", allow_fallback=True)
    assert result.status == "SUCCESS"
    assert result.source == "remotive"
    assert result.fallback_used is True
    assert result.jobs_inserted == 1
