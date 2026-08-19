import logging
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = (
    "AcdyonJobIngestion/0.1 "
    "(engineering-challenge; respectful-batch; "
    "https://github.com/acdyon/job-ingestion)"
)

# Global in-memory timestamp store for pacing min request interval per host/domain
_last_request_time: dict[str, float] = {}


@dataclass
class FetchResult:
    ok: bool
    status_code: int
    body: Optional[str]
    error: Optional[str] = None
    rate_limited: bool = False
    access_denied: bool = False
    latency_seconds: float = 0.0
    retry_count: int = 0
    retry_after: Optional[float] = None


def _status_code_group(code: int) -> str:
    if code == 429:
        return "rate_limited"
    if code in (403, 401):
        return "access_denied"
    if code >= 500:
        return "server_error"
    if code >= 400:
        return "client_error"
    return "ok"


def _parse_retry_after(header_val: Optional[str]) -> Optional[float]:
    if not header_val:
        return None
    header_val = header_val.strip()
    try:
        return float(header_val)
    except ValueError:
        try:
            dt = parsedate_to_datetime(header_val)
            now = time.time()
            return max(0.0, dt.timestamp() - now)
        except Exception:
            return None


def enforce_pacing(key: str = "default", min_interval: Optional[float] = None) -> None:
    min_interval = min_interval if min_interval is not None else settings.http_min_request_interval
    if min_interval <= 0:
        return
    now = time.monotonic()
    last_time = _last_request_time.get(key, 0.0)
    elapsed = now - last_time
    if elapsed < min_interval:
        sleep_needed = min_interval - elapsed
        logger.info("FETCH_PACING_DELAY", extra={"key": key, "sleep_needed": sleep_needed})
        time.sleep(sleep_needed)
    _last_request_time[key] = time.monotonic()


def fetch_url(
    url: str,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    pacing_key: Optional[str] = None,
) -> FetchResult:
    timeout = timeout or settings.http_timeout
    max_retries = max_retries if max_retries is not None else settings.http_max_retries
    retry_delay = retry_delay or settings.http_retry_delay

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    # Respect safe request pacing before outbound call
    enforce_pacing(pacing_key or url)

    start_time = time.monotonic()
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
                response = client.get(url)
                status = response.status_code
                group = _status_code_group(status)
                latency = time.monotonic() - start_time

                if status == 429:
                    retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                    logger.warning(
                        "FETCH_RATE_LIMITED",
                        extra={"url": url, "status": status, "retry_after": retry_after},
                    )
                    return FetchResult(
                        ok=False,
                        status_code=status,
                        body=response.text,
                        rate_limited=True,
                        error="Rate limited by source",
                        latency_seconds=latency,
                        retry_count=attempt,
                        retry_after=retry_after,
                    )

                if group == "access_denied":
                    logger.warning("FETCH_ACCESS_DENIED", extra={"url": url, "status": status})
                    return FetchResult(
                        ok=False,
                        status_code=status,
                        body=response.text,
                        access_denied=True,
                        error=f"Access denied ({status})",
                        latency_seconds=latency,
                        retry_count=attempt,
                    )

                if group == "server_error":
                    logger.warning(
                        "FETCH_SERVER_ERROR",
                        extra={"url": url, "status": status, "attempt": attempt + 1},
                    )
                    if attempt < max_retries:
                        sleep_seconds = retry_delay * (2 ** attempt)
                        logger.info("FETCH_RETRY_BACKOFF", extra={"sleep": sleep_seconds})
                        time.sleep(sleep_seconds)
                        continue
                    return FetchResult(
                        ok=False,
                        status_code=status,
                        body=response.text,
                        error=f"Server error persisted after {max_retries} retries",
                        latency_seconds=latency,
                        retry_count=attempt,
                    )

                if group == "client_error":
                    logger.warning("FETCH_CLIENT_ERROR", extra={"url": url, "status": status})
                    return FetchResult(
                        ok=False,
                        status_code=status,
                        body=response.text,
                        error=f"Client error ({status})",
                        latency_seconds=latency,
                        retry_count=attempt,
                    )

                if status == 200:
                    return FetchResult(
                        ok=True,
                        status_code=status,
                        body=response.text,
                        latency_seconds=latency,
                        retry_count=attempt,
                    )

                return FetchResult(
                    ok=False,
                    status_code=status,
                    body=response.text,
                    error=f"Unexpected status {status}",
                    latency_seconds=latency,
                    retry_count=attempt,
                )

        except httpx.TimeoutException as e:
            last_error = f"Timeout: {e}"
            logger.warning("FETCH_TIMEOUT", extra={"url": url, "attempt": attempt + 1})
            if attempt < max_retries:
                sleep_seconds = retry_delay * (2 ** attempt)
                logger.info("FETCH_RETRY_BACKOFF", extra={"sleep": sleep_seconds})
                time.sleep(sleep_seconds)
                continue
            latency = time.monotonic() - start_time
            return FetchResult(
                ok=False,
                status_code=0,
                body=None,
                error=last_error,
                latency_seconds=latency,
                retry_count=attempt,
            )

        except httpx.NetworkError as e:
            last_error = f"Network error: {e}"
            logger.warning("FETCH_NETWORK_ERROR", extra={"url": url, "attempt": attempt + 1})
            if attempt < max_retries:
                sleep_seconds = retry_delay * (2 ** attempt)
                logger.info("FETCH_RETRY_BACKOFF", extra={"sleep": sleep_seconds})
                time.sleep(sleep_seconds)
                continue
            latency = time.monotonic() - start_time
            return FetchResult(
                ok=False,
                status_code=0,
                body=None,
                error=last_error,
                latency_seconds=latency,
                retry_count=attempt,
            )

        except Exception as e:
            logger.exception("FETCH_UNEXPECTED_ERROR", extra={"url": url})
            latency = time.monotonic() - start_time
            return FetchResult(
                ok=False,
                status_code=0,
                body=None,
                error=f"Unexpected error: {e}",
                latency_seconds=latency,
                retry_count=attempt,
            )

    latency = time.monotonic() - start_time
    return FetchResult(
        ok=False,
        status_code=0,
        body=None,
        error=last_error or "Fetch failed",
        latency_seconds=latency,
        retry_count=max_retries,
    )
