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


class RemotiveSource(BaseJobSource):
    name = "remotive"

    def __init__(self, count: Optional[int] = None):
        self.count = count or 50
        self.url = f"https://remotive.com/api/remote-jobs?limit={self.count}"

    def fetch(self) -> FetchResult:
        logger.info("FETCH_STARTED", extra={"source": self.name, "url": self.url})
        result = fetch_url(self.url, pacing_key=self.name)
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
            raise ValueError("Missing 'jobs' key in Remotive response")

        if not isinstance(jobs, list):
            raise ValueError("'jobs' field must be a list")

        return jobs

    def _extract_id(self, raw: dict[str, Any]) -> str:
        job_id = raw.get("id")
        if job_id is not None:
            return str(job_id)
        slug = raw.get("slug")
        if slug is not None:
            return str(slug)
        raise ValueError("No stable id or slug found in Remotive record")

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                return None

    def _hash(self, raw: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:32]

    def normalize(self, raw: dict[str, Any]) -> JobCreate:
        if not isinstance(raw, dict):
            raise ValueError("Job record must be a dict")

        external_id = self._extract_id(raw)
        title = raw.get("title")
        company = raw.get("company_name") or raw.get("company")
        location = raw.get("candidate_required_location") or raw.get("location")
        description = raw.get("description")
        url = raw.get("url")
        employment_type = raw.get("job_type") or raw.get("employment_type")
        published_at = self._parse_datetime(raw.get("publication_date") or raw.get("published_at"))

        return JobCreate(
            source=self.name,
            external_id=external_id,
            title=str(title) if title else None,
            company=str(company) if company else None,
            location=str(location) if location else None,
            description=str(description) if description else None,
            url=str(url) if url else None,
            employment_type=str(employment_type) if employment_type else None,
            published_at=published_at,
            raw_data_hash=self._hash(raw),
        )
