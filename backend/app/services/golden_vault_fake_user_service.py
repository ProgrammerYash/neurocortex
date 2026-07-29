"""Golden Vault synthetic demo participant batch generation."""

from __future__ import annotations

import random
import secrets
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.consent_record import ConsentRecord
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.golden_fake_user_batch import GoldenFakeUserBatch
from app.models.participant import Participant
from app.models.participant_game_data import ParticipantGameData
from app.schemas.game import GameDataPayload
from app.services.audit_service import record_audit_event
from app.services.electronic_consent_service import create_consent_record_uncommitted
from app.services.golden_vault_auto_data_service import (
    apply_auto_data_config,
    apply_backfill_batch,
    default_weekdays_for_frequency,
    map_participant_frequency,
)
from app.services.golden_vault_profile import apply_profile_to_override, generate_demo_profile
from app.services.study_frequency import (
    STUDY_FREQUENCY_DAILY,
    STUDY_FREQUENCY_FOUR_TIMES_WEEKLY,
    STUDY_FREQUENCY_TWICE_WEEKLY,
    STUDY_FREQUENCY_WEEKLY,
)
from app.utils.ids import generate_public_id
from app.utils.security import hash_pin
from jose import JWTError, jwt

FIRST_NAMES = ("Alex", "Blake", "Casey", "Drew", "Emery", "Finley", "Gray", "Harper", "Indie", "Jordan")
LAST_NAMES = ("Brooks", "Chen", "Diaz", "Ellis", "Frost", "Grant", "Hayes", "Ivers", "Jules", "Keene")
GUARDIAN_LAST = ("Morgan", "Reed", "Shaw", "Vale", "Wells", "York", "Lane", "Pierce", "Quinn", "Rowe")
GRADES = ("9th Grade", "10th Grade", "11th Grade", "12th Grade")
PETS = ("fox", "owl", "cat", "dragon")
_CREDENTIALS_AUD = "golden_fake_user_credentials"


def _credentials_settings():
    settings = get_settings()
    return settings.jwt_secret, settings.jwt_algorithm


def _merge_sealed_credentials(sealed: str | None, new_items: list[dict[str, str]]) -> str:
    secret, algorithm = _credentials_settings()
    existing: list[dict[str, str]] = []
    if sealed:
        try:
            payload = jwt.decode(sealed, secret, algorithms=[algorithm], audience=_CREDENTIALS_AUD)
            raw = payload.get("items")
            if isinstance(raw, list):
                existing = [item for item in raw if isinstance(item, dict)]
        except JWTError:
            existing = []
    merged = existing + new_items
    return jwt.encode(
        {"items": merged, "aud": _CREDENTIALS_AUD},
        secret,
        algorithm=algorithm,
    )


def _unseal_credentials(sealed: str) -> list[dict[str, str]]:
    secret, algorithm = _credentials_settings()
    payload = jwt.decode(sealed, secret, algorithms=[algorithm], audience=_CREDENTIALS_AUD)
    raw = payload.get("items")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict) and item.get("publicId") and item.get("temporaryPin")]


def batch_status_payload(batch: GoldenFakeUserBatch) -> dict[str, Any]:
    return {
        "batchId": str(batch.id),
        "status": batch.status,
        "requestedCount": batch.requested_count,
        "processedCount": batch.processed_count,
        "successfulCount": batch.successful_count,
        "failedCount": batch.failed_count,
        "startDate": batch.start_date.isoformat(),
        "dailyCount": batch.daily_count,
        "weeklyCount": batch.weekly_count,
        "twoDaysCount": batch.two_days_count,
        "fourDaysCount": batch.four_days_count,
        "credentialsAvailable": bool(
            batch.credentials_sealed and batch.credentials_viewed_at is None and batch.status.startswith("completed")
        ),
        "credentialsViewedAt": batch.credentials_viewed_at.isoformat() if batch.credentials_viewed_at else None,
        "errors": (batch.error_summary_json or {}).get("errors") if batch.error_summary_json else None,
    }


def claim_batch_credentials(db: Session, *, batch_id: uuid.UUID) -> dict[str, Any]:
    batch = db.get(GoldenFakeUserBatch, batch_id)
    if batch is None:
        raise FakeUserBatchError("Batch not found", status_code=404)
    if not batch.status.startswith("completed"):
        raise FakeUserBatchError("Batch is not finished yet", status_code=409)
    if batch.credentials_viewed_at is not None:
        raise FakeUserBatchError("Credentials were already retrieved", status_code=410)
    if not batch.credentials_sealed:
        raise FakeUserBatchError("No credentials are available for this batch", status_code=404)
    items = _unseal_credentials(batch.credentials_sealed)
    batch.credentials_sealed = None
    batch.credentials_viewed_at = datetime.now(UTC)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.fake_user_credentials_claimed",
        metadata={"batch_id": str(batch.id), "count": len(items)},
    )
    return {"batchId": str(batch.id), "credentials": items}


