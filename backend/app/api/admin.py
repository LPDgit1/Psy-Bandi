from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.public import _detail
from app.core.config import settings
from app.core.security import require_admin
from app.db.session import get_db
from app.importers.arcs_fvg import run_arcs_fvg_import
from app.importers.asdaa_alto_adige import run_asdaa_alto_adige_import
from app.importers.asl_roma2 import run_asl_roma2_import
from app.importers.asuit_trentino import run_asuit_trentino_import
from app.importers.azienda_zero import run_azienda_zero_import
from app.importers.azienda_zero_piemonte import run_azienda_zero_piemonte_import
from app.importers.comune_venezia import run_comune_venezia_import
from app.importers.inpa import remove_demo_source, run_inpa_import
from app.importers.myportal_veneto import run_myportal_treviso_import
from app.importers.sample_fixture import run_sample_import
from app.models import EditorialAction, ImportRun, Opportunity, Source
from app.schemas import (
    AdminLogin,
    ImportRunRead,
    OpportunityDetail,
    OpportunityPatch,
    SourceRead,
    TokenResponse,
)
from app.services.classifier import build_search_text, normalize_text
from app.services.source_probe import probe_source_catalog

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: AdminLogin) -> TokenResponse:
    if not all((
        settings.admin_email,
        settings.admin_password,
        settings.admin_api_token,
    )):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is not configured",
        )
    if payload.email != settings.admin_email or payload.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=settings.admin_api_token)


@router.get("/opportunities", response_model=list[OpportunityDetail])
def list_admin_opportunities(
    editorial_status: str | None = None,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[OpportunityDetail]:
    statement = select(Opportunity)
    if editorial_status:
        statement = statement.where(Opportunity.editorial_status == editorial_status)
    items = db.scalars(statement).all()
    return [_detail(item) for item in items]


def _audit(
    db: Session,
    opportunity_id: str,
    action_type: str,
    field_name: str | None = None,
    previous_value: object | None = None,
    new_value: object | None = None,
) -> None:
    db.add(
        EditorialAction(
            admin_user=settings.admin_email,
            opportunity_id=opportunity_id,
            action_type=action_type,
            field_name=field_name,
            previous_value=None if previous_value is None else str(previous_value),
            new_value=None if new_value is None else str(new_value),
        )
    )


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
def update_opportunity(
    opportunity_id: str,
    payload: OpportunityPatch,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OpportunityDetail:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, new_value in updates.items():
        previous_value = getattr(opportunity, field_name)
        setattr(opportunity, field_name, new_value)
        _audit(db, opportunity_id, "update", field_name, previous_value, new_value)

    if "title" in updates:
        opportunity.normalized_title = normalize_text(opportunity.title)

    opportunity.search_text = build_search_text(
        opportunity.title,
        opportunity.description,
        opportunity.summary,
        opportunity.organization,
        opportunity.region,
        opportunity.province,
        opportunity.category,
        opportunity.areas,
        opportunity.requirements,
    )

    db.commit()
    db.refresh(opportunity)
    return _detail(opportunity)


@router.post("/opportunities/{opportunity_id}/approve", response_model=OpportunityDetail)
def approve_opportunity(
    opportunity_id: str,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OpportunityDetail:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    previous = opportunity.editorial_status
    opportunity.editorial_status = "approved"
    _audit(db, opportunity_id, "approve", "editorial_status", previous, "approved")
    db.commit()
    db.refresh(opportunity)
    return _detail(opportunity)


@router.post("/opportunities/{opportunity_id}/hide", response_model=OpportunityDetail)
def hide_opportunity(
    opportunity_id: str,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OpportunityDetail:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    previous = opportunity.editorial_status
    opportunity.editorial_status = "hidden"
    _audit(db, opportunity_id, "hide", "editorial_status", previous, "hidden")
    db.commit()
    db.refresh(opportunity)
    return _detail(opportunity)


@router.post("/opportunities/{opportunity_id}/feature", response_model=OpportunityDetail)
def feature_opportunity(
    opportunity_id: str,
    featured: bool = True,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OpportunityDetail:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    previous = opportunity.is_featured
    opportunity.is_featured = featured
    _audit(db, opportunity_id, "feature", "is_featured", previous, featured)
    db.commit()
    db.refresh(opportunity)
    return _detail(opportunity)


@router.get("/sources", response_model=list[SourceRead])
def list_sources(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[SourceRead]:
    return list(db.scalars(select(Source)).all())


@router.post("/sources/demo/run-import")
def run_demo_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_sample_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.delete("/sources/demo")
def delete_demo_source(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    deleted_count = remove_demo_source(db)
    db.commit()
    return {"deleted_count": deleted_count}


@router.post("/sources/inpa/run-import")
def run_real_inpa_import(
    remove_demo: bool = True,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_inpa_import(db, remove_demo=remove_demo)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/azienda-zero/run-import")
def run_real_azienda_zero_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_azienda_zero_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/asl-roma2/run-import")
def run_real_asl_roma2_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_asl_roma2_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/azienda-zero-piemonte/run-import")
def run_real_azienda_zero_piemonte_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_azienda_zero_piemonte_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/arcs-fvg/run-import")
def run_real_arcs_fvg_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_arcs_fvg_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/asuit-trentino/run-import")
def run_real_asuit_trentino_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_asuit_trentino_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/asdaa-alto-adige/run-import")
def run_real_asdaa_alto_adige_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_asdaa_alto_adige_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/comune-venezia/run-import")
def run_real_comune_venezia_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_comune_venezia_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/myportal-treviso/run-import")
def run_real_myportal_treviso_import(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    result = run_myportal_treviso_import(db)
    return {
        "source_id": result.source_id,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


@router.post("/sources/probe", response_model=list[SourceRead])
def probe_sources(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[SourceRead]:
    return probe_source_catalog(db)


@router.get("/import-runs", response_model=list[ImportRunRead])
def list_import_runs(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ImportRunRead]:
    return list(db.scalars(select(ImportRun).order_by(ImportRun.started_at.desc())).all())
