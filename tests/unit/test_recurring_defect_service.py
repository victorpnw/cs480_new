"""
test_recurring_defect_service.py — Unit tests for the RecurringDefectService.

These tests verify the *business logic* in isolation — no real database is
involved.  Instead we create plain Python objects (``InspectionRecord``,
``Lot``, ``Defect``) in memory and feed them to the service through a fake
repository.

Key concepts for beginners:
    pytest:     Run all tests with ``poetry run pytest``.  Any function whose
                name starts with ``test_`` is automatically discovered.
    Fixture:    A ``@pytest.fixture`` is a reusable setup step.  pytest injects
                it into your test function by matching the parameter name.
    Arrange-Act-Assert (AAA):
                1. *Arrange* — set up test data and dependencies.
                2. *Act* — call the function you're testing.
                3. *Assert* — check that the result matches expectations.

Acceptance Criteria covered:
    AC1 — Recurring classification (>1 week, >1 lot)
    AC2 — Not recurring (single lot only)
    AC3 — Zero-defect records excluded
    AC4 — Insufficient data flag
    AC5 — Summary list fields
    AC7 — Drill-down detail (weekly breakdown + raw records)
    AC8 — Missing period identification
    AC9 — Default sort order
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

from src.schemas import DefectStatus
from src.services.recurring_defect_service import RecurringDefectService
from src.models import InspectionRecord, Lot, Defect


# ---------------------------------------------------------------------------
# Fixtures — reusable test setup
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repository():
    """Create a fake repository that returns controlled test data.

    Instead of hitting a real database, we use ``MagicMock`` to simulate the
    repository.  In each test you configure what ``get_records_by_date_range``
    (or other methods) should return.

    Returns:
        A ``MagicMock`` standing in for ``InspectionRepository``.
    """
    return MagicMock()


@pytest.fixture
def service(mock_repository):
    """Create a ``RecurringDefectService`` wired to the fake repository.

    Returns:
        A ready-to-use service instance.
    """
    return RecurringDefectService(mock_repository)


# ---------------------------------------------------------------------------
# Helper — build test data quickly
# ---------------------------------------------------------------------------


def _make_record(
    defect_code: str,
    lot_id: str,
    inspection_date: date,
    qty_defects: int,
    is_data_complete: bool = True,
) -> InspectionRecord:
    """Convenience factory for creating in-memory InspectionRecord objects.

    These are *not* persisted to any database — they're just plain objects
    used to feed the service in tests.

    Args:
        defect_code:      e.g., 'DEF-001'.
        lot_id:           e.g., 'LOT-A'.
        inspection_date:  The date of the inspection.
        qty_defects:      Number of defects found.
        is_data_complete: Whether the data is trustworthy (default True).

    Returns:
        An ``InspectionRecord`` with related ``Lot`` and ``Defect`` attached.
    """
    defect = Defect(defect_code=defect_code)
    lot = Lot(lot_id=lot_id)
    record = InspectionRecord(
        inspection_date=inspection_date,
        qty_defects=qty_defects,
        is_data_complete=is_data_complete,
    )
    record.defect = defect
    record.lot = lot
    return record


# ============================= AC1 =======================================
class TestAC1RecurringClassification:
    """AC1: A defect is recurring when it appears in >1 calendar week
    AND in >1 lot."""

    def test_defect_in_multiple_weeks_and_lots_is_recurring(
        self, service, mock_repository
    ):
        """Given DEF-001 in LOT-A (week 1) and LOT-B (week 2),
        it should be classified as Recurring."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),  # week 1
            _make_record(
                "DEF-001", "LOT-B", date(2026, 1, 13), qty_defects=2
            ),  # week 2
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 1
        row = result[0]
        assert row.defect_code == "DEF-001"
        assert row.status == DefectStatus.RECURRING

    def test_defect_in_multiple_weeks_but_single_lot_is_not_recurring(
        self, service, mock_repository
    ):
        """Given DEF-002 in LOT-A in both week 1 and week 2 (same lot),
        it should NOT be recurring — AC1 requires >1 lot."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-002", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record("DEF-002", "LOT-A", date(2026, 1, 13), qty_defects=2),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 1
        assert result[0].status == DefectStatus.NOT_RECURRING

    def test_defect_in_multiple_lots_but_single_week_is_not_recurring(
        self, service, mock_repository
    ):
        """Given DEF-001 in LOT-A and LOT-B but both in the same week,
        it should NOT be recurring — AC1 requires >1 week."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 11)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record("DEF-001", "LOT-B", date(2026, 1, 7), qty_defects=2),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 1
        assert result[0].status == DefectStatus.NOT_RECURRING


