"""SQLite data access for users, medications and the intake log.

This is the only module that knows about SQL. It converts between database rows
(text columns) and the Python types the rest of the code uses (`schedule.Medication`,
`dt.time`, `dt.date`, timezone-aware `dt.datetime`). Database errors are never hidden.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from .schedule import WEEKDAYS, Medication

DEFAULT_TIME_ZONE = "America/Costa_Rica"
INTAKE_STATUSES = ("taken", "missed", "unclear")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    time_zone  TEXT NOT NULL DEFAULT '{DEFAULT_TIME_ZONE}'
);

CREATE TABLE IF NOT EXISTS medications (
    medication_id INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    name          TEXT NOT NULL,
    dose          TEXT,
    instructions  TEXT,
    days          TEXT NOT NULL,          -- e.g. 'mon,wed,fri'
    time          TEXT NOT NULL,          -- 'HH:MM', local time
    start_date    TEXT,                   -- 'YYYY-MM-DD' or NULL
    end_date      TEXT,                   -- 'YYYY-MM-DD' or NULL
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS intake_log (
    intake_id     INTEGER PRIMARY KEY,
    medication_id INTEGER NOT NULL REFERENCES medications(medication_id),
    status        TEXT NOT NULL CHECK (status IN {INTAKE_STATUSES}),
    recorded_at   TEXT NOT NULL           -- ISO 8601, UTC
);
"""


class UnknownMedicationError(LookupError):
    """The medication does not exist, or belongs to a different user."""


@dataclass(frozen=True)
class User:
    user_id: int
    name: str
    time_zone: str


@dataclass(frozen=True)
class Intake:
    intake_id: int
    medication_id: int
    status: str
    recorded_at: dt.datetime   # timezone-aware, UTC


def connect(path: str) -> sqlite3.Connection:
    """Open a database (a file path, or ":memory:" for tests)."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite leaves foreign keys off by default
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the tables if they don't exist yet."""
    conn.executescript(SCHEMA)


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # --- users -------------------------------------------------------------

    def add_user(self, name: str, time_zone: str = DEFAULT_TIME_ZONE) -> int:
        with self._conn:   # commits on success, rolls back on error
            cur = self._conn.execute(
                "INSERT INTO users (name, time_zone) VALUES (?, ?)", (name, time_zone)
            )
        return cur.lastrowid

    def get_user(self, user_id: int) -> User | None:
        row = self._conn.execute(
            "SELECT user_id, name, time_zone FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return User(**row) if row else None

    # --- medications ---------------------------------------------------------

    def add_medication(
        self,
        user_id: int,
        *,
        name: str,
        time: dt.time,
        days: frozenset[str],
        dose: str | None = None,
        instructions: str | None = None,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
        active: bool = True,
    ) -> Medication:
        unknown = set(days) - set(WEEKDAYS)
        if not days or unknown:
            raise ValueError(f"days must be a non-empty subset of {WEEKDAYS}, got unknown {sorted(unknown)}")

        days_text = ",".join(d for d in WEEKDAYS if d in days)   # stable order: mon..sun
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO medications
                    (user_id, name, dose, instructions, days, time, start_date, end_date, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, name, dose, instructions, days_text, time.strftime("%H:%M"),
                    start_date.isoformat() if start_date else None,
                    end_date.isoformat() if end_date else None,
                    int(active),
                ),
            )
        return Medication(
            medication_id=cur.lastrowid, name=name, time=time.replace(second=0, microsecond=0),
            days=frozenset(days), dose=dose, instructions=instructions,
            start_date=start_date, end_date=end_date, active=active,
        )

    def list_medications(self, user_id: int, include_inactive: bool = False) -> list[Medication]:
        sql = "SELECT * FROM medications WHERE user_id = ?"
        if not include_inactive:
            sql += " AND active = 1"
        sql += " ORDER BY time, medication_id"
        return [_row_to_medication(row) for row in self._conn.execute(sql, (user_id,))]

    # --- intake log ----------------------------------------------------------

    def record_intake(
        self, user_id: int, medication_id: int, status: str, recorded_at: dt.datetime
    ) -> Intake:
        if status not in INTAKE_STATUSES:
            raise ValueError(f"status must be one of {INTAKE_STATUSES}, got {status!r}")
        if recorded_at.tzinfo is None:
            raise ValueError("recorded_at must include a time zone (use UTC)")

        owned = self._conn.execute(
            "SELECT 1 FROM medications WHERE medication_id = ? AND user_id = ?",
            (medication_id, user_id),
        ).fetchone()
        if not owned:
            raise UnknownMedicationError(f"medication {medication_id} not found for this user")

        recorded_utc = recorded_at.astimezone(dt.timezone.utc)
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO intake_log (medication_id, status, recorded_at) VALUES (?, ?, ?)",
                (medication_id, status, recorded_utc.isoformat()),
            )
        return Intake(cur.lastrowid, medication_id, status, recorded_utc)

    def list_intakes(self, user_id: int) -> list[Intake]:
        rows = self._conn.execute(
            """
            SELECT i.intake_id, i.medication_id, i.status, i.recorded_at
            FROM intake_log AS i
            JOIN medications AS m ON m.medication_id = i.medication_id
            WHERE m.user_id = ?
            ORDER BY i.recorded_at, i.intake_id
            """,
            (user_id,),
        )
        return [
            Intake(r["intake_id"], r["medication_id"], r["status"], dt.datetime.fromisoformat(r["recorded_at"]))
            for r in rows
        ]


def _row_to_medication(row: sqlite3.Row) -> Medication:
    return Medication(
        medication_id=row["medication_id"],
        name=row["name"],
        time=dt.time.fromisoformat(row["time"]),
        days=frozenset(row["days"].split(",")),
        dose=row["dose"],
        instructions=row["instructions"],
        start_date=dt.date.fromisoformat(row["start_date"]) if row["start_date"] else None,
        end_date=dt.date.fromisoformat(row["end_date"]) if row["end_date"] else None,
        active=bool(row["active"]),
    )
