from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ImportResult:
    source_id: str | None
    created_count: int
    updated_count: int
    skipped_count: int


class SourceImporter(Protocol):
    source_name: str

    def run(self, db: Session) -> ImportResult:
        """Import or update opportunities from a source."""

