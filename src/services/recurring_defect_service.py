"""
recurring_defect_service.py — Business logic for recurring defect analysis.

This is the "brain" of the feature.  It takes raw inspection records from the
repository, applies the acceptance-criteria rules (AC1–AC4), and returns
structured DTOs that the UI can display directly.

Key concepts for beginners:
    Service layer:  Sits between the UI and the repository.  It contains the
                    *rules* ("is this defect recurring?") but does NOT know
                    how to render HTML or run SQL — those jobs belong to the
                    UI layer and repository layer respectively.
    Dependency Injection:  Instead of creating its own repository, this class
                           *receives* one through its constructor.  This makes
                           testing easy — in tests you can pass a fake repo.

Acceptance Criteria mapping:
    AC1 → ``classify_defects``  (recurring = >1 week AND >1 lot)
    AC2 → ``classify_defects``  (single-lot → not recurring)
    AC3 → ``classify_defects``  (skip records with qty_defects == 0)
    AC4 → ``classify_defects``  (incomplete data → insufficient data)
    AC5 → ``get_recurring_defect_list``  (builds the summary table rows)
    AC7 → ``get_defect_detail``  (weekly breakdown + raw records)
    AC8 → ``get_missing_periods``  (identifies data gaps)
    AC9 → ``get_recurring_defect_list``  (default sort order)
"""

from collections import defaultdict
from datetime import date, timedelta

from src.repositories.inspection_repository import InspectionRepository
from src.schemas import (
    DefectStatus,
    RecurringDefectRow,
    WeeklyBreakdownRow,
    InspectionDetail,
    MissingPeriod,
)


class RecurringDefectService:
    """Analyses inspection data to classify defects as recurring or not.

    Usage::

        service = RecurringDefectService(repo)
        rows = service.get_recurring_defect_list(start, end)

    Args:
        repository: An ``InspectionRepository`` instance for data access.
    """

    def __init__(self, repository: InspectionRepository):
        self._repository = repository

    # ------------------------------------------------------------------
    # AC1–AC4, AC5, AC9 — Summary list
    # ------------------------------------------------------------------
    def get_recurring_defect_list(
        self, start_date: date, end_date: date
    ) -> list[RecurringDefectRow]:
        """Build the Recurring Defects summary table (AC5) with default sort (AC9).

        Steps (to be implemented):
            1. Fetch all inspection records in the date range from the repo.
            2. Group records by defect_code.
            3. For each defect_code, apply classification rules:
               - Exclude records where qty_defects == 0 (AC3).
               - If any record has is_data_complete == False → INSUFFICIENT_DATA (AC4).
               - If distinct calendar weeks > 1 AND distinct lots > 1 → RECURRING (AC1).
               - Otherwise → NOT_RECURRING (AC2).
            4. Compute aggregate fields: num_weeks, num_lots, first_seen,
               last_seen, total_qty.
            5. Sort: Recurring first, then by num_weeks desc, then num_lots
               desc (AC9).

        Args:
            start_date: Start of the user-selected date range (inclusive).
            end_date:   End of the user-selected date range (inclusive).

        Returns:
            A list of ``RecurringDefectRow`` DTOs, one per defect_code, sorted
            per AC9.
        """
        # 1. Fetch all inspection records in the date range.
        records = self._repository.get_records_by_date_range(start_date, end_date)

        # 2. Group records by defect_code.
        groups = defaultdict(list)
        for record in records:
            groups[record.defect.defect_code].append(record)

        # 3–4. Classify each defect and compute aggregates.
        rows: list[RecurringDefectRow] = []
        for defect_code, group in groups.items():
            # AC4: if any record has incomplete data → INSUFFICIENT_DATA
            has_incomplete = any(not r.is_data_complete for r in group)

            # AC3: exclude records with qty_defects == 0 for classification
            meaningful = [r for r in group if r.qty_defects > 0]

            if not meaningful:
                continue

            distinct_weeks = {r.inspection_date.isocalendar()[:2] for r in meaningful}
            distinct_lots = {r.lot.lot_id for r in meaningful}

            if has_incomplete:
                status = DefectStatus.INSUFFICIENT_DATA
            elif len(distinct_weeks) > 1 and len(distinct_lots) > 1:
                status = DefectStatus.RECURRING
            else:
                status = DefectStatus.NOT_RECURRING

            rows.append(RecurringDefectRow(
                defect_code=defect_code,
                status=status,
                num_weeks=len(distinct_weeks),
                num_lots=len(distinct_lots),
                first_seen=min(r.inspection_date for r in meaningful),
                last_seen=max(r.inspection_date for r in meaningful),
                total_qty=sum(r.qty_defects for r in meaningful),
            ))

        # 5. AC9: sort — Recurring first, then by num_weeks desc, num_lots desc.
        status_order = {
            DefectStatus.RECURRING: 0,
            DefectStatus.NOT_RECURRING: 1,
            DefectStatus.INSUFFICIENT_DATA: 2,
        }
        rows.sort(key=lambda r: (status_order[r.status], -r.num_weeks, -r.num_lots))

        return rows

    # ------------------------------------------------------------------
    # AC7 — Drill-down: weekly breakdown
    # ------------------------------------------------------------------
    def get_defect_detail(
        self, defect_code: str, start_date: date, end_date: date
    ) -> tuple[list[WeeklyBreakdownRow], list[InspectionDetail]]:
        """Build the drill-down view for a single defect code (AC7).

        Returns two collections:
            1. A weekly breakdown — one row per calendar week showing which
               lots were involved and the total qty that week.
            2. The underlying raw inspection records.

        Args:
            defect_code: The defect to drill into (e.g., 'DEF-001').
            start_date:  Start of the date range (inclusive).
            end_date:    End of the date range (inclusive).

        Returns:
            A tuple of (weekly_rows, inspection_details).
        """
        # TODO: implement
        pass

    # ------------------------------------------------------------------
    # AC8 — Identify missing data periods
    # ------------------------------------------------------------------
    def get_missing_periods(
        self, defect_code: str, start_date: date, end_date: date
    ) -> list[MissingPeriod]:
        """Identify time periods with incomplete data for a defect (AC8).

        When a defect is classified as "Insufficient data" (AC4), this method
        explains *which* weeks are missing and why.

        Args:
            defect_code: The defect to check.
            start_date:  Start of the date range (inclusive).
            end_date:    End of the date range (inclusive).

        Returns:
            A list of ``MissingPeriod`` DTOs describing each gap.  Returns an
            empty list if data is complete.
        """
        # TODO: implement
        pass
