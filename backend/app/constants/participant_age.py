MIN_PARTICIPANT_AGE = 11
MAX_PARTICIPANT_AGE = 26

PARTICIPANT_AGES = list(range(MIN_PARTICIPANT_AGE, MAX_PARTICIPANT_AGE + 1))


def validate_participant_age(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("age must be an integer")
    if value < MIN_PARTICIPANT_AGE or value > MAX_PARTICIPANT_AGE:
        raise ValueError(
            f"age must be between {MIN_PARTICIPANT_AGE} and {MAX_PARTICIPANT_AGE}",
        )
    return value


def format_participant_age_display(age_years: int | None, age_range: str | None) -> str:
    if age_years is not None:
        return str(age_years)
    if age_range and age_range.strip():
        return f"{age_range.strip()} (legacy)"
    return "Not Provided"