def _initial_game_data(profile: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    payload = {
        "pet": {"type": profile["pet"], "xp": 0, "level": 1},
        "house": {"items": []},
        "coins": rng.randint(25, 120),
        "streak": rng.randint(0, 4),
        "longestStreak": rng.randint(0, 6),
        "totalDays": rng.randint(0, 8),
        "lastCompleted": None,
        "achievements": [],
        "unlockedRegions": [],
        "milestones": [],
    }
    return GameDataPayload.model_validate(payload).model_dump()


class FakeUserBatchError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _validate_distribution(
    *,
    total: int,
    daily: int,
    weekly: int,
    two_days: int,
    four_days: int,
) -> None:
    settings = get_settings()
    if total < 1:
        raise FakeUserBatchError("At least one user is required")
    if total > settings.golden_fake_user_batch_limit:
        raise FakeUserBatchError(
            f"Requested count exceeds limit of {settings.golden_fake_user_batch_limit}",
            status_code=400,
        )
    for label, value in (
        ("Daily", daily),
        ("Weekly", weekly),
        ("Two days/week", two_days),
        ("Four days/week", four_days),
    ):
        if value < 0 or value != int(value):
            raise FakeUserBatchError(f"{label} count must be a non-negative integer")
    if daily + weekly + two_days + four_days != total:
        raise FakeUserBatchError("Schedule distribution must equal total user count")


def _frequency_plan(daily: int, weekly: int, two_days: int, four_days: int) -> list[str]:
    plan: list[str] = []
    plan.extend([STUDY_FREQUENCY_DAILY] * daily)
    plan.extend([STUDY_FREQUENCY_WEEKLY] * weekly)
    plan.extend([STUDY_FREQUENCY_TWICE_WEEKLY] * two_days)
    plan.extend([STUDY_FREQUENCY_FOUR_TIMES_WEEKLY] * four_days)
    return plan


def preview_fake_users(
    db: Session,
    *,
    total: int,
    start_date: date,
    daily: int,
    weekly: int,
    two_days: int,
    four_days: int,
) -> dict[str, Any]:
    _validate_distribution(total=total, daily=daily, weekly=weekly, two_days=two_days, four_days=four_days)
    settings = get_settings()
    batches = max(1, (total + settings.golden_fake_user_batch_size - 1) // settings.golden_fake_user_batch_size)
    from app.services.golden_vault_auto_data_service import _today_local, iter_scheduled_dates

    estimated_events = 0
    through = _today_local()
    for index, frequency in enumerate(_frequency_plan(daily, weekly, two_days, four_days)):
        seed = 1000 + index
        weekdays = default_weekdays_for_frequency(frequency=frequency, seed=seed)
        estimated_events += sum(
            1
            for _ in iter_scheduled_dates(
                start_date=start_date,
                end_date=None,
                frequency=frequency,
                weekdays=weekdays,
                through_local=through,
            )
        )
    return {
        "totalUsers": total,
        "startDate": start_date.isoformat(),
        "dailyCount": daily,
        "weeklyCount": weekly,
        "twoDaysCount": two_days,
        "fourDaysCount": four_days,
        "estimatedAutoDataEvents": estimated_events,
        "estimatedPdfCount": total,
        "estimatedGenerationBatches": batches,
    }


def create_fake_user_batch(
    db: Session,
    *,
    total: int,
    start_date: date,
    daily: int,
    weekly: int,
    two_days: int,
    four_days: int,
    idempotency_key: str | None,
    created_by: str = "golden_vault",
) -> GoldenFakeUserBatch:
    _validate_distribution(total=total, daily=daily, weekly=weekly, two_days=two_days, four_days=four_days)
    if idempotency_key:
        existing = db.execute(
            select(GoldenFakeUserBatch).where(GoldenFakeUserBatch.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            return existing
    batch = GoldenFakeUserBatch(
        id=uuid.uuid4(),
        requested_count=total,
        daily_count=daily,
        weekly_count=weekly,
        two_days_count=two_days,
        four_days_count=four_days,
        start_date=start_date,
        status="pending",
        idempotency_key=idempotency_key,
        created_by=created_by,
    )
    db.add(batch)
    db.flush()
    record_audit_event(db, actor_type="golden_vault", event_type="golden_vault.fake_user_batch_created", metadata={"batch_id": str(batch.id), "requested": total})
    return batch


def _unique_public_id(db: Session) -> str:
    for _ in range(8):
        candidate = generate_public_id()
        if db.execute(select(Participant.id).where(Participant.public_id == candidate)).first() is None:
            return candidate
    raise FakeUserBatchError("Could not allocate participant id", status_code=500)


def _profile_for_index(index: int, frequency: str) -> dict[str, Any]:
    rng = random.Random(9000 + index)
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    guardian = f"{rng.choice(GUARDIAN_LAST)} {last}"
    age = rng.choice([13, 14, 15, 16, 17])
    return {
        "participant_name": f"{first} {last}",
        "guardian_name": guardian,
        "age": age,
        "grade": rng.choice(GRADES),
        "pet": rng.choice(PETS),
        "frequency": frequency,
        "seed": 5000 + index,
    }


def process_fake_user_batch_chunk(db: Session, *, batch_id: uuid.UUID) -> dict[str, Any]:
    batch = db.get(GoldenFakeUserBatch, batch_id)
    if batch is None:
        raise FakeUserBatchError("Batch not found", status_code=404)
    if batch.status in {"completed", "failed"}:
        return {"status": batch.status, "processed": batch.processed_count}
    if batch.status == "pending":
        batch.status = "running"
        batch.started_at = datetime.now(UTC)
    settings = get_settings()
    chunk = settings.golden_fake_user_batch_size
    plan = _frequency_plan(batch.daily_count, batch.weekly_count, batch.two_days_count, batch.four_days_count)
    credentials: list[dict[str, str]] = []
    errors: list[str] = []
    start_index = batch.processed_count
    end_index = min(batch.requested_count, start_index + chunk)
    for index in range(start_index, end_index):
        frequency = plan[index]
        profile = _profile_for_index(index, frequency)
        pin = f"{secrets.randbelow(900000) + 100000}"[:6]
        if len(pin) < 4:
            pin = "2468"
        try:
            public_id = _unique_public_id(db)
            participant = Participant(
                public_id=public_id,
                pin_hash=hash_pin(pin),
                grade=profile["grade"],
                age_range=str(profile["age"]),
                age_years=profile["age"],
                age_consent_category="under_18",
                pet_choice=profile["pet"],
                study_frequency=map_participant_frequency(frequency),
            )
            db.add(participant)
            db.flush()
            row = GoldenDemoOverride(participant_id=participant.id, enabled=True, random_seed=profile["seed"])
            apply_profile_to_override(row, generate_demo_profile(seed=profile["seed"]))
            row.is_synthetic_generated = True
            row.synthetic_batch_id = batch.id
            db.add(row)
            db.flush()
            game_rng = random.Random(profile["seed"] + 17)
            game_payload = _initial_game_data(profile, game_rng)
            db.add(
                ParticipantGameData(
                    participant_id=participant.id,
                    game_data=game_payload,
                    updated_at=datetime.now(UTC),
                )
            )
            db.flush()
            weekdays = default_weekdays_for_frequency(frequency=frequency, seed=profile["seed"])
            apply_auto_data_config(
                db,
                participant=participant,
                row=row,
                start_date=batch.start_date,
                end_date=None,
                frequency=frequency,
                weekdays=weekdays,
                enable_future=True,
            )
            while True:
                result = apply_backfill_batch(db, participant=participant, row=row, limit=chunk)
                if result.get("created", 0) == 0:
                    break
            consent_payload = {
                "participant_printed_name": profile["participant_name"],
                "guardian_printed_name": profile["guardian_name"],
                "participant_acknowledged": True,
                "guardian_acknowledged": True,
                "participant_signature_agreed": True,
                "guardian_signature_agreed": True,
                "consent_version": batch.created_at and "2026-pilot-v1",
                "idempotency_key": str(uuid.uuid4()),
                "is_synthetic_demo_record": True,
                "synthetic_batch_id": batch.id,
            }
            from app.services.consent_content import CONSENT_VERSION, SURVEY_VERSION, EXPECTED_TEMPLATE_SHA256

            consent_payload.update(
                {
                    "consent_version": CONSENT_VERSION,
                    "survey_version": SURVEY_VERSION,
                    "template_sha256": EXPECTED_TEMPLATE_SHA256,
                }
            )
            create_consent_record_uncommitted(db, participant=participant, payload=consent_payload)
            batch.successful_count += 1
            credentials.append({"publicId": public_id, "temporaryPin": pin})
        except Exception as exc:
            batch.failed_count += 1
            errors.append(str(exc)[:200])
        batch.processed_count += 1
    if batch.processed_count >= batch.requested_count:
        batch.status = "completed_with_errors" if batch.failed_count else "completed"
        batch.completed_at = datetime.now(UTC)
    if credentials:
        batch.credentials_sealed = _merge_sealed_credentials(batch.credentials_sealed, credentials)
    db.flush()
    if errors:
        batch.error_summary_json = {"errors": errors[:20]}
    return {
        "batchId": str(batch.id),
        "status": batch.status,
        "processedCount": batch.processed_count,
        "successfulCount": batch.successful_count,
        "failedCount": batch.failed_count,
        "credentialsAvailable": bool(
            batch.credentials_sealed and batch.credentials_viewed_at is None and batch.status.startswith("completed")
        ),
        "errors": errors[:5] if errors else None,
    }
