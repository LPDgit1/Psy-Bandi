from __future__ import annotations

import os
from dataclasses import dataclass


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    app_name: str = "Bandi Psicologia API"
    app_env: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./bandi_dev.db")
    admin_email: str = os.getenv("ADMIN_EMAIL", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    admin_api_token: str = os.getenv("ADMIN_API_TOKEN", "")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:5173")
    public_api_base_url: str = os.getenv(
        "PUBLIC_API_BASE_URL",
        "http://localhost:8000/api/public",
    )
    cors_origins: list[str] = None  # type: ignore[assignment]
    seed_on_startup: bool = _bool_env("SEED_ON_STARTUP", False)
    inpa_import_on_startup: bool = _bool_env("INPA_IMPORT_ON_STARTUP", False)
    institutional_import_on_startup: bool = _bool_env("INSTITUTIONAL_IMPORT_ON_STARTUP", False)
    inpa_verify_tls: bool = _bool_env("INPA_VERIFY_TLS", True)
    source_import_verify_tls: bool = _bool_env("SOURCE_IMPORT_VERIFY_TLS", True)
    source_probe_verify_tls: bool = _bool_env("SOURCE_PROBE_VERIFY_TLS", True)
    remove_demo_on_startup: bool = _bool_env("REMOVE_DEMO_ON_STARTUP", False)
    inpa_search_terms: list[str] = None  # type: ignore[assignment]
    inpa_page_size: int = _int_env("INPA_PAGE_SIZE", 100)
    inpa_max_pages: int = _int_env("INPA_MAX_PAGES", 10)
    inpa_open_scan_enabled: bool = _bool_env("INPA_OPEN_SCAN_ENABLED", True)
    inpa_open_scan_max_pages: int = _int_env("INPA_OPEN_SCAN_MAX_PAGES", 50)
    inps_search_terms: list[str] = None  # type: ignore[assignment]
    inps_page_size: int = _int_env("INPS_PAGE_SIZE", 25)
    inps_max_pages: int = _int_env("INPS_MAX_PAGES", 3)
    inail_max_pages: int = _int_env("INAIL_MAX_PAGES", 3)
    azienda_zero_piemonte_max_pages: int = _int_env("AZIENDA_ZERO_PIEMONTE_MAX_PAGES", 8)
    asuit_max_pages: int = _int_env("ASUIT_MAX_PAGES", 8)
    ausl_romagna_max_pages: int = _int_env("AUSL_ROMAGNA_MAX_PAGES", 4)
    catalog_max_detail_links_per_source: int = _int_env(
        "CATALOG_MAX_DETAIL_LINKS_PER_SOURCE",
        4,
    )
    deep_adapter_max_links_per_source: int = _int_env(
        "DEEP_ADAPTER_MAX_LINKS_PER_SOURCE",
        24,
    )
    deep_adapter_budget_seconds: int = _int_env("DEEP_ADAPTER_BUDGET_SECONDS", 300)
    public_refresh_cooldown_seconds: int = _int_env("PUBLIC_REFRESH_COOLDOWN_SECONDS", 300)
    alert_scheduler_enabled: bool = _bool_env("ALERT_SCHEDULER_ENABLED", False)
    alert_scheduler_initial_delay_seconds: int = _int_env(
        "ALERT_SCHEDULER_INITIAL_DELAY_SECONDS",
        60,
    )
    alert_scheduler_interval_seconds: int = _int_env(
        "ALERT_SCHEDULER_INTERVAL_SECONDS",
        3600,
    )
    email_delivery_mode: str = os.getenv("EMAIL_DELIVERY_MODE", "file")
    email_from: str = os.getenv("EMAIL_FROM", "Bandi Psicologia <noreply@example.test>")
    email_outbox_dir: str = os.getenv("EMAIL_OUTBOX_DIR", "tmp/email_outbox")
    smtp_host: str | None = os.getenv("SMTP_HOST")
    smtp_port: int = _int_env("SMTP_PORT", 587)
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    smtp_use_tls: bool = _bool_env("SMTP_USE_TLS", True)

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            object.__setattr__(
                self,
                "cors_origins",
                _csv_env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"),
            )
        if self.inpa_search_terms is None:
            object.__setattr__(
                self,
                "inpa_search_terms",
                _csv_env(
                    "INPA_SEARCH_TERMS",
                    "psicolog,psicoterap,neuropsicolog,lm-51,albo psicologi,"
                    "psicodiagnostic,valutazione psicologica,test neuropsicologici,"
                    "riabilitazione cognitiva,psicopedagog,psicoeduc,psicosocial,"
                    "salute mentale",
                ),
            )
        if self.inps_search_terms is None:
            object.__setattr__(
                self,
                "inps_search_terms",
                _csv_env(
                    "INPS_SEARCH_TERMS",
                    "psicolog,psicoterap,neuropsicolog,lm-51,albo psicologi,"
                    "psicodiagnostic,valutazione psicologica,test neuropsicologici,"
                    "riabilitazione cognitiva,psicopedagog,psicoeduc,psicosocial,"
                    "salute mentale",
                ),
            )


settings = Settings()