# ============================= AC2 =========================================
class TestAC2SingleLotNotRecurring:
    """AC2: A defect that only appears within a single lot should NOT be
    classified as recurring, even if it has multiple records."""

    def test_single_lot_multiple_records_not_recurring(self, service, mock_repository):
        """Given DEF-003 with 3 records all in LOT-A,
        status should be Not recurring."""
        # Arrange
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-003", "LOT-A", date(2026, 1, 6), qty_defects=2),
            _make_record("DEF-003", "LOT-A", date(2026, 1, 13), qty_defects=4),
            _make_record("DEF-003", "LOT-A", date(2026, 1, 20), qty_defects=1),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 1
        assert result[0].defect_code == "DEF-003"
        assert result[0].status == DefectStatus.NOT_RECURRING


# ============================= AC3 =========================================
class TestAC3ZeroDefectsExcluded:
    """AC3: Records with qty_defects == 0 should not count as an occurrence."""

    def test_zero_defect_records_are_ignored(self, service, mock_repository):
        """Given DEF-004 with qty_defects=0 in week 1 and qty_defects=5 in
        week 2, only week 2 should count → only 1 week → Not recurring."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-004", "LOT-A", date(2026, 1, 6), qty_defects=0),
            _make_record("DEF-004", "LOT-B", date(2026, 1, 13), qty_defects=5),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 1
        row = result[0]
        assert row.status == DefectStatus.NOT_RECURRING
        assert row.num_weeks == 1
        assert row.total_qty == 5

    def test_all_zero_defect_records_excluded_from_results(
        self, service, mock_repository
    ):
        """Given DEF-005 with only qty_defects=0 records,
        it should not appear in results at all."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-005", "LOT-A", date(2026, 1, 6), qty_defects=0),
            _make_record("DEF-005", "LOT-B", date(2026, 1, 13), qty_defects=0),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 0


# ============================= AC4 =========================================
class TestAC4InsufficientData:
    """AC4: When is_data_complete is False for any record of a defect,
    the defect should be classified as Insufficient data."""

    def test_incomplete_data_yields_insufficient_status(self, service, mock_repository):
        """Given DEF-005 where one record has is_data_complete=False,
        status should be Insufficient data."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-005", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record(
                "DEF-005",
                "LOT-B",
                date(2026, 1, 13),
                qty_defects=2,
                is_data_complete=False,
            ),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 1
        assert result[0].status == DefectStatus.INSUFFICIENT_DATA

    def test_incomplete_data_overrides_recurring(self, service, mock_repository):
        """Even if a defect meets recurring criteria (>1 week, >1 lot),
        incomplete data should take precedence."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record(
                "DEF-006",
                "LOT-A",
                date(2026, 1, 6),
                qty_defects=3,
                is_data_complete=False,
            ),
            _make_record("DEF-006", "LOT-B", date(2026, 1, 13), qty_defects=2),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert result[0].status == DefectStatus.INSUFFICIENT_DATA


