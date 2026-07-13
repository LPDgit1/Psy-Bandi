from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import (
    AlertSubscription,
    Attachment,
    Base,
    EditorialAction,
    EmailLog,
    ImportRun,
    Opportunity,
    Source,
)
from app.services.public_snapshot import (
    PUBLIC_TABLE_NAMES,
    export_public_snapshot,
    publish_snapshot,
    validate_public_snapshot,
)
from app.services.static_catalog import StaticCatalog


def _source_session(path: Path) -> tuple[Session, object]:
    engine = create_engine(f"sqlite+pysqlite:///{path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    return Session(engine), engine


def _opportunity(
    *,
    opportunity_id: str,
    source: Source,
    editorial_status: str = "approved",
) -> Opportunity:
    return Opportunity(
        id=opportunity_id,
        source=source,
        title="Concorso pubblico per psicologo",
        normalized_title="concorso pubblico per psicologo",
        summary="Selezione pubblica per professionisti della psicologia.",
        category="concorso-pubblico",
        areas=["psicologia-clinica"],
        psychology_relevance="alta",
        relevance_score=95,
        organization="Azienda sanitaria pubblica",
        entity_type="azienda-sanitaria",
        region="Lazio",
        province="RM",
        status="open",
        deadline=datetime(2099, 12, 31, tzinfo=UTC),
        requirements=["iscrizione-albo"],
        official_url=f"https://ente.example.org/bandi/{opportunity_id}",
        search_text="concorso pubblico psicologo psicologia clinica",
        editorial_status=editorial_status,
        editorial_notes="NOTA_REDAZIONALE_PRIVATA",
        content_hash="HASH_INTERNO_PRIVATO",
    )


def test_snapshot_exports_only_approved_sanitized_public_data(tmp_path: Path) -> None:
    session, engine = _source_session(tmp_path / "source.sqlite")
    real_source = Source(
        id="src_real",
        name="Fonte istituzionale",
        source_type="json",
        base_url="https://ente.example.org/bandi",
        last_error="ERRORE_TECNICO_PRIVATO",
        technical_notes="NOTA_TECNICA_PRIVATA",
    )
    demo_source = Source(
        id="src_demo",
        name="Fonte demo",
        source_type="fixture",
        base_url="https://demo.example.test",
    )
    approved = _opportunity(opportunity_id="opp_public", source=real_source)
    approved.attachments.append(
        Attachment(
            id="att_public",
            title="Testo ufficiale",
            url="https://ente.example.org/allegato.pdf",
            extracted_text="TESTO_ESTRATTO_NON_DA_PUBBLICARE",
            content_hash="HASH_ALLEGATO_PRIVATO",
        )
    )
    session.add_all(
        [
            approved,
            _opportunity(
                opportunity_id="opp_pending",
                source=real_source,
                editorial_status="pending",
            ),
            _opportunity(opportunity_id="opp_demo", source=demo_source),
            AlertSubscription(
                email="persona-privata@example.org",
                confirm_token="TOKEN_CONFERMA_PRIVATO",
            ),
            EmailLog(
                recipient="persona-privata@example.org",
                subject="OGGETTO_EMAIL_PRIVATO",
                body_text="CORPO_EMAIL_PRIVATO",
            ),
            EditorialAction(
                admin_user="AMMINISTRATORE_PRIVATO",
                opportunity_id="opp_public",
                action_type="approve",
            ),
            ImportRun(
                source_id="src_real",
                status="failed",
                error_message="LOG_IMPORT_PRIVATO",
            ),
        ]
    )
    session.commit()

    destination = tmp_path / "public.sqlite"
    report = export_public_snapshot(session, destination)
    session.close()
    engine.dispose()

    assert report.opportunity_count == 1
    assert report.source_count == 1
    assert report.attachment_count == 1
    assert validate_public_snapshot(destination) == report

    with sqlite3.connect(destination) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
            if not row[0].startswith("sqlite_")
        }
        assert tables == PUBLIC_TABLE_NAMES
        assert connection.execute(
            "SELECT last_error, technical_notes FROM sources"
        ).fetchone() == (None, None)
        assert connection.execute(
            "SELECT editorial_notes, content_hash FROM opportunities"
        ).fetchone() == (None, None)
        assert connection.execute(
            "SELECT extracted_text, content_hash, indexed_at FROM attachments"
        ).fetchone() == (None, None, None)

    snapshot_bytes = destination.read_bytes()
    for private_marker in (
        b"persona-privata@example.org",
        b"TOKEN_CONFERMA_PRIVATO",
        b"NOTA_REDAZIONALE_PRIVATA",
        b"ERRORE_TECNICO_PRIVATO",
        b"CORPO_EMAIL_PRIVATO",
        b"LOG_IMPORT_PRIVATO",
        b"TESTO_ESTRATTO_NON_DA_PUBBLICARE",
    ):
        assert private_marker not in snapshot_bytes


def test_static_catalog_searches_and_cannot_write(tmp_path: Path) -> None:
    session, engine = _source_session(tmp_path / "source.sqlite")
    source = Source(
        id="src_real",
        name="Fonte istituzionale",
        source_type="json",
        base_url="https://ente.example.org/bandi",
    )
    opportunity = _opportunity(opportunity_id="opp_public", source=source)
    opportunity.attachments.append(
        Attachment(
            id="att_public",
            title="Bando",
            url="https://ente.example.org/bando.pdf",
        )
    )
    session.add(opportunity)
    session.commit()
    destination = tmp_path / "public.sqlite"
    export_public_snapshot(session, destination)
    session.close()
    engine.dispose()

    catalog = StaticCatalog(destination)
    response = catalog.search(q="psicologo", region="Lazio")
    assert response.total == 1
    assert response.items[0].id == "opp_public"
    assert catalog.facets().regions[0].value == "Lazio"
    detail = catalog.detail("opp_public")
    assert detail is not None
    assert detail.attachments[0].title == "Bando"

    with pytest.raises(OperationalError, match="readonly"):
        with catalog.engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO snapshot_metadata (key, value) VALUES ('write', 'blocked')"
            )
    catalog.close()


def test_unchanged_public_content_does_not_replace_snapshot(tmp_path: Path) -> None:
    session, engine = _source_session(tmp_path / "source.sqlite")
    source = Source(
        id="src_real",
        name="Fonte istituzionale",
        source_type="json",
        base_url="https://ente.example.org/bandi",
    )
    session.add(_opportunity(opportunity_id="opp_public", source=source))
    session.commit()

    destination = tmp_path / "public.sqlite"
    candidate = tmp_path / "candidate.sqlite"
    first_report = export_public_snapshot(
        session,
        destination,
        generated_at=datetime(2026, 7, 13, 10, 0, tzinfo=UTC),
    )
    export_public_snapshot(
        session,
        candidate,
        generated_at=datetime(2026, 7, 13, 18, 0, tzinfo=UTC),
    )
    published_report, changed = publish_snapshot(candidate, destination)

    assert changed is False
    assert published_report.generated_at == first_report.generated_at
    assert candidate.exists()
    session.close()
    engine.dispose()
