"""Study schedule preference values and display labels."""

from __future__ import annotations

STUDY_FREQUENCY_DAILY = "daily"
STUDY_FREQUENCY_TWICE_WEEKLY = "twice_weekly"
STUDY_FREQUENCY_FOUR_TIMES_WEEKLY = "four_times_weekly"
STUDY_FREQUENCY_WEEKLY = "weekly"

ALLOWED_STUDY_FREQUENCIES = frozenset(
    {
        STUDY_FREQUENCY_DAILY,
        STUDY_FREQUENCY_TWICE_WEEKLY,
        STUDY_FREQUENCY_FOUR_TIMES_WEEKLY,
        STUDY_FREQUENCY_WEEKLY,
    }
)

STUDY_FREQUENCY_LABELS: dict[str, str] = {
    STUDY_FREQUENCY_DAILY: "Daily",
    STUDY_FREQUENCY_TWICE_WEEKLY: "Twice a Week",
    STUDY_FREQUENCY_FOUR_TIMES_WEEKLY: "4 Times a Week",
    STUDY_FREQUENCY_WEEKLY: "Weekly",
}


def study_frequency_label(value: str | None) -> str:
    if value is None:
        return "Not Selected"
    return STUDY_FREQUENCY_LABELS.get(value, "Not Selected")


def validate_study_frequency(value: str) -> str:
    cleaned = value.strip()
    if cleaned not in ALLOWED_STUDY_FREQUENCIES:
        raise ValueError(
            "study_frequency must be one of: daily, twice_weekly, four_times_weekly, weekly"
        )
    return cleaned