# ============================= AC5 =========================================
class TestAC5SummaryListFields:
    """AC5: Each row in the summary list must include the required fields."""

    def test_summary_row_has_all_required_fields(self, service, mock_repository):
        """The returned RecurringDefectRow should have: defect_code, status,
        num_weeks, num_lots, first_seen, last_seen, total_qty."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record("DEF-001", "LOT-B", date(2026, 1, 13), qty_defects=2),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert
        assert len(result) == 1
        row = result[0]
        assert row.defect_code == "DEF-001"
        assert row.status == DefectStatus.RECURRING
        assert row.num_weeks == 2
        assert row.num_lots == 2
        assert row.first_seen == date(2026, 1, 6)
        assert row.last_seen == date(2026, 1, 13)
        assert row.total_qty == 5


# ============================= AC7 =========================================
class TestAC7DrillDownDetail:
    """AC7: The drill-down view should show weekly breakdown and raw records."""

    def test_weekly_breakdown_groups_by_week(self, service, mock_repository):
        """Given records for DEF-001 across 3 weeks,
        get_defect_detail should return 3 WeeklyBreakdownRow objects."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 25)
        mock_repository.get_records_by_defect_code.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),  # week 2
            _make_record(
                "DEF-001", "LOT-B", date(2026, 1, 13), qty_defects=2
            ),  # week 3
            _make_record(
                "DEF-001", "LOT-A", date(2026, 1, 20), qty_defects=1
            ),  # week 4
        ]

        # Act
        weekly_rows, _ = service.get_defect_detail("DEF-001", start, end)

        # Assert
        assert len(weekly_rows) == 3
        assert weekly_rows[0].week_start == date(2026, 1, 5)  # Monday of ISO week 2
        assert weekly_rows[0].total_qty == 3
        assert weekly_rows[1].total_qty == 2
        assert weekly_rows[2].total_qty == 1

    def test_drill_down_returns_raw_inspection_records(self, service, mock_repository):
        """The second element of the tuple should contain InspectionDetail
        objects matching the underlying records."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_defect_code.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record("DEF-001", "LOT-B", date(2026, 1, 13), qty_defects=2),
        ]

        # Act
        _, details = service.get_defect_detail("DEF-001", start, end)

        # Assert
        assert len(details) == 2
        assert details[0].lot_id == "LOT-A"
        assert details[0].defect_code == "DEF-001"
        assert details[0].qty_defects == 3
        assert details[1].lot_id == "LOT-B"

    def test_weekly_breakdown_excludes_zero_defect_records(
        self, service, mock_repository
    ):
        """Zero-defect records should not appear in the weekly breakdown (AC3)."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_defect_code.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=0),
            _make_record("DEF-001", "LOT-B", date(2026, 1, 13), qty_defects=2),
        ]

        # Act
        weekly_rows, details = service.get_defect_detail("DEF-001", start, end)

        # Assert — only 1 week in breakdown (week with qty > 0)
        assert len(weekly_rows) == 1
        assert weekly_rows[0].total_qty == 2
        # But raw details include all records
        assert len(details) == 2

    def test_weekly_breakdown_lists_lots_involved(self, service, mock_repository):
        """Each weekly row should list the lots that had defects that week."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 11)
        mock_repository.get_records_by_defect_code.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record("DEF-001", "LOT-B", date(2026, 1, 7), qty_defects=2),
        ]

        # Act
        weekly_rows, _ = service.get_defect_detail("DEF-001", start, end)

        # Assert
        assert len(weekly_rows) == 1
        assert sorted(weekly_rows[0].lots_involved) == ["LOT-A", "LOT-B"]
        assert weekly_rows[0].total_qty == 5


# ============================= AC8 =========================================
class TestAC8MissingPeriods:
    """AC8: When data is insufficient, the system should explain which
    periods are missing."""

    def test_missing_periods_identified(self, service, mock_repository):
        """Given incomplete data for a week,
        get_missing_periods should return MissingPeriod DTOs for that week."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_defect_code.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record(
                "DEF-001",
                "LOT-B",
                date(2026, 1, 13),
                qty_defects=2,
                is_data_complete=False,
            ),
        ]

        # Act
        missing = service.get_missing_periods("DEF-001", start, end)

        # Assert
        assert len(missing) == 1
        assert missing[0].period_start == date(2026, 1, 12)  # Monday of that week
        assert missing[0].period_end == date(2026, 1, 18)  # Sunday
        assert "Missing inspection records" in missing[0].reason

    def test_no_missing_periods_when_data_complete(self, service, mock_repository):
        """When all data is complete, get_missing_periods should return []."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_defect_code.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record("DEF-001", "LOT-B", date(2026, 1, 13), qty_defects=2),
        ]

        # Act
        missing = service.get_missing_periods("DEF-001", start, end)

        # Assert
        assert missing == []

    def test_consecutive_missing_weeks_merged(self, service, mock_repository):
        """Consecutive incomplete weeks should be merged into one period."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 25)
        mock_repository.get_records_by_defect_code.return_value = [
            _make_record("DEF-001", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record(
                "DEF-001",
                "LOT-B",
                date(2026, 1, 13),
                qty_defects=2,
                is_data_complete=False,
            ),
            _make_record(
                "DEF-001",
                "LOT-A",
                date(2026, 1, 20),
                qty_defects=1,
                is_data_complete=False,
            ),
        ]

        # Act
        missing = service.get_missing_periods("DEF-001", start, end)

        # Assert — two consecutive weeks merged into one period
        assert len(missing) == 1
        assert missing[0].period_start == date(2026, 1, 12)
        assert missing[0].period_end == date(2026, 1, 25)


# ============================= AC9 =========================================
class TestAC9DefaultSortOrder:
    """AC9: Default sort = Recurring first, then by # weeks desc,
    then # lots desc."""

    def test_recurring_defects_sorted_first(self, service, mock_repository):
        """Given a mix of Recurring, Not recurring, and Insufficient data
        defects, Recurring should appear at the top of the list."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 18)
        mock_repository.get_records_by_date_range.return_value = [
            # DEF-NOT: single lot → Not recurring
            _make_record("DEF-NOT", "LOT-A", date(2026, 1, 6), qty_defects=1),
            # DEF-REC: multiple weeks & lots → Recurring
            _make_record("DEF-REC", "LOT-A", date(2026, 1, 6), qty_defects=3),
            _make_record("DEF-REC", "LOT-B", date(2026, 1, 13), qty_defects=2),
            # DEF-INC: incomplete data → Insufficient data
            _make_record(
                "DEF-INC",
                "LOT-A",
                date(2026, 1, 6),
                qty_defects=1,
                is_data_complete=False,
            ),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert — Recurring first, then Not recurring, then Insufficient
        assert result[0].defect_code == "DEF-REC"
        assert result[0].status == DefectStatus.RECURRING
        assert result[1].status == DefectStatus.NOT_RECURRING
        assert result[2].status == DefectStatus.INSUFFICIENT_DATA

    def test_within_recurring_sorted_by_weeks_then_lots(self, service, mock_repository):
        """Given two Recurring defects — one with 3 weeks and one with 2 —
        the 3-week defect should come first."""
        # Arrange
        start = date(2026, 1, 5)
        end = date(2026, 1, 25)
        mock_repository.get_records_by_date_range.return_value = [
            # DEF-A: 2 weeks, 2 lots → Recurring
            _make_record("DEF-A", "LOT-A", date(2026, 1, 6), qty_defects=1),
            _make_record("DEF-A", "LOT-B", date(2026, 1, 13), qty_defects=1),
            # DEF-B: 3 weeks, 2 lots → Recurring (should sort first)
            _make_record("DEF-B", "LOT-A", date(2026, 1, 6), qty_defects=1),
            _make_record("DEF-B", "LOT-B", date(2026, 1, 13), qty_defects=1),
            _make_record("DEF-B", "LOT-C", date(2026, 1, 20), qty_defects=1),
        ]

        # Act
        result = service.get_recurring_defect_list(start, end)

        # Assert — DEF-B (3 weeks) before DEF-A (2 weeks)
        recurring = [r for r in result if r.status == DefectStatus.RECURRING]
        assert len(recurring) == 2
        assert recurring[0].defect_code == "DEF-B"
        assert recurring[0].num_weeks == 3
        assert recurring[1].defect_code == "DEF-A"
        assert recurring[1].num_weeks == 2
