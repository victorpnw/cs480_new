"""
recurring_defect_service.py - Business logic for recurring defect analysis.

This is the service layer for recurring-defect calculations. It takes raw
inspection records from the repository, applies classification rules, and
returns DTOs for the UI layer.
"""

from collections import defaultdict
from datetime import date, timedelta
import logging

from src.repositories.inspection_repository import InspectionRepository
from src.schemas import (
    DefectStatus,
    InspectionDetail,
    MissingPeriod,
    RecurringDefectRow,
    WeeklyBreakdownRow,
)

LOGGER = logging.getLogger(__name__)


class RecurringDefectService:
    """Analyses inspection data to classify defects as recurring or not."""

    def __init__(self, repository: InspectionRepository):
        self._repository = repository

    def get_recurring_defect_list(
        self, start_date: date, end_date: date
    ) -> list[RecurringDefectRow]:
        """Build the recurring-defects summary list."""
        LOGGER.info(
            "Recurring defect analysis started. start_date=%s end_date=%s",
            start_date,
            end_date,
        )
        try:
            records = self._repository.get_records_by_date_range(start_date, end_date)
            LOGGER.info(
                "Inspection records loaded for analysis. number_of_inspections=%s",
                len(records),
            )

            groups: dict[str, list] = defaultdict(list)
            for record in records:
                groups[record.defect.defect_code].append(record)

            rows: list[RecurringDefectRow] = []
            for defect_code, group in groups.items():
                has_incomplete = any(not r.is_data_complete for r in group)
                meaningful = [r for r in group if r.qty_defects > 0]
                if not meaningful:
                    continue

                distinct_weeks = {
                    r.inspection_date.isocalendar()[:2] for r in meaningful
                }
                distinct_lots = {r.lot.lot_id for r in meaningful}
                number_of_defects_detected = sum(r.qty_defects for r in meaningful)

                if has_incomplete:
                    LOGGER.warning(
                        "Missing inspection data detected during classification. "
                        "defect_type=%s number_of_inspections=%s",
                        defect_code,
                        len(group),
                    )

                if len(distinct_weeks) >= 4 and len(distinct_lots) == 1:
                    LOGGER.warning(
                        "Suspicious defect pattern detected. defect_type=%s "
                        "number_of_inspections=%s number_of_defects_detected=%s",
                        defect_code,
                        len(group),
                        number_of_defects_detected,
                    )

                if has_incomplete:
                    status = DefectStatus.INSUFFICIENT_DATA
                elif len(distinct_weeks) > 1 and len(distinct_lots) > 1:
                    status = DefectStatus.RECURRING
                else:
                    status = DefectStatus.NOT_RECURRING

                rows.append(
                    RecurringDefectRow(
                        defect_code=defect_code,
                        status=status,
                        num_weeks=len(distinct_weeks),
                        num_lots=len(distinct_lots),
                        first_seen=min(r.inspection_date for r in meaningful),
                        last_seen=max(r.inspection_date for r in meaningful),
                        total_qty=number_of_defects_detected,
                    )
                )

            status_order = {
                DefectStatus.RECURRING: 0,
                DefectStatus.NOT_RECURRING: 1,
                DefectStatus.INSUFFICIENT_DATA: 2,
            }
            rows.sort(key=lambda r: (status_order[r.status], -r.num_weeks, -r.num_lots))

            recurring_count = sum(
                1 for row in rows if row.status == DefectStatus.RECURRING
            )
            LOGGER.info(
                "Recurring defect analysis complete. number_of_defects_detected=%s "
                "number_of_summary_rows=%s",
                recurring_count,
                len(rows),
            )
            return rows
        except (TypeError, ValueError):
            LOGGER.exception(
                "Data parsing error during recurring defect analysis. "
                "start_date=%s end_date=%s",
                start_date,
                end_date,
            )
            raise
        except Exception:
            LOGGER.exception(
                "Unexpected exception during recurring defect analysis. "
                "start_date=%s end_date=%s",
                start_date,
                end_date,
            )
            raise

    def get_defect_detail(
        self, defect_code: str, start_date: date, end_date: date
    ) -> tuple[list[WeeklyBreakdownRow], list[InspectionDetail]]:
        """Build weekly breakdown and underlying inspection details for one defect."""
        LOGGER.info(
            "Defect drill-down started. defect_type=%s start_date=%s end_date=%s",
            defect_code,
            start_date,
            end_date,
        )
        try:
            records = self._repository.get_records_by_defect_code(
                defect_code, start_date, end_date
            )
            LOGGER.info(
                "Defect drill-down records loaded. defect_type=%s "
                "number_of_inspections=%s",
                defect_code,
                len(records),
            )

            inspection_details = [
                InspectionDetail(
                    lot_id=r.lot.lot_id,
                    inspection_date=r.inspection_date,
                    defect_code=r.defect.defect_code,
                    qty_defects=r.qty_defects,
                )
                for r in records
            ]

            meaningful = [r for r in records if r.qty_defects > 0]
            weeks: dict[tuple[int, int], list] = defaultdict(list)
            for r in meaningful:
                iso = r.inspection_date.isocalendar()
                weeks[(iso[0], iso[1])].append(r)

            weekly_rows = []
            for (iso_year, iso_week), week_records in sorted(weeks.items()):
                week_start = date.fromisocalendar(iso_year, iso_week, 1)
                week_end = week_start + timedelta(days=6)
                lots_involved = sorted({r.lot.lot_id for r in week_records})
                total_qty = sum(r.qty_defects for r in week_records)
                weekly_rows.append(
                    WeeklyBreakdownRow(
                        week_start=week_start,
                        week_end=week_end,
                        lots_involved=lots_involved,
                        total_qty=total_qty,
                    )
                )

            LOGGER.info(
                "Defect drill-down complete. defect_type=%s number_of_inspections=%s "
                "number_of_defects_detected=%s",
                defect_code,
                len(inspection_details),
                sum(detail.qty_defects for detail in inspection_details),
            )
            return (weekly_rows, inspection_details)
        except (TypeError, ValueError):
            LOGGER.exception(
                "Data parsing error during defect drill-down. defect_type=%s "
                "start_date=%s end_date=%s",
                defect_code,
                start_date,
                end_date,
            )
            raise
        except Exception:
            LOGGER.exception(
                "Unexpected exception during defect drill-down. defect_type=%s "
                "start_date=%s end_date=%s",
                defect_code,
                start_date,
                end_date,
            )
            raise

    def get_missing_periods(
        self, defect_code: str, start_date: date, end_date: date
    ) -> list[MissingPeriod]:
        """Identify missing/incomplete data periods for one defect."""
        LOGGER.info(
            "Missing-period analysis started. defect_type=%s start_date=%s end_date=%s",
            defect_code,
            start_date,
            end_date,
        )
        try:
            records = self._repository.get_records_by_defect_code(
                defect_code, start_date, end_date
            )

            incomplete = [r for r in records if not r.is_data_complete]
            if not incomplete:
                return []

            LOGGER.warning(
                "Missing inspection data found. defect_type=%s number_of_inspections=%s",
                defect_code,
                len(incomplete),
            )

            weeks: dict[tuple[int, int], list] = defaultdict(list)
            for r in incomplete:
                iso = r.inspection_date.isocalendar()
                weeks[(iso[0], iso[1])].append(r)

            missing_periods = []
            for iso_year, iso_week in sorted(weeks.keys()):
                period_start = date.fromisocalendar(iso_year, iso_week, 1)
                period_end = period_start + timedelta(days=6)
                reason = (
                    f"Missing inspection records for week of "
                    f"{period_start.isoformat()} to {period_end.isoformat()}"
                )
                missing_periods.append(
                    MissingPeriod(
                        period_start=period_start,
                        period_end=period_end,
                        reason=reason,
                    )
                )

            if len(missing_periods) > 1:
                merged = [missing_periods[0]]
                for mp in missing_periods[1:]:
                    prev = merged[-1]
                    if mp.period_start <= prev.period_end + timedelta(days=1):
                        merged[-1] = MissingPeriod(
                            period_start=prev.period_start,
                            period_end=mp.period_end,
                            reason=(
                                f"Missing inspection records for weeks of "
                                f"{prev.period_start.isoformat()} to {mp.period_end.isoformat()}"
                            ),
                        )
                    else:
                        merged.append(mp)
                missing_periods = merged

            LOGGER.info(
                "Missing-period analysis complete. defect_type=%s number_of_periods=%s",
                defect_code,
                len(missing_periods),
            )
            return missing_periods
        except (TypeError, ValueError):
            LOGGER.exception(
                "Data parsing error during missing-period analysis. defect_type=%s "
                "start_date=%s end_date=%s",
                defect_code,
                start_date,
                end_date,
            )
            raise
        except Exception:
            LOGGER.exception(
                "Unexpected exception during missing-period analysis. defect_type=%s "
                "start_date=%s end_date=%s",
                defect_code,
                start_date,
                end_date,
            )
            raise
