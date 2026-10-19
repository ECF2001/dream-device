"""Tests for dreamcare_mcp.schedule.

Pattern used here:
- `NOW` is a fixed moment, so tests never depend on the real clock.
- `make_med(...)` builds a valid Medication with sensible defaults; each test
  overrides only the fields it cares about, which keeps the test's intent obvious.
"""

import datetime as dt

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
