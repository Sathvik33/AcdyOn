import time
import respx
from httpx import Response
from app.services.fetcher import fetch_url, _parse_retry_after, enforce_pacing


def test_parse_retry_after_seconds():
    assert _parse_retry_after("120") == 120.0
    assert _parse_retry_after(" 5 ") == 5.0
    assert _parse_retry_after(None) is None


@respx.mock
def test_fetch_url_records_retry_after_and_latency():
    url = "https://jobicy.com/api/v2/remote-jobs?count=50"
    respx.get(url).mock(
        return_value=Response(429, text="Rate Limited", headers={"Retry-After": "30"})
    )

    result = fetch_url(url, max_retries=0)
    assert result.ok is False
    assert result.rate_limited is True
    assert result.status_code == 429
    assert result.retry_after == 30.0
    assert result.latency_seconds >= 0.0


def test_enforce_pacing_delays_execution():
    key = "test_pacing_host"
    start = time.monotonic()
    enforce_pacing(key=key, min_interval=0.05)
    enforce_pacing(key=key, min_interval=0.05)
    elapsed = time.monotonic() - start
    assert elapsed >= 0.04
