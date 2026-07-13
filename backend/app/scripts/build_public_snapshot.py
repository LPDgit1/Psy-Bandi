from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import Base, Opportunity
from app.services.deadline_status import refresh_deadline_statuses
from app.services.import_pipeline import run_active_source_imports
from app.services.public_snapshot import (
    SnapshotValidationError,
    export_public_snapshot,
    publish_snapshot,
    validate_public_snapshot,
)
from app.services.source_probe import ensure_source_catalog

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "data" / "bandi.sqlite"


def _sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.resolve().as_posix()}"


def build_snapshot(output: Path) -> bool:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix="bandi-snapshot-", dir=output.parent) as temp_dir:
        temp_root = Path(temp_dir)
        working_database = temp_root / "working.sqlite"
        candidate = temp_root / "candidate.sqlite"

        if output.exists():
            validate_public_snapshot(output)
            shutil.copy2(output, working_database)

        engine = create_engine(_sqlite_url(working_database))
        Base.metadata.create_all(bind=engine)
        with Session(engine) as session:
            ensure_source_catalog(session)
            summaries = run_active_source_imports(session, remove_demo=True)
            refresh_deadline_statuses(session)
            approved_count = session.scalar(
                select(func.count()).select_from(Opportunity).where(
                    Opportunity.editorial_status == "approved"
                )
            ) or 0
            successful = [summary for summary in summaries if summary.status == "success"]
            failed = [summary for summary in summaries if summary.status == "failed"]
            if not successful and not approved_count:
                raise RuntimeError(
                    "Nessuna fonte e stata aggiornata e non esiste uno snapshot precedente"
                )
            export_public_snapshot(session, candidate)
        engine.dispose()

        report, changed = publish_snapshot(candidate, output)
        print(
            f"Snapshot {'pubblicato' if changed else 'invariato'}: "
            f"{report.opportunity_count} opportunita, "
            f"{report.source_count} fonti, {report.attachment_count} allegati."
        )
        print(
            f"Import completati: {len(successful)}; "
            f"fonti non disponibili: {len(failed)}."
        )
        if failed:
            print("Da ricontrollare: " + ", ".join(item.label for item in failed))
        return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggiorna e pubblica lo snapshot SQLite per Streamlit."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        build_snapshot(args.output)
    except SnapshotValidationError as exc:
        raise SystemExit(f"Snapshot non valido: {exc}") from exc


if __name__ == "__main__":
    main()
