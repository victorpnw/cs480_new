"""Integration tests for repository + service against a real database.

This file is intentionally more verbose for learning:
    - Unit tests prove isolated logic with mocks.
    - These tests prove the wiring between layers and SQL behavior.
    - We avoid browser/UI concerns here (those belong to E2E tests).

Test style:
    Most tests follow Arrange -> Act -> Assert.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import Defect, InspectionRecord
from src.schemas import DefectStatus


pytestmark = pytest.mark.integration


def _date_bounds(session: Session) -> tuple[date, date]:
    """Return the available inspection date window from the real DB.

    We use the full date window so tests are resilient even when sample data
    changes over time.
    """
    start_date, end_date = session.query(
        func.min(InspectionRecord.inspection_date),
        func.max(InspectionRecord.inspection_date),
    ).one()
    if start_date is None or end_date is None:
        pytest.skip("inspection_records is empty; skipping integration assertions.")
    return start_date, end_date


def _status_order(status: DefectStatus) -> int:
    """Map enum values to the expected AC9 sort priority."""
    return {
        DefectStatus.RECURRING: 0,
        DefectStatus.NOT_RECURRING: 1,
        DefectStatus.INSUFFICIENT_DATA: 2,
    }[status]


def _top_defect_code(session: Session) -> str | None:
    """Pick one stable defect code for detail-oriented tests.

    Why this helper:
        Some tests need "a defect that definitely exists."
        We choose the defect with most records so we are less likely to pick
        an edge case with no useful data.
    """
    row = (
        session.query(Defect.defect_code, func.count(InspectionRecord.id).label("cnt"))
        .join(InspectionRecord, InspectionRecord.defect_fk == Defect.id)
        .group_by(Defect.defect_code)
        # Tie-break by defect_code to keep selection deterministic.
        .order_by(func.count(InspectionRecord.id).desc(), Defect.defect_code.asc())
        .first()
    )
    return row[0] if row else None


def test_repository_date_range_matches_direct_count(repository, db_session: Session):
    """Repository range query should match a direct ORM count.

    This validates that:
        1. date-range filtering is correct (inclusive boundaries)
        2. repository returns the same record volume as a baseline query
        3. joined relationships (lot + defect) are available on returned rows
    """
    # Arrange: use the full available date window from DB.
    start_date, end_date = _date_bounds(db_session)

    # Baseline query that does not use repository code.
    expected_count = (
        db_session.query(func.count(InspectionRecord.id))
        .filter(
            InspectionRecord.inspection_date >= start_date,
            InspectionRecord.inspection_date <= end_date,
        )
        .scalar()
    )

    # Act: call repository method under test.
    records = repository.get_records_by_date_range(start_date, end_date)

    # Assert: repository result matches baseline count and boundaries.
    assert len(records) == expected_count
    assert records
    assert all(start_date <= record.inspection_date <= end_date for record in records)

    # joinedload() in repository should make related objects immediately usable.
    sample = records[0]
    assert sample.lot.lot_id
    assert sample.defect.defect_code


def test_repository_defect_lookup_matches_direct_query(repository, db_session: Session):
    """Defect lookup should return the same IDs as a direct baseline query.

    We compare exact inspection IDs (set equality), not just row counts, to
    catch subtle filtering/join mistakes.
    """
    # Arrange: choose a defect that exists and query the full date window.
    start_date, end_date = _date_bounds(db_session)

    top_defect_code = _top_defect_code(db_session)
    if not top_defect_code:
        pytest.skip("No defect rows found; skipping integration assertions.")

    # Build expected result directly via ORM query (independent baseline).
    expected_ids = {
        record.inspection_id
        for record in (
            db_session.query(InspectionRecord)
            .join(InspectionRecord.defect)
            .filter(
                Defect.defect_code == top_defect_code,
                InspectionRecord.inspection_date >= start_date,
                InspectionRecord.inspection_date <= end_date,
            )
            .all()
        )
    }

    # Act: call repository method under test.
    records = repository.get_records_by_defect_code(
        top_defect_code, start_date, end_date
    )
    actual_ids = {record.inspection_id for record in records}

    # Assert: exact same record identity set.
    assert actual_ids == expected_ids
    assert all(record.defect.defect_code == top_defect_code for record in records)


def test_service_summary_rows_match_repository_aggregates(
    service, repository, db_session
):
    """Service summary rows should match raw repository-derived aggregates.

    This is a true integration check for business logic with real DB data:
        Service classification + aggregation output is validated against
        hand-computed expectations from repository records.
    """
    # Arrange: run against the available DB date span.
    start_date, end_date = _date_bounds(db_session)

    # Act: summary output from business service.
    rows = service.get_recurring_defect_list(start_date, end_date)

    # Assert basic sanity:
    # - at least one row exists
    # - each defect code appears once
    # - rows are sorted by AC9 status precedence
    assert rows
    assert len(rows) == len({row.defect_code for row in rows})
    assert [_status_order(r.status) for r in rows] == sorted(
        _status_order(r.status) for r in rows
    )

    # Assert each row's fields by recomputing from repository records.
    for row in rows:
        # Pull raw records for this defect from repository layer.
        records = repository.get_records_by_defect_code(
            row.defect_code, start_date, end_date
        )

        # AC3: only qty_defects > 0 counts toward classification stats.
        meaningful = [record for record in records if record.qty_defects > 0]
        assert meaningful

        # Rebuild expected aggregate pieces.
        weeks = {record.inspection_date.isocalendar()[:2] for record in meaningful}
        lots = {record.lot.lot_id for record in meaningful}
        has_incomplete = any(not record.is_data_complete for record in records)

        # Recompute expected status using same AC rules explicitly.
        if has_incomplete:
            expected_status = DefectStatus.INSUFFICIENT_DATA
        elif len(weeks) > 1 and len(lots) > 1:
            expected_status = DefectStatus.RECURRING
        else:
            expected_status = DefectStatus.NOT_RECURRING

        # Final field-by-field equality checks.
        assert row.status == expected_status
        assert row.num_weeks == len(weeks)
        assert row.num_lots == len(lots)
        assert row.first_seen == min(record.inspection_date for record in meaningful)
        assert row.last_seen == max(record.inspection_date for record in meaningful)
        assert row.total_qty == sum(record.qty_defects for record in meaningful)


def test_service_detail_and_missing_periods_are_consistent(
    service, repository, db_session
):
    """Drill-down and missing-period outputs should match raw records.

    Validates two service methods together:
        - get_defect_detail()
        - get_missing_periods()
    """
    # Arrange: choose a defect that definitely has records.
    start_date, end_date = _date_bounds(db_session)

    defect_code = _top_defect_code(db_session)
    if not defect_code:
        pytest.skip("No defects found for integration detail test.")

    # Raw records from repository become our baseline.
    records = repository.get_records_by_defect_code(defect_code, start_date, end_date)

    # Act: request both detail outputs from service.
    weekly_rows, details = service.get_defect_detail(defect_code, start_date, end_date)

    # Assert raw detail list mirrors repository record count and defect code.
    assert len(details) == len(records)
    assert all(detail.defect_code == defect_code for detail in details)

    # Rebuild expected weekly buckets from raw records (qty > 0 only).
    meaningful = [record for record in records if record.qty_defects > 0]
    expected_by_week: dict[tuple[int, int], dict[str, set[str] | int]] = {}
    for record in meaningful:
        iso_year, iso_week, _ = record.inspection_date.isocalendar()
        bucket = expected_by_week.setdefault(
            (iso_year, iso_week), {"lots": set(), "qty": 0}
        )
        lots = bucket["lots"]
        assert isinstance(lots, set)
        lots.add(record.lot.lot_id)
        bucket["qty"] = int(bucket["qty"]) + record.qty_defects

    # Weekly row count and total quantities should match bucket rebuild.
    assert len(weekly_rows) == len(expected_by_week)
    assert sum(row.total_qty for row in weekly_rows) == sum(
        record.qty_defects for record in meaningful
    )

    # Each weekly row should represent a full ISO week and matching lot/qty data.
    for row in weekly_rows:
        # Monday = 0, so week_start should be Monday.
        assert row.week_start.weekday() == 0
        assert row.week_end == row.week_start + timedelta(days=6)
        iso_key = row.week_start.isocalendar()[:2]
        bucket = expected_by_week[iso_key]
        assert set(row.lots_involved) == bucket["lots"]
        assert row.total_qty == bucket["qty"]

    # AC8 path: verify missing-period logic only when incomplete records exist.
    incomplete = [record for record in records if not record.is_data_complete]
    missing_periods = service.get_missing_periods(defect_code, start_date, end_date)
    if not incomplete:
        assert missing_periods == []
        return

    # Build expected missing week ranges from raw incomplete records.
    weeks = sorted({record.inspection_date.isocalendar()[:2] for record in incomplete})
    week_ranges: list[tuple[date, date]] = []
    for iso_year, iso_week in weeks:
        week_start = date.fromisocalendar(iso_year, iso_week, 1)
        week_end = week_start + timedelta(days=6)
        week_ranges.append((week_start, week_end))

    # Merge consecutive weeks to match service behavior.
    merged: list[tuple[date, date]] = []
    for week_start, week_end in week_ranges:
        if not merged or week_start > merged[-1][1] + timedelta(days=1):
            merged.append((week_start, week_end))
        else:
            merged[-1] = (merged[-1][0], week_end)

    # Final equality: service output periods must match merged expectation.
    assert [
        (period.period_start, period.period_end) for period in missing_periods
    ] == merged
