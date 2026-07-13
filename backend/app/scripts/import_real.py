from __future__ import annotations

import argparse

from app.db.session import SessionLocal, engine
from app.importers.base import ImportResult
from app.importers.inpa import run_inpa_import
from app.models import Base
from app.services.import_pipeline import INSTITUTIONAL_IMPORTERS
from app.services.source_probe import probe_source_catalog


def _print_result(label: str, result: ImportResult) -> None:
    print(
        f"{label} import completed: "
        f"source={result.source_id}, created={result.created_count}, "
        f"updated={result.updated_count}, skipped={result.skipped_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa bandi reali da fonti ufficiali.")
    parser.add_argument(
        "--remove-demo",
        action="store_true",
        help="Rimuove la fonte demo dopo import.",
    )
    parser.add_argument(
        "--probe-local-sources",
        action="store_true",
        help="Verifica le fonti istituzionali catalogate.",
    )
    parser.add_argument(
        "--skip-institutional-sources",
        action="store_true",
        help="Esegue solo l'import inPA, senza gli adapter istituzionali attivi.",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = run_inpa_import(db, remove_demo=args.remove_demo)
        _print_result("inPA", result)

        if not args.skip_institutional_sources:
            for label, importer in INSTITUTIONAL_IMPORTERS:
                try:
                    _print_result(label, importer(db))
                except Exception as exc:
                    print(f"{label} import failed: {exc}")

        if args.probe_local_sources:
            for source in probe_source_catalog(db):
                print(f"source probe: {source.name} -> {source.status}")


if __name__ == "__main__":
    main()
