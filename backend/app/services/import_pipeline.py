from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.importers.arcs_fvg import run_arcs_fvg_import
from app.importers.asdaa_alto_adige import run_asdaa_alto_adige_import
from app.importers.asl_piemonte import run_asl_piemonte_import
from app.importers.asl_roma2 import run_asl_roma2_import
from app.importers.ast_marche import run_ast_marche_import
from app.importers.asuit_trentino import run_asuit_trentino_import
from app.importers.ats_liguria import run_ats_liguria_import
from app.importers.ausl_romagna import run_ausl_romagna_import
from app.importers.azienda_zero import run_azienda_zero_import
from app.importers.azienda_zero_piemonte import run_azienda_zero_piemonte_import
from app.importers.base import ImportResult
from app.importers.catalog_sources import run_catalog_sources_import
from app.importers.comune_venezia import run_comune_venezia_import
from app.importers.deep_html_sources import run_deep_html_sources_import
from app.importers.inail import run_inail_import
from app.importers.inpa import run_inpa_import
from app.importers.inps import run_inps_import
from app.importers.myportal_veneto import run_myportal_treviso_import
from app.importers.puglia_aol import run_puglia_aol_import
from app.importers.target_health_html import run_target_health_html_import
from app.importers.usl_umbria1 import run_usl_umbria1_import
from app.importers.usl_umbria2 import run_usl_umbria2_import

Importer = Callable[[Session], ImportResult]

INSTITUTIONAL_IMPORTERS: list[tuple[str, Importer]] = [
    ("Azienda Zero Veneto", run_azienda_zero_import),
    ("Azienda Zero Piemonte", run_azienda_zero_piemonte_import),
    ("ARCS FVG", run_arcs_fvg_import),
    ("ASUIT Trentino", run_asuit_trentino_import),
    ("ASDAA Alto Adige", run_asdaa_alto_adige_import),
    ("AUSL Romagna", run_ausl_romagna_import),
    ("USL Umbria 2", run_usl_umbria2_import),
    ("ASL Roma 2", run_asl_roma2_import),
    ("Comune di Venezia", run_comune_venezia_import),
    ("MyPortal Comune di Treviso", run_myportal_treviso_import),
    ("INAIL", run_inail_import),
    ("INPS", run_inps_import),
]

PUBLIC_REFRESH_IMPORTERS: list[tuple[str, Importer]] = [
    *INSTITUTIONAL_IMPORTERS,
    ("ASL Piemonte", run_asl_piemonte_import),
    ("AST Marche", run_ast_marche_import),
    ("ATS Liguria", run_ats_liguria_import),
    ("USL Umbria 1", run_usl_umbria1_import),
    ("PugliaSalute Albo Online", run_puglia_aol_import),
    ("Fonti sanitarie e sociali regionali", run_target_health_html_import),
    ("PAT e ospedali - adapter profondi", run_deep_html_sources_import),
    ("Fonti catalogate", run_catalog_sources_import),
]


@dataclass(frozen=True)
class SourceImportSummary:
    label: str
    status: str
    source_id: str | None = None
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error: str | None = None


def _summary(label: str, result: ImportResult) -> SourceImportSummary:
    return SourceImportSummary(
        label=label,
        status="success",
        source_id=result.source_id,
        created_count=result.created_count,
        updated_count=result.updated_count,
        skipped_count=result.skipped_count,
    )


def run_active_source_imports(
    db: Session,
    *,
    remove_demo: bool = True,
) -> list[SourceImportSummary]:
    summaries: list[SourceImportSummary] = []
    try:
        summaries.append(_summary("inPA", run_inpa_import(db, remove_demo=remove_demo)))
    except Exception as exc:
        summaries.append(SourceImportSummary(label="inPA", status="failed", error=str(exc)))

    for label, importer in PUBLIC_REFRESH_IMPORTERS:
        try:
            summaries.append(_summary(label, importer(db)))
        except Exception as exc:
            summaries.append(SourceImportSummary(label=label, status="failed", error=str(exc)))
    return summaries
