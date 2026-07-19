"""Study readiness checks for NeuroCortex pilot/production deployments."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


CRITICAL_CHECKS = {
    "postgresql_connection",
    "alembic_migration_status",
    "active_study_protocol",
    "active_consent_form_versions",
    "official_form4_template_exists",
    "official_form4_template_sha256",
}


def _print_result(result: CheckResult) -> None:
    print(f"[{result.status}] {result.name}: {result.detail}")


def main() -> int:
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, func, select, text

    from app.config import get_settings
    from app.models.consent_form_version import ConsentFormVersion
    from app.models.participant import Participant
    from app.models.participant_consent_event import ParticipantConsentEvent
    from app.models.study_protocol import StudyProtocol
    from app.services.consent_service import build_consent_status, resolve_active_protocol
    from app.services.pdf_form_service import (
        DOCUMENTS_DIR,
        TEMPLATE_PDF,
        compute_template_sha256,
        load_template_metadata,
    )
    from app.services.study_guard import get_study_config, get_synthetic_prefixes, is_synthetic_public_id
    from app.database import SessionLocal

    results: list[CheckResult] = []
    settings = get_settings()

    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        results.append(CheckResult("postgresql_connection", "PASS", "Database connection succeeded"))
    except Exception as exc:
        results.append(CheckResult("postgresql_connection", "FAIL", str(exc)))

    try:
        alembic_cfg = Config(str(ROOT / "alembic.ini"))
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current = context.get_current_revision()
        if current == head:
            results.append(CheckResult("alembic_migration_status", "PASS", f"At head revision {head}"))
        else:
            results.append(
                CheckResult(
                    "alembic_migration_status",
                    "FAIL",
                    f"Current revision {current!r}, expected head {head!r}",
                )
            )
    except Exception as exc:
        results.append(CheckResult("alembic_migration_status", "FAIL", str(exc)))

    db = SessionLocal()
    try:
        try:
            protocol = resolve_active_protocol(db)
            results.append(
                CheckResult(
                    "active_study_protocol",
                    "PASS",
                    f"Active protocol {protocol.version}",
                )
            )
        except Exception as exc:
            results.append(CheckResult("active_study_protocol", "FAIL", str(exc)))

        configured_version = settings.active_study_protocol_version.strip()
        configured = db.execute(
            select(StudyProtocol).where(StudyProtocol.version == configured_version)
        ).scalar_one_or_none()
        if configured is None:
            results.append(
                CheckResult(
                    "configured_protocol_present",
                    "WARNING",
                    f"Configured protocol {configured_version} not found",
                )
            )
        elif not configured.active:
            results.append(
                CheckResult(
                    "configured_protocol_active",
                    "FAIL",
                    f"Configured protocol {configured_version} is inactive",
                )
            )
        else:
            results.append(
                CheckResult(
                    "configured_protocol_active",
                    "PASS",
                    f"Configured protocol {configured_version} is active",
                )
            )

        try:
            protocol = resolve_active_protocol(db)
            forms = db.execute(
                select(ConsentFormVersion).where(
                    ConsentFormVersion.protocol_id == protocol.id,
                    ConsentFormVersion.active.is_(True),
                )
            ).scalars().all()
            required = {"participant_assent", "parental_permission", "adult_informed_consent"}
            present = {form.form_type for form in forms}
            missing = sorted(required - present)
            if missing:
                results.append(
                    CheckResult(
                        "active_consent_form_versions",
                        "FAIL",
                        f"Missing active form types: {', '.join(missing)}",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "active_consent_form_versions",
                        "PASS",
                        f"{len(forms)} active consent form versions for protocol {protocol.version}",
                    )
                )
        except Exception as exc:
            results.append(CheckResult("active_consent_form_versions", "FAIL", str(exc)))

        if TEMPLATE_PDF.exists():
            results.append(CheckResult("official_form4_template_exists", "PASS", str(TEMPLATE_PDF)))
        else:
            results.append(CheckResult("official_form4_template_exists", "FAIL", "Official Form 4 template missing"))

        if TEMPLATE_PDF.exists():
            metadata = load_template_metadata()
            actual = compute_template_sha256().lower()
            expected = metadata.get("sha256", "").lower()
            if actual == expected:
                results.append(
                    CheckResult(
                        "official_form4_template_sha256",
                        "PASS",
                        f"SHA-256 matches metadata ({actual[:12]}...)",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        "official_form4_template_sha256",
                        "FAIL",
                        f"Expected {expected}, got {actual}",
                    )
                )

        study_config = get_study_config()
        results.append(
            CheckResult(
                "study_mode_configuration",
                "PASS",
                f"study_mode={study_config['study_mode']}, require_consent={settings.require_consent_for_sessions}",
            )
        )

        participants = db.execute(select(Participant)).scalars().all()
        synthetic_count = sum(1 for participant in participants if is_synthetic_public_id(participant.public_id))
        if synthetic_count:
            results.append(
                CheckResult(
                    "synthetic_participant_count",
                    "WARNING" if settings.study_mode == "development" else "WARNING",
                    f"{synthetic_count} synthetic participants present (prefixes: {', '.join(get_synthetic_prefixes())})",
                )
            )
        else:
            results.append(CheckResult("synthetic_participant_count", "PASS", "No synthetic participants detected"))

        unresolved_count = sum(
            1 for participant in participants if (participant.age_consent_category or "") == "unresolved"
        )
        if unresolved_count:
            results.append(
                CheckResult(
                    "unresolved_age_consent_category_count",
                    "WARNING",
                    f"{unresolved_count} participants still unresolved",
                )
            )
        else:
            results.append(
                CheckResult(
                    "unresolved_age_consent_category_count",
                    "PASS",
                    "No unresolved age consent categories",
                )
            )

        pending_parental = 0
        for participant in participants:
            status = build_consent_status(db, participant)
            if status["age_category"] == "minor" and status["parental_permission_status"] == "pending":
                pending_parental += 1
        if pending_parental:
            results.append(
                CheckResult(
                    "pending_parental_permission_count",
                    "WARNING",
                    f"{pending_parental} minors awaiting researcher parental verification",
                )
            )
        else:
            results.append(
                CheckResult(
                    "pending_parental_permission_count",
                    "PASS",
                    "No pending parental permission records",
                )
            )

        withdrawn_count = db.execute(
            select(func.count())
            .select_from(ParticipantConsentEvent)
            .where(ParticipantConsentEvent.event_type == "withdrawn")
        ).scalar_one()
        if withdrawn_count:
            results.append(
                CheckResult(
                    "withdrawn_participant_count",
                    "WARNING",
                    f"{withdrawn_count} withdrawal events recorded",
                )
            )
        else:
            results.append(CheckResult("withdrawn_participant_count", "PASS", "No withdrawn participants"))

        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        probe = DOCUMENTS_DIR / ".write_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            results.append(
                CheckResult(
                    "generated_documents_directory_permissions",
                    "PASS",
                    f"Writable directory at {DOCUMENTS_DIR}",
                )
            )
        except OSError as exc:
            results.append(
                CheckResult(
                    "generated_documents_directory_permissions",
                    "FAIL",
                    f"Cannot write to {DOCUMENTS_DIR}: {exc}",
                )
            )
    finally:
        db.close()

    print("NeuroCortex Study Readiness Report")
    print("=" * 40)
    for result in results:
        _print_result(result)

    critical_failures = [
        result for result in results if result.name in CRITICAL_CHECKS and result.status == "FAIL"
    ]
    warnings = [result for result in results if result.status == "WARNING"]
    print("=" * 40)
    print(f"Checks: {len(results)}  Failures: {len(critical_failures)}  Warnings: {len(warnings)}")
    return 1 if critical_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
