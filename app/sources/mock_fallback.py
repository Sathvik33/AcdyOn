import json
from datetime import datetime, timezone
from typing import Any

from app.schemas.job import JobCreate
from app.services.fetcher import FetchResult
from app.sources.base import BaseJobSource


class MockFallbackSource(BaseJobSource):
    name = "mock_fallback"

    def fetch(self) -> FetchResult:
        return FetchResult(
            ok=True,
            status_code=200,
            body=json.dumps({"jobs": [self._record(1), self._record(2)]}),
        )

    def parse(self, body: str) -> list[dict[str, Any]]:
        return json.loads(body).get("jobs", [])

    def normalize(self, raw: dict[str, Any]) -> JobCreate:
        return JobCreate(
            source=self.name,
            external_id=str(raw["id"]),
            title=raw["title"],
            company=raw["company"],
            location=raw["location"],
            description=raw["description"],
            url=raw["url"],
            employment_type=raw["employment_type"],
            published_at=raw["published_at"],
            raw_data_hash="mock_hash",
        )

    def _record(self, idx: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": f"mock-{idx}",
            "title": f"Mock Job {idx}",
            "company": "Mock Co",
            "location": "Remote",
            "description": "<p>Simulated fallback listing.</p>",
            "url": "https://example.com/jobs/mock",
            "employment_type": "Full-Time",
            "published_at": now,
        }
