"""Pure scheduling logic: which medications are due at a given moment.

No database, no real clock, no time zones: callers pass the medications and the
user's current *local* time. That keeps the trickiest logic easy to test.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")  # index = date.weekday()


@dataclass(frozen=True)
class Medication:
    medication_id: int
    name: str
    time: dt.time                      # local time of day it should be taken
    days: frozenset[str]               # subset of WEEKDAYS
    dose: str | None = None
    instructions: str | None = None
    start_date: dt.date | None = None  # inclusive; None = no start limit
    end_date: dt.date | None = None    # inclusive; None = no end limit
    active: bool = True


@dataclass(frozen=True)
class DueMedication:
    medication: Medication
    scheduled_at: dt.datetime          # the local date and time this dose was scheduled for


def _is_scheduled_on(med: Medication, day: dt.date) -> bool:
    """True if `med` has a dose on the calendar date `day`."""
    if med.start_date is not None and day < med.start_date:
        return False
    if med.end_date is not None and day > med.end_date:
        return False
    return WEEKDAYS[day.weekday()] in med.days


def due_medications(
    medications: Iterable[Medication],
    now: dt.datetime,
    window_minutes: int = 15,
) -> list[DueMedication]:
    """Return the doses scheduled within `window_minutes` before or after `now`.

    A dose counts only if, on the day it is scheduled, the medication is active,
    the weekday is in `days`, and the date is within `start_date`..`end_date`.
    Results are sorted by `scheduled_at`.
    """
    window = dt.timedelta(minutes=window_minutes)
    due = []
    for med in medications:
        if not med.active:
            continue
        # Near midnight the window reaches into yesterday or tomorrow, so check the
        # dose on each of those dates too, using that date's own weekday and range.
        for day_offset in (-1, 0, 1):
            day = now.date() + dt.timedelta(days=day_offset)
            if not _is_scheduled_on(med, day):
                continue
            scheduled_at = dt.datetime.combine(day, med.time, tzinfo=now.tzinfo)
            if abs(scheduled_at - now) <= window:
                due.append(DueMedication(medication=med, scheduled_at=scheduled_at))
    return sorted(due, key=lambda d: d.scheduled_at)
