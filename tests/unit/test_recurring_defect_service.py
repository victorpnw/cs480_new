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

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_defect_in_multiple_weeks_but_single_lot_is_not_recurring(
        self, service, mock_repository
    ):
        """Given DEF-002 in LOT-A in both week 1 and week 2 (same lot),
        it should NOT be recurring — AC1 requires >1 lot."""
        # Arrange / Act / Assert
        # TODO: implement
        pass


# ============================= AC2 =========================================
class TestAC2SingleLotNotRecurring:
    """AC2: A defect that only appears within a single lot should NOT be
    classified as recurring, even if it has multiple records."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_single_lot_multiple_records_not_recurring(self, service, mock_repository):
        """Given DEF-003 with 3 records all in LOT-A,
        status should be Not recurring."""
        # Arrange / Act / Assert
        # TODO: implement
        pass


# ============================= AC3 =========================================
class TestAC3ZeroDefectsExcluded:
    """AC3: Records with qty_defects == 0 should not count as an occurrence."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_zero_defect_records_are_ignored(self, service, mock_repository):
        """Given DEF-004 with qty_defects=0 in week 1 and qty_defects=5 in
        week 2, only week 2 should count → only 1 week → Not recurring."""
        # Arrange / Act / Assert
        # TODO: implement
        pass


# ============================= AC4 =========================================
class TestAC4InsufficientData:
    """AC4: When is_data_complete is False for any record of a defect,
    the defect should be classified as Insufficient data."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_incomplete_data_yields_insufficient_status(self, service, mock_repository):
        """Given DEF-005 where one record has is_data_complete=False,
        status should be Insufficient data."""
        # Arrange / Act / Assert
        # TODO: implement
        pass


# ============================= AC5 =========================================
class TestAC5SummaryListFields:
    """AC5: Each row in the summary list must include the required fields."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_summary_row_has_all_required_fields(self, service, mock_repository):
        """The returned RecurringDefectRow should have: defect_code, status,
        num_weeks, num_lots, first_seen, last_seen, total_qty."""
        # Arrange / Act / Assert
        # TODO: implement — check that all dataclass fields are populated
        pass


# ============================= AC7 =========================================
class TestAC7DrillDownDetail:
    """AC7: The drill-down view should show weekly breakdown and raw records."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_weekly_breakdown_groups_by_week(self, service, mock_repository):
        """Given records for DEF-001 across 3 weeks,
        get_defect_detail should return 3 WeeklyBreakdownRow objects."""
        # Arrange / Act / Assert
        # TODO: implement
        pass

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_drill_down_returns_raw_inspection_records(self, service, mock_repository):
        """The second element of the tuple should contain InspectionDetail
        objects matching the underlying records."""
        # Arrange / Act / Assert
        # TODO: implement
        pass


# ============================= AC8 =========================================
class TestAC8MissingPeriods:
    """AC8: When data is insufficient, the system should explain which
    periods are missing."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_missing_periods_identified(self, service, mock_repository):
        """Given incomplete data for weeks 2–3,
        get_missing_periods should return MissingPeriod DTOs for those weeks."""
        # Arrange / Act / Assert
        # TODO: implement
        pass


# ============================= AC9 =========================================
class TestAC9DefaultSortOrder:
    """AC9: Default sort = Recurring first, then by # weeks desc,
    then # lots desc."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_recurring_defects_sorted_first(self, service, mock_repository):
        """Given a mix of Recurring, Not recurring, and Insufficient data
        defects, Recurring should appear at the top of the list."""
        # Arrange / Act / Assert
        # TODO: implement
        pass

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_within_recurring_sorted_by_weeks_then_lots(self, service, mock_repository):
        """Given two Recurring defects — one with 5 weeks and one with 3 —
        the 5-week defect should come first."""
        # Arrange / Act / Assert
        # TODO: implement
        pass
