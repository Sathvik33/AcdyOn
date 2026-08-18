import httpx
import pytest
import respx

from app.services.fetcher import fetch_url
from app.core.config import settings


@respx.mock
def test_fetch_success(respx_mock):
    route = respx_mock.get("https://example.com/jobs").mock(return_value=httpx.Response(200, json={"jobs": []}))
    result = fetch_url("https://example.com/jobs")
    assert result.ok is True
    assert result.status_code == 200


@respx.mock
def test_fetch_timeout(respx_mock):
    route = respx_mock.get("https://example.com/jobs").mock(side_effect=httpx.TimeoutException("timed out"))
    result = fetch_url("https://example.com/jobs", timeout=1.0, max_retries=1, retry_delay=0.01)
    assert result.ok is False
    assert "Timeout" in result.error


@respx.mock
def test_fetch_429(respx_mock):
    route = respx_mock.get("https://example.com/jobs").mock(return_value=httpx.Response(429, text="rate limited"))
    result = fetch_url("https://example.com/jobs")
    assert result.ok is False
    assert result.status_code == 429
    assert result.rate_limited is True


@respx.mock
def test_fetch_403(respx_mock):
    route = respx_mock.get("https://example.com/jobs").mock(return_value=httpx.Response(403, text="forbidden"))
    result = fetch_url("https://example.com/jobs")
    assert result.ok is False
    assert result.status_code == 403
    assert result.access_denied is True


@respx.mock
def test_fetch_500_retry(respx_mock):
    route = respx_mock.get("https://example.com/jobs").mock(
        side_effect=[httpx.Response(500, text="err"), httpx.Response(500, text="err"), httpx.Response(200, json={"ok": True})]
    )
    result = fetch_url("https://example.com/jobs", max_retries=2, retry_delay=0.01)
    assert result.ok is True


@respx.mock
def test_fetch_500_fail(respx_mock):
    route = respx_mock.get("https://example.com/jobs").mock(return_value=httpx.Response(500, text="err"))
    result = fetch_url("https://example.com/jobs", max_retries=1, retry_delay=0.01)
    assert result.ok is False
    assert result.status_code == 500


@respx.mock
def test_fetch_empty_body(respx_mock):
    route = respx_mock.get("https://example.com/jobs").mock(return_value=httpx.Response(200, text=""))
    result = fetch_url("https://example.com/jobs")
    assert result.ok is True
    assert result.body == ""
