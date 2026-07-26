"""Apply Golden Vault demo overrides to researcher/participant display metrics."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant
from app.services.participant_feedback_service import (
    RESEARCHER_STATUS_NOT_RELEASED,
    RESEARCHER_STATUS_RELEASED,
    RESEARCHER_STATUS_REVOKED,
)
from app.services.researcher_dashboard_service import format_study_datetime
from app.config import get_settings


def _study_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().study_timezone)


def demo_last_active_datetime(override: GoldenDemoOverride) -> datetime | None:
    if override.last_active_minute_of_day is None:
        return None
    today = datetime.now(_study_tz()).date()
    yesterday = today - timedelta(days=1)
    hour, minute = divmod(int(override.last_active_minute_of_day), 60)
    local = datetime(
        yesterday.year,
        yesterday.month,
        yesterday.day,
        hour,
        minute,
        tzinfo=_study_tz(),
    )
    return local.astimezone(UTC)


def map_simulated_feedback_status(status: str | None) -> str:
    if status == "Revoked":
        return RESEARCHER_STATUS_REVOKED
    if status == "Released":
        return RESEARCHER_STATUS_RELEASED
    return RESEARCHER_STATUS_NOT_RELEASED


def overrides_visible() -> bool:
    settings = get_settings()
    return bool(getattr(settings, "golden_overrides_visible", True))


def should_apply_override(override: GoldenDemoOverride | None) -> bool:
    if override is None or not override.enabled:
        return False
    if not overrides_visible():
        return False
    return True


def resolve_participant_display_metrics(
    *,
    participant: Participant,
    real_metrics: dict[str, Any],
    golden_override: GoldenDemoOverride | None,
) -> dict[str, Any]:
    real_completed = int(real_metrics.get("sessions_completed") or 0)
    real_started = int(real_metrics.get("sessions_started") or real_metrics.get("sessions") or 0)
    real_status = real_metrics.get("status") or real_metrics.get("realStatus")
    display: dict[str, Any] = {
        "realCompletedSessions": real_completed,
        "realSessionsStarted": real_started,
        "bonusSessions": 0,
        "displayedCompletedSessions": real_completed,
        "isDemoOverride": False,
        "realStatus": real_status,
        "displayStatus": real_status,
    }

    if not should_apply_override(golden_override):
        return display

    if participant.removed_at is not None:
        return display

    bonus_sessions = max(0, int(golden_override.bonus_sessions or 0))
    display.update(
        {
            "bonusSessions": bonus_sessions,
            "displayedCompletedSessions": real_completed + bonus_sessions,
            "isDemoOverride": True,
            "displayStatus": "Active",
        }
    )

    last_active = demo_last_active_datetime(golden_override)
    if last_active is not None:
        display["lastActiveAt"] = last_active
        display["lastActiveDisplay"] = format_study_datetime(last_active)

    if golden_override.simulated_reaction_ms is not None:
        display["averageReactionTimeMs"] = round(float(golden_override.simulated_reaction_ms))
    if golden_override.simulated_stress is not None:
        display["averageStress"] = round(float(golden_override.simulated_stress), 1)
    if golden_override.simulated_fatigue is not None:
        display["averageFatigue"] = round(float(golden_override.simulated_fatigue), 1)
    if golden_override.simulated_sleep_hours is not None:
        display["averageSleepHours"] = round(float(golden_override.simulated_sleep_hours), 1)
    if golden_override.simulated_memory_percent is not None:
        display["averageMemoryAccuracy"] = round(float(golden_override.simulated_memory_percent), 1)
    if golden_override.simulated_session_completion_percent is not None:
        display["sessionCompletion"] = round(float(golden_override.simulated_session_completion_percent), 1)

    display["feedbackStatus"] = map_simulated_feedback_status(golden_override.simulated_feedback_status)
    display["simulatedFeedback"] = {
        "status": golden_override.simulated_feedback_status,
        "level": golden_override.simulated_feedback_level,
        "headline": golden_override.simulated_feedback_headline,
        "summary": golden_override.simulated_feedback_summary,
        "factors": golden_override.simulated_feedback_factors_json or [],
        "isSimulated": True,
    }
    return display


def apply_display_to_dashboard_row(row: dict[str, Any], display: dict[str, Any]) -> None:
    if not display.get("isDemoOverride"):
        return
    row["isDemoOverride"] = True
    row["realCompletedSessions"] = display["realCompletedSessions"]
    row["bonusSessions"] = display["bonusSessions"]
    row["displayedCompletedSessions"] = display["displayedCompletedSessions"]
    row["sessions"] = display["displayedCompletedSessions"]
    if display.get("lastActiveDisplay"):
        row["lastActiveDisplay"] = display["lastActiveDisplay"]
        row["lastActiveAt"] = display.get("lastActiveAt")
    if display.get("displayStatus"):
        row["status"] = display["displayStatus"]
    for key in (
        "averageReactionTimeMs",
        "averageStress",
        "averageFatigue",
        "averageSleepHours",
        "averageMemoryAccuracy",
        "sessionCompletion",
        "feedbackStatus",
    ):
        if key in display:
            row[key] = display[key]


def apply_display_to_game_data(game_data: dict[str, Any] | None, override: GoldenDemoOverride | None) -> dict[str, Any] | None:
    if game_data is None:
        game_data = {}
    if not should_apply_override(override):
        return game_data
    earned_coins = int(game_data.get("coins") or 0)
    real_days = int(game_data.get("totalDays") or 0)
    bonus_coins = max(0, int(override.bonus_coins or 0))
    bonus_sessions = max(0, int(override.bonus_sessions or 0))
    payload = dict(game_data)
    payload["earnedCoins"] = earned_coins
    payload["bonusCoins"] = bonus_coins
    payload["displayedCoins"] = earned_coins + bonus_coins
    payload["coins"] = earned_coins + bonus_coins
    payload["realTotalDays"] = real_days
    payload["bonusStudyDays"] = bonus_sessions
    payload["totalDays"] = real_days + bonus_sessions
    payload["isDemoOverride"] = True
    payload["demoAccount"] = True
    return payload
