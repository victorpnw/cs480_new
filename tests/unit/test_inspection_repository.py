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

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models import Base
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
    # TODO: insert test defects, lots, and inspection_records into the session
    #       then session.commit()
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

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_returns_records_within_range(self, repository):
        """Records inside [start, end] should be included."""
        # Arrange / Act / Assert
        # TODO: implement
        pass

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_excludes_records_outside_range(self, repository):
        """Records before start or after end should NOT be included."""
        # Arrange / Act / Assert
        # TODO: implement
        pass

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_empty_range_returns_empty_list(self, repository):
        """A date range with no matching records should return []."""
        # Arrange / Act / Assert
        # TODO: implement
        pass


# ---------------------------------------------------------------------------
# Tests — get_records_by_defect_code
# ---------------------------------------------------------------------------


class TestGetRecordsByDefectCode:
    """Tests for ``InspectionRepository.get_records_by_defect_code``."""

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_returns_only_matching_defect_code(self, repository):
        """Only records for the requested defect_code should be returned."""
        # Arrange / Act / Assert
        # TODO: implement
        pass

    @pytest.mark.skip(reason="Test not implemented yet")
    def test_no_match_returns_empty_list(self, repository):
        """A defect_code with no records should return []."""
        # Arrange / Act / Assert
        # TODO: implement
        pass
