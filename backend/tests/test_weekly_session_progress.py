from __future__ import annotations

from datetime import date

from app.services.study_week import week_bounds_for, weekly_session_target


def test_weekly_session_targets():
    assert weekly_session_target("daily") == 7
    assert weekly_session_target("four_times_weekly") == 4
    assert weekly_session_target("twice_weekly") == 2
    assert weekly_session_target("weekly") == 1


def test_weekly_bounds_monday_sunday():
    start, end = week_bounds_for(date(2026, 7, 25))
    assert start.weekday() == 0
    assert end.weekday() == 6
