import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

from app.core.config import settings
from app.schemas.job import JobCreate
from app.services.fetcher import fetch_url, FetchResult
from app.sources.base import BaseJobSource

logger = logging.getLogger(__name__)


class JobicySource(BaseJobSource):
    name = "jobicy"

    def __init__(self, count: Optional[int] = None):
        self.count = count or settings.jobicy_default_count
        self.url = f"{settings.jobicy_api_url}?count={self.count}"

    def fetch(self) -> FetchResult:
        logger.info("FETCH_STARTED", extra={"source": self.name, "url": self.url})
        result = fetch_url(self.url)
        if result.ok:
            logger.info("FETCH_SUCCESS", extra={"source": self.name, "status": result.status_code})
        else:
            logger.warning(
                "FETCH_FAILED",
                extra={
                    "source": self.name,
                    "status": result.status_code,
                    "error": result.error,
                    "rate_limited": result.rate_limited,
                    "access_denied": result.access_denied,
                },
            )
        return result

    def parse(self, body: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Expected top-level JSON object")

        jobs = data.get("jobs")
        if jobs is None:
            raise ValueError("Missing 'jobs' key in response")

        if not isinstance(jobs, list):
            raise ValueError("'jobs' field must be a list")

        return jobs

    def _pick(self, raw: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in raw and raw[key] is not None:
                return raw[key]
        return None

    def _extract_id(self, raw: dict[str, Any]) -> str:
        job_id = raw.get("id")
        if job_id is not None:
            return str(job_id)
        job_slug = raw.get("jobSlug")
        if job_slug is not None:
            return str(job_slug)
        raise ValueError("No stable id or jobSlug found")

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            # ISO 8601 with timezone
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                return None

    def _geo(self, raw: dict[str, Any]) -> Optional[str]:
        geo = raw.get("jobGeo")
        if isinstance(geo, str):
            return geo.strip() or None
        if isinstance(geo, list):
            return ", ".join(str(g) for g in geo).strip() or None
        return None

    def _employment_type(self, raw: dict[str, Any]) -> Optional[str]:
        jt = raw.get("jobType")
        if isinstance(jt, list) and jt:
            return ", ".join(str(x) for x in jt)
        if isinstance(jt, str):
            return jt
        return None

    def _hash(self, raw: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:32]

    def normalize(self, raw: dict[str, Any]) -> JobCreate:
        if not isinstance(raw, dict):
            raise ValueError("Job record must be a dict")

        external_id = self._extract_id(raw)
        title = self._pick(raw, "jobTitle", "title")
        company = self._pick(raw, "companyName", "company")
        location = self._geo(raw)
        description = self._pick(raw, "jobDescription", "description")
        url = self._pick(raw, "url", "jobUrl")
        employment_type = self._employment_type(raw)
        published_at = self._parse_datetime(self._pick(raw, "pubDate", "publishedAt", "publication_date"))

        return JobCreate(
            source=self.name,
            external_id=external_id,
            title=str(title) if title else None,
            company=str(company) if company else None,
            location=location,
            description=str(description) if description else None,
            url=str(url) if url else None,
            employment_type=employment_type,
            published_at=published_at,
            raw_data_hash=self._hash(raw),
        )
