from __future__ import annotations

from app.db.session import SessionLocal, engine
from app.importers.sample_fixture import run_sample_import
from app.models import Base


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = run_sample_import(db)
        print(
            "Seed completed: "
            f"source={result.source_id}, created={result.created_count}, "
            f"updated={result.updated_count}, skipped={result.skipped_count}"
        )


if __name__ == "__main__":
    main()

