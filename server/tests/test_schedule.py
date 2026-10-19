"""Tests for dreamcare_mcp.schedule.

Pattern used here:
- `NOW` is a fixed moment, so tests never depend on the real clock.
- `make_med(...)` builds a valid Medication with sensible defaults; each test
  overrides only the fields it cares about, which keeps the test's intent obvious.
"""

import datetime as dt

import pytest

from dreamcare_mcp.schedule import WEEKDAYS, Medication, due_medications

NOW = dt.datetime(2026, 10, 19, 8, 0)  # Monday, 08:00 local time


def make_med(**overrides) -> Medication:
    fields = dict(
        medication_id=1,
        name="Metformina",
        time=dt.time(8, 0),
        days=frozenset(WEEKDAYS),  # every day
    )
    fields.update(overrides)
    return Medication(**fields)


def test_medication_at_exactly_now_is_due():
    med = make_med()

    due = due_medications([med], NOW)

    assert len(due) == 1
    assert due[0].medication == med
    assert due[0].scheduled_at == dt.datetime(2026, 10, 19, 8, 0)


def test_medication_inside_window_is_due():
    med = make_med(time=dt.time(8, 10))   # 10 minutes after NOW

    due = due_medications([med], NOW)     # default window is 15 minutes

    assert len(due) == 1
    assert due[0].scheduled_at == dt.datetime(2026, 10, 19, 8, 10)


def test_medication_outside_window_is_not_due():
    med = make_med(time=dt.time(8, 20))   # 20 minutes after NOW

    due = due_medications([med], NOW)     # default window is 15 minutes

    assert due == []


def test_inactive_medication_is_not_due():
    med = make_med(active=False)          # exactly at NOW, but switched off

    due = due_medications([med], NOW)

    assert due == []


def test_medication_on_listed_weekday_is_due():
    med = make_med(days=frozenset({"mon"}))   # NOW is a Monday

    assert len(due_medications([med], NOW)) == 1


def test_medication_on_other_weekday_is_not_due():
    med = make_med(days=frozenset({"tue"}))   # NOW is a Monday

    assert due_medications([med], NOW) == []


MONDAY = dt.date(2026, 10, 19)  # the date of NOW


@pytest.mark.parametrize(
    ("start_date", "end_date", "expected_due"),
    [
        (MONDAY + dt.timedelta(days=1), None, False),   # starts tomorrow
        (MONDAY, None, True),                           # starts today (inclusive)
        (None, MONDAY, True),                           # ends today (inclusive)
        (None, MONDAY - dt.timedelta(days=1), False),   # ended yesterday
    ],
    ids=["before-start", "on-start", "on-end", "after-end"],
)
def test_date_range_limits_when_medication_is_due(start_date, end_date, expected_due):
    med = make_med(start_date=start_date, end_date=end_date)

    due = due_medications([med], NOW)

    assert (len(due) == 1) is expected_due


def test_late_dose_from_yesterday_is_due_just_after_midnight():
    med = make_med(time=dt.time(23, 55))
    tuesday_after_midnight = dt.datetime(2026, 10, 20, 0, 5)

    due = due_medications([med], tuesday_after_midnight)

    assert len(due) == 1
    assert due[0].scheduled_at == dt.datetime(2026, 10, 19, 23, 55)  # Monday's dose


def test_yesterdays_weekday_rules_apply_across_midnight():
    med = make_med(time=dt.time(23, 55), days=frozenset({"tue"}))  # no Monday dose
    tuesday_after_midnight = dt.datetime(2026, 10, 20, 0, 5)

    assert due_medications([med], tuesday_after_midnight) == []


def test_early_dose_from_tomorrow_is_due_just_before_midnight():
    med = make_med(time=dt.time(0, 5))
    monday_before_midnight = dt.datetime(2026, 10, 19, 23, 55)

    due = due_medications([med], monday_before_midnight)

    assert len(due) == 1
    assert due[0].scheduled_at == dt.datetime(2026, 10, 20, 0, 5)  # Tuesday's dose


def test_due_medications_are_sorted_by_scheduled_time():
    later = make_med(medication_id=1, time=dt.time(8, 10))
    earlier = make_med(medication_id=2, time=dt.time(7, 55))

    due = due_medications([later, earlier], NOW)

    assert [d.medication.medication_id for d in due] == [2, 1]
