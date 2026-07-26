"""Generate persistent simulated demo metrics for Golden Vault."""

from __future__ import annotations

import random
from typing import Any

from app.models.golden_demo_override import GoldenDemoOverride

FEEDBACK_LEVELS = ("low", "moderate", "elevated", "unclear")
FEEDBACK_STATUSES = ("Released", "Not Released", "Revoked")


def _rand_float(rng: random.Random, low: float, high: float, places: int = 1) -> float:
    value = rng.uniform(low, high)
    return round(value, places)


def generate_demo_profile(*, seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(seed if seed is not None else random.randint(1, 2_000_000_000))
    profile_seed = seed if seed is not None else rng.randint(1, 2_000_000_000)
    rng = random.Random(profile_seed)

    stress = _rand_float(rng, 1.5, 8.8)
    fatigue = _rand_float(rng, 1.5, 8.8)
    memory = _rand_float(rng, 55.0, 98.0, 1)
    completion = _rand_float(rng, 75.0, 100.0, 1)

    if stress <= 3.5 and fatigue <= 3.5:
        level = "low"
        headline = "Lower strain indicators"
    elif stress >= 7.0 or fatigue >= 7.0:
        level = "elevated"
        headline = "Elevated strain indicators"
    elif stress >= 5.0 or fatigue >= 5.0:
        level = "moderate"
        headline = "Moderate strain indicators"
    else:
        level = "unclear"
        headline = "Unclear pattern"

    minute_of_day = rng.randint(14 * 60, 20 * 60)

    factors_pool = [
        "Reaction-time consistency",
        "Attention-task performance",
        "Recent typing patterns",
        "Memory-task accuracy",
        "Survey response trends",
    ]
    rng.shuffle(factors_pool)
    factors = factors_pool[: rng.randint(1, 3)]

    return {
        "random_seed": profile_seed,
        "simulated_reaction_ms": round(rng.uniform(230, 650)),
        "simulated_stress": stress,
        "simulated_fatigue": fatigue,
        "simulated_sleep_hours": _rand_float(rng, 4.5, 9.5, 1),
        "simulated_memory_percent": memory,
        "simulated_session_completion_percent": completion,
        "last_active_minute_of_day": minute_of_day,
        "simulated_feedback_status": "Released",
        "simulated_feedback_level": level,
        "simulated_feedback_headline": headline[:80],
        "simulated_feedback_summary": (
            "Your recent study activity shows patterns associated with cognitive strain indicators "
            "based on demo metrics for presentation purposes."
        )[:500],
        "simulated_feedback_factors_json": factors,
    }


def apply_profile_to_override(row: GoldenDemoOverride, profile: dict[str, Any]) -> None:
    row.random_seed = profile["random_seed"]
    row.simulated_reaction_ms = profile["simulated_reaction_ms"]
    row.simulated_stress = profile["simulated_stress"]
    row.simulated_fatigue = profile["simulated_fatigue"]
    row.simulated_sleep_hours = profile["simulated_sleep_hours"]
    row.simulated_memory_percent = profile["simulated_memory_percent"]
    row.simulated_session_completion_percent = profile["simulated_session_completion_percent"]
    row.last_active_minute_of_day = profile["last_active_minute_of_day"]
    row.simulated_feedback_status = profile.get("simulated_feedback_status", "Released")
    row.simulated_feedback_level = profile.get("simulated_feedback_level")
    row.simulated_feedback_headline = profile.get("simulated_feedback_headline")
    row.simulated_feedback_summary = profile.get("simulated_feedback_summary")
    row.simulated_feedback_factors_json = profile.get("simulated_feedback_factors_json") or []
