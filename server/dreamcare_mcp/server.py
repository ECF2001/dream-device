"""DreamCare MCP server: three medication tools for one user.

Run it (from the server/ folder, after `python -m dreamcare_mcp.seed`):
    DREAMCARE_USER_ID=1 python -m dreamcare_mcp.server

It speaks MCP over stdio, so an MCP client (MCP Inspector, Claude Desktop, an agent)
starts it as a subprocess. Settings come from environment variables:
    DREAMCARE_USER_ID  the user this server serves (required)
    DREAMCARE_DB       SQLite file (default: dreamcare.db)
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path
from typing import Annotated, Callable, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from .repository import Repository, UnknownMedicationError, connect
from .schedule import WEEKDAYS, Medication, due_medications

MAX_WINDOW_MINUTES = 120

INSTRUCTIONS = """\
Medication tools for one older adult using the Dream Device voice assistant.
Use get_due_medications to answer "what do I take now?", list_medications for
"what are my medications?", and confirm_intake after the user says whether they
took a dose. Times are in the user's local time zone.
"""


class DueDose(BaseModel):
    medication_id: int
    name: str
    dose: str | None
    instructions: str | None
    scheduled_time: str = Field(description="Local time of the dose, HH:MM")
    scheduled_at: str = Field(description="Local date and time of the dose, ISO 8601 with UTC offset")


class MedicationInfo(BaseModel):
    medication_id: int
    name: str
    dose: str | None
    instructions: str | None
    time: str = Field(description="Local time of day, HH:MM")
    days: list[str] = Field(description="Weekdays, mon..sun")
    start_date: str | None
    end_date: str | None
    active: bool


class IntakeRecorded(BaseModel):
    recorded: bool
    intake_id: int
    medication_id: int
    status: str
    recorded_at: str = Field(description="When it was recorded, ISO 8601 in UTC")


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def create_server(
    repo: Repository, user_id: int, clock: Callable[[], dt.datetime] = _utc_now
) -> MCPServer:
    """Build the MCP server for one user. `clock` returns the current UTC time (fixed in tests)."""
    user = repo.get_user(user_id)
    if user is None:
        raise ValueError(f"user {user_id} not found in the database")
    try:
        tz = ZoneInfo(user.time_zone)
    except ZoneInfoNotFoundError:
        raise ValueError(f"user {user_id} has an unknown time zone: {user.time_zone!r}") from None

    server = MCPServer("dreamcare", instructions=INSTRUCTIONS)

    # Tools are `async def` so they run on the server's event loop, in the same thread
    # that opened the SQLite connection (plain `def` tools would run in a worker thread).

    @server.tool()
    async def get_due_medications(
        window_minutes: Annotated[
            int, Field(ge=1, le=MAX_WINDOW_MINUTES, description="How many minutes before or after now count as due")
        ] = 15,
    ) -> list[DueDose]:
        """Medications the user should take now: doses scheduled within the window, not yet confirmed as taken."""
        now_local = clock().astimezone(tz)
        due = due_medications(repo.list_medications(user_id), now_local, window_minutes)

        window = dt.timedelta(minutes=window_minutes)
        taken = [i for i in repo.list_intakes(user_id) if i.status == "taken"]

        def already_taken(medication_id: int, scheduled_at: dt.datetime) -> bool:
            return any(i.medication_id == medication_id and i.recorded_at >= scheduled_at - window for i in taken)

        return [
            DueDose(
                medication_id=d.medication.medication_id,
                name=d.medication.name,
                dose=d.medication.dose,
                instructions=d.medication.instructions,
                scheduled_time=d.scheduled_at.strftime("%H:%M"),
                scheduled_at=d.scheduled_at.isoformat(),
            )
            for d in due
            if not already_taken(d.medication.medication_id, d.scheduled_at)
        ]

    @server.tool()
    async def list_medications(include_inactive: bool = False) -> list[MedicationInfo]:
        """All of the user's medications with their schedule, ordered by time of day."""
        return [_medication_info(m) for m in repo.list_medications(user_id, include_inactive=include_inactive)]

    @server.tool()
    async def confirm_intake(
        medication_id: int,
        status: Literal["taken", "missed", "unclear"],
    ) -> IntakeRecorded:
        """Record whether the user took a dose: "taken", "missed", or "unclear" if their answer wasn't clear."""
        try:
            intake = repo.record_intake(user_id, medication_id, status, clock())
        except UnknownMedicationError:
            raise ToolError(f"medication {medication_id} not found; call list_medications for valid ids") from None
        return IntakeRecorded(
            recorded=True,
            intake_id=intake.intake_id,
            medication_id=intake.medication_id,
            status=intake.status,
            recorded_at=intake.recorded_at.isoformat(),
        )

    return server


def _medication_info(med: Medication) -> MedicationInfo:
    return MedicationInfo(
        medication_id=med.medication_id,
        name=med.name,
        dose=med.dose,
        instructions=med.instructions,
        time=med.time.strftime("%H:%M"),
        days=[d for d in WEEKDAYS if d in med.days],
        start_date=med.start_date.isoformat() if med.start_date else None,
        end_date=med.end_date.isoformat() if med.end_date else None,
        active=med.active,
    )


def main() -> int:
    """Start the server over stdio. Errors go to stderr: stdout belongs to the MCP protocol."""
    try:
        user_id = int(os.environ.get("DREAMCARE_USER_ID", ""))
    except ValueError:
        print("Set DREAMCARE_USER_ID to a user id number (1 for the seeded demo user).", file=sys.stderr)
        return 1

    db_path = Path(os.environ.get("DREAMCARE_DB", "dreamcare.db"))
    if not db_path.exists():
        print(f"Database {db_path} does not exist. Create it with: python -m dreamcare_mcp.seed", file=sys.stderr)
        return 1

    conn = connect(str(db_path))
    try:
        server = create_server(Repository(conn), user_id)
        server.run()   # stdio
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
