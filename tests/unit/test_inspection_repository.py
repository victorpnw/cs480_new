"""
test_inspection_repository.py — Unit tests for the InspectionRepository.

These tests verify that the repository methods build the correct queries.
We use an **in-memory SQLite database** so tests run instantly without needing
a real PostgreSQL server.

Key concepts for beginners:
    In-memory SQLite:  ``sqlite:///:memory:`` creates a throwaway database that
                       lives only in RAM.  It vanishes when the test ends.
    Fixture scope:     ``scope="function"`` means each test gets a fresh
                       database — tests can't accidentally affect each other.
    ORM setup:         We call ``Base.metadata.create_all(engine)`` to create
                       the tables from our model definitions, then insert test
                       rows using a session.

Note:
    Because SQLite lacks some PostgreSQL-specific features (e.g., SERIAL),
    these tests focus on query *logic* (filtering, joining) rather than
    database-engine-specific behaviour.
"""

import pytest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models import Base, Defect, Lot, InspectionRecord
from src.repositories.inspection_repository import InspectionRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session():
    """Create a fresh in-memory SQLite database and return a session.

    Steps:
        1. Create an in-memory SQLite engine.
        2. Create all tables defined in ``models.py``.
        3. Open a session, yield it to the test, then close/clean up.

    Yields:
        A SQLAlchemy ``Session`` connected to the in-memory database.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def seeded_session(session):
    """Insert a small set of test data and return the session.

    Test data:
        - 2 defects: DEF-001, DEF-002
        - 2 lots: LOT-A, LOT-B
        - Several inspection records spanning multiple weeks

    Yields:
        The same session, now containing seed data.
    """
    defect1 = Defect(id=1, defect_code="DEF-001")
    defect2 = Defect(id=2, defect_code="DEF-002")
    lot_a = Lot(id=1, lot_id="LOT-A")
    lot_b = Lot(id=2, lot_id="LOT-B")

    session.add_all([defect1, defect2, lot_a, lot_b])
    session.flush()

    records = [
        # DEF-001 in LOT-A, week of Jan 5 2026
        InspectionRecord(
            inspection_id="IR-001",
            lot_fk=1,
            defect_fk=1,
            inspection_date=date(2026, 1, 6),
            qty_defects=3,
            is_data_complete=True,
        ),
        # DEF-001 in LOT-B, week of Jan 12 2026
        InspectionRecord(
            inspection_id="IR-002",
            lot_fk=2,
            defect_fk=1,
            inspection_date=date(2026, 1, 13),
            qty_defects=2,
            is_data_complete=True,
        ),
        # DEF-002 in LOT-A, week of Jan 5 2026
        InspectionRecord(
            inspection_id="IR-003",
            lot_fk=1,
            defect_fk=2,
            inspection_date=date(2026, 1, 7),
            qty_defects=1,
            is_data_complete=True,
        ),
        # DEF-001 in LOT-A, far future — Feb 2026
        InspectionRecord(
            inspection_id="IR-004",
            lot_fk=1,
            defect_fk=1,
            inspection_date=date(2026, 2, 10),
            qty_defects=5,
            is_data_complete=True,
        ),
    ]
    session.add_all(records)
    session.commit()
    yield session


@pytest.fixture
def repository(seeded_session):
    """Create a repository backed by the seeded in-memory database.

    Returns:
        An ``InspectionRepository`` instance.
    """
    return InspectionRepository(seeded_session)


# ---------------------------------------------------------------------------
# Tests — get_records_by_date_range
# ---------------------------------------------------------------------------


class TestGetRecordsByDateRange:
    """Tests for ``InspectionRepository.get_records_by_date_range``."""

    def test_returns_records_within_range(self, repository):
        """Records inside [start, end] should be included."""
        results = repository.get_records_by_date_range(
            date(2026, 1, 1), date(2026, 1, 31)
        )
        # Should get IR-001, IR-002, IR-003 (all in January)
        assert len(results) == 3
        inspection_ids = {r.inspection_id for r in results}
        assert inspection_ids == {"IR-001", "IR-002", "IR-003"}

    def test_excludes_records_outside_range(self, repository):
        """Records before start or after end should NOT be included."""
        results = repository.get_records_by_date_range(
            date(2026, 1, 1), date(2026, 1, 10)
        )
        # Only IR-001 (Jan 6) and IR-003 (Jan 7) fall in this range
        assert len(results) == 2
        inspection_ids = {r.inspection_id for r in results}
        assert inspection_ids == {"IR-001", "IR-003"}

    def test_empty_range_returns_empty_list(self, repository):
        """A date range with no matching records should return []."""
        results = repository.get_records_by_date_range(
            date(2025, 1, 1), date(2025, 1, 31)
        )
        assert results == []

    def test_eagerly_loads_lot_and_defect(self, repository):
        """Related Lot and Defect objects should be accessible."""
        results = repository.get_records_by_date_range(
            date(2026, 1, 6), date(2026, 1, 6)
        )
        assert len(results) == 1
        record = results[0]
        assert record.lot.lot_id == "LOT-A"
        assert record.defect.defect_code == "DEF-001"

    def test_inclusive_boundaries(self, repository):
        """Both start_date and end_date should be inclusive."""
        results = repository.get_records_by_date_range(
            date(2026, 1, 6), date(2026, 1, 7)
        )
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Tests — get_records_by_defect_code
# ---------------------------------------------------------------------------


class TestGetRecordsByDefectCode:
    """Tests for ``InspectionRepository.get_records_by_defect_code``."""

    def test_returns_only_matching_defect_code(self, repository):
        """Only records for the requested defect_code should be returned."""
        results = repository.get_records_by_defect_code(
            "DEF-001", date(2026, 1, 1), date(2026, 1, 31)
        )
        assert len(results) == 2
        assert all(r.defect.defect_code == "DEF-001" for r in results)

    def test_no_match_returns_empty_list(self, repository):
        """A defect_code with no records should return []."""
        results = repository.get_records_by_defect_code(
            "DEF-999", date(2026, 1, 1), date(2026, 12, 31)
        )
        assert results == []

    def test_respects_date_range(self, repository):
        """Records outside the date range should be excluded even if defect matches."""
        results = repository.get_records_by_defect_code(
            "DEF-001", date(2026, 1, 1), date(2026, 1, 10)
        )
        # Only IR-001 (Jan 6) — IR-002 (Jan 13) is outside this range
        assert len(results) == 1
        assert results[0].inspection_id == "IR-001"
