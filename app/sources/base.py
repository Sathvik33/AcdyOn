from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from app.schemas.job import JobCreate
from app.services.fetcher import FetchResult


class BaseJobSource(ABC):
    name: str = "base"

    def __init__(self, count: Optional[int] = None):
        self.count = count

    @abstractmethod
    def fetch(self) -> FetchResult:
        raise NotImplementedError

    @abstractmethod
    def parse(self, body: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> JobCreate:
        raise NotImplementedError

    def records(self, body: str) -> Iterable[JobCreate]:
        for raw in self.parse(body):
            try:
                yield self.normalize(raw)
            except Exception:
                # Caller logs and counts malformed rows.
                raise
