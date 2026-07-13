from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from app.api.public import (
    _build_contextual_facets,
    _build_facets,
    _detail,
    _filter_items,
    _list_item,
    _sort_items,
)
from app.models import Opportunity
from app.schemas import Facets, OpportunityDetail, OpportunityListResponse
from app.services.public_snapshot import SnapshotReport, validate_public_snapshot


def _read_only_engine(path: Path) -> Engine:
    resolved = path.resolve()

    def connect() -> sqlite3.Connection:
        return sqlite3.connect(
            f"file:{resolved.as_posix()}?mode=ro&immutable=1",
            uri=True,
            check_same_thread=False,
        )

    return create_engine("sqlite+pysqlite://", creator=connect)


class StaticCatalog:
    """Read-only search facade for a validated public SQLite snapshot."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.snapshot: SnapshotReport = validate_public_snapshot(self.path)
        self.engine = _read_only_engine(self.path)

    def close(self) -> None:
        self.engine.dispose()

    def _items(self, *, relationships: bool = False) -> list[Opportunity]:
        statement: Any = select(Opportunity).where(
            Opportunity.editorial_status == "approved"
        )
        if relationships:
            statement = statement.options(
                selectinload(Opportunity.source),
                selectinload(Opportunity.attachments),
            )
        with Session(self.engine) as session:
            return list(session.scalars(statement).all())

    def facets(self) -> Facets:
        return _build_facets(self._items())

    def search(
        self,
        *,
        q: str | None = None,
        region: str | None = None,
        province: str | None = None,
        category: str | None = None,
        entity_type: str | None = None,
        area: str | None = None,
        status_filter: str | None = None,
        deadline: str | None = None,
        featured: bool | None = None,
        sort: str = "deadline",
        limit: int = 20,
        offset: int = 0,
    ) -> OpportunityListResponse:
        items = self._items(relationships=True)
        filtered = _filter_items(
            items,
            q=q,
            region=region,
            province=province,
            category=category,
            entity_type=entity_type,
            area=area,
            status_filter=status_filter,
            deadline=deadline,
            featured=featured,
        )
        sorted_items = _sort_items(filtered, sort)
        return OpportunityListResponse(
            items=[_list_item(item) for item in sorted_items[offset : offset + limit]],
            total=len(filtered),
            limit=limit,
            offset=offset,
            facets=_build_contextual_facets(
                items,
                q=q,
                region=region,
                province=province,
                selected_province=province,
                category=category,
                entity_type=entity_type,
                area=area,
                status_filter=status_filter,
                deadline=deadline,
                featured=featured,
            ),
        )

    def detail(self, opportunity_id: str) -> OpportunityDetail | None:
        statement = (
            select(Opportunity)
            .where(
                Opportunity.id == opportunity_id,
                Opportunity.editorial_status == "approved",
            )
            .options(
                selectinload(Opportunity.source),
                selectinload(Opportunity.attachments),
            )
        )
        with Session(self.engine) as session:
            opportunity = session.scalar(statement)
            return _detail(opportunity) if opportunity is not None else None
