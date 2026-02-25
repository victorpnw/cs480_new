"""
schemas.py — Data Transfer Objects (DTOs) using Python dataclasses.

DTOs are simple containers that carry data between layers.  They are *not*
tied to the database — they exist so the service layer can hand structured
results to the UI layer without exposing ORM internals.

Key concepts for beginners:
    @dataclass:  A Python decorator that auto-generates ``__init__``,
                 ``__repr__``, and ``__eq__`` for you.  All you do is list the
                 fields and their types.
    Enum:        A fixed set of named constants (like a dropdown with only
                 three choices).

Why not just return dictionaries?
    Dataclasses give you autocomplete in your IDE, catch typos at development
    time, and make the code easier to read for your teammates.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum


# ---------------------------------------------------------------------------
# Defect status — maps directly to AC1 / AC2 / AC4
# ---------------------------------------------------------------------------
class DefectStatus(Enum):
    """Classification outcome for a defect code.

    Values:
        RECURRING:          The defect appeared in >1 calendar week AND >1 lot
                            (AC1).
        NOT_RECURRING:      The defect did not meet the recurring threshold
                            (AC2).
        INSUFFICIENT_DATA:  Data gaps prevent a confident classification (AC4).
    """

    RECURRING = "Recurring"
    NOT_RECURRING = "Not recurring"
    INSUFFICIENT_DATA = "Insufficient data"


# ---------------------------------------------------------------------------
# AC5 — one row in the "Recurring Defects" list view
# ---------------------------------------------------------------------------
@dataclass
class RecurringDefectRow:
    """A single row in the Recurring Defects summary table (AC5).

    Each instance represents one ``defect_code`` and its aggregated statistics
    over the selected date range.

    Attributes:
        defect_code:    The human-readable defect identifier (e.g., 'DEF-001').
        status:         Classification result — see ``DefectStatus``.
        num_weeks:      Number of distinct calendar weeks with occurrences
                        (zero-defect records excluded per AC3).
        num_lots:       Number of distinct lots affected.
        first_seen:     Earliest inspection date with qty_defects > 0.
        last_seen:      Latest inspection date with qty_defects > 0.
        total_qty:      Sum of qty_defects across all matching records.
    """

    defect_code: str
    status: DefectStatus
    num_weeks: int
    num_lots: int
    first_seen: date
    last_seen: date
    total_qty: int


# ---------------------------------------------------------------------------
# AC7 — one week's worth of data in the drill-down detail view
# ---------------------------------------------------------------------------
@dataclass
class WeeklyBreakdownRow:
    """One row in the weekly drill-down for a specific defect code (AC7).

    Attributes:
        week_start:     The Monday (or first day) of the calendar week.
        week_end:       The Sunday (or last day) of the calendar week.
        lots_involved:  List of lot IDs that had this defect during the week.
        total_qty:      Sum of qty_defects for this defect in this week.
    """

    week_start: date
    week_end: date
    lots_involved: list[str]
    total_qty: int


# ---------------------------------------------------------------------------
# AC7 — a single underlying inspection record shown in the drill-down
# ---------------------------------------------------------------------------
@dataclass
class InspectionDetail:
    """One raw inspection record displayed in the drill-down view (AC7).

    Attributes:
        lot_id:           The lot's business identifier.
        inspection_date:  Date the inspection was performed.
        defect_code:      The defect's business identifier.
        qty_defects:      Number of defects recorded.
    """

    lot_id: str
    inspection_date: date
    defect_code: str
    qty_defects: int


# ---------------------------------------------------------------------------
# AC8 — information about missing data periods
# ---------------------------------------------------------------------------
@dataclass
class MissingPeriod:
    """Describes a time period with incomplete data (AC8).

    Shown to the user when a defect is classified as "Insufficient data" so
    they understand *why* a determination could not be made.

    Attributes:
        period_start:  First date of the gap.
        period_end:    Last date of the gap.
        reason:        Human-readable explanation (e.g., "Missing inspection
                       records for weeks of 2026-01-05 to 2026-01-19").
    """

    period_start: date
    period_end: date
    reason: str
