import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = (
    "AcdyonJobIngestion/0.1 "
    "(engineering-challenge; respectful-batch; "
    "https://github.com/acdyon/job-ingestion)"
)


@dataclass
class FetchResult:
    ok: bool
    status_code: int
    body: Optional[str]
    error: Optional[str] = None
    rate_limited: bool = False
    access_denied: bool = False


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


def fetch_url(
    url: str,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
) -> FetchResult:
    timeout = timeout or settings.http_timeout
    max_retries = max_retries if max_retries is not None else settings.http_max_retries
    retry_delay = retry_delay or settings.http_retry_delay

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
                response = client.get(url)
                status = response.status_code
                group = _status_code_group(status)

                if status == 429:
                    logger.warning("FETCH_RATE_LIMITED", extra={"url": url, "status": status})
                    return FetchResult(
                        ok=False,
                        status_code=status,
                        body=response.text,
                        rate_limited=True,
                        error="Rate limited by source",
                    )

                if group == "access_denied":
                    logger.warning("FETCH_ACCESS_DENIED", extra={"url": url, "status": status})
                    return FetchResult(
                        ok=False,
                        status_code=status,
                        body=response.text,
                        access_denied=True,
                        error=f"Access denied ({status})",
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
                    )

                if group == "client_error":
                    logger.warning("FETCH_CLIENT_ERROR", extra={"url": url, "status": status})
                    return FetchResult(
                        ok=False,
                        status_code=status,
                        body=response.text,
                        error=f"Client error ({status})",
                    )

                if status == 200:
                    return FetchResult(
                        ok=True,
                        status_code=status,
                        body=response.text,
                    )

                return FetchResult(
                    ok=False,
                    status_code=status,
                    body=response.text,
                    error=f"Unexpected status {status}",
                )

        except httpx.TimeoutException as e:
            last_error = f"Timeout: {e}"
            logger.warning("FETCH_TIMEOUT", extra={"url": url, "attempt": attempt + 1})
            if attempt < max_retries:
                sleep_seconds = retry_delay * (2 ** attempt)
                logger.info("FETCH_RETRY_BACKOFF", extra={"sleep": sleep_seconds})
                time.sleep(sleep_seconds)
                continue
            return FetchResult(ok=False, status_code=0, body=None, error=last_error)

        except httpx.NetworkError as e:
            last_error = f"Network error: {e}"
            logger.warning("FETCH_NETWORK_ERROR", extra={"url": url, "attempt": attempt + 1})
            if attempt < max_retries:
                sleep_seconds = retry_delay * (2 ** attempt)
                logger.info("FETCH_RETRY_BACKOFF", extra={"sleep": sleep_seconds})
                time.sleep(sleep_seconds)
                continue
            return FetchResult(ok=False, status_code=0, body=None, error=last_error)

        except Exception as e:
            logger.exception("FETCH_UNEXPECTED_ERROR", extra={"url": url})
            return FetchResult(ok=False, status_code=0, body=None, error=f"Unexpected error: {e}")

    return FetchResult(ok=False, status_code=0, body=None, error=last_error or "Fetch failed")
