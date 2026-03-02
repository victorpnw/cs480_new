"""
inspection_repository.py — Data Access Layer for inspection records.

This module is the *only* place that touches the database for inspection-related
queries.  The service layer calls these functions; the UI layer never calls them
directly.  This separation means you can swap the database or change a query
without touching business logic or UI code.

Key concepts for beginners:
    Repository pattern:  A class whose sole job is to run database queries and
                         return results.  It hides SQL details from the rest of
                         the application.
    Session:             A SQLAlchemy session (see ``database.py``) that you
                         pass in so the repository can execute queries.

All methods return ORM model instances or simple Python values — *not* DTOs.
The service layer is responsible for converting these into DTOs.
"""

from datetime import date
from sqlalchemy.orm import Session

from src.models import InspectionRecord


class InspectionRepository:
    """Provides database queries for inspection records.

    Usage::

        repo = InspectionRepository(session)
        records = repo.get_records_by_date_range(start, end)

    Args:
        session: An active SQLAlchemy ``Session`` obtained from
                 ``database.get_session()``.
    """

    def __init__(self, session: Session):
        self._session = session

    def get_records_by_date_range(
        self, start_date: date, end_date: date
    ) -> list[InspectionRecord]:
        """Return all inspection records within a date range (inclusive).

        Used by the service layer to gather the raw data needed for defect
        classification (AC1–AC4) and the list view (AC5).

        Args:
            start_date: First date to include (inclusive).
            end_date:   Last date to include (inclusive).

        Returns:
            A list of ``InspectionRecord`` ORM objects with their related
            ``Lot`` and ``Defect`` eagerly loaded.
        """
        # TODO: implement — query inspection_records filtered by date range,
        #       eagerly load related lot and defect objects.
        return []

    def get_records_by_defect_code(
        self, defect_code: str, start_date: date, end_date: date
    ) -> list[InspectionRecord]:
        """Return inspection records for one defect code within a date range.

        Used by the service layer to build the drill-down detail view (AC7).

        Args:
            defect_code: The defect's business key (e.g., 'DEF-001').
            start_date:  First date to include (inclusive).
            end_date:    Last date to include (inclusive).

        Returns:
            A list of ``InspectionRecord`` ORM objects for the given defect.
        """
        # TODO: implement — query inspection_records joined with defects,
        #       filtered by defect_code and date range.
        return []
