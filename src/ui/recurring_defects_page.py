"""
recurring_defects_page.py — Streamlit UI for the Recurring Defects view.

This is the presentation layer.  It draws the web interface and calls the
service layer for data.  It should contain *no* business logic — all rules
live in ``recurring_defect_service.py``.

Key concepts for beginners:
    Streamlit:  A Python library that turns a plain script into an interactive
                web page.  You call functions like ``st.title()`` and
                ``st.dataframe()`` and Streamlit renders them in the browser.
    Page layout: Streamlit runs your script top-to-bottom every time the user
                 interacts with a widget (button click, slider change, etc.).

How to run this page locally:
    poetry run streamlit run src/ui/recurring_defects_page.py

Acceptance Criteria covered here:
    AC5 — List/table view with required fields
    AC6 — Visual highlight and filter for recurring defects
    AC7 — Drill-down detail view (triggered by selecting a row)
    AC8 — Insufficient data messaging
    AC9 — Default sorting (handled by the service, displayed here)
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add the project root to sys.path so "src" is importable when Streamlit
# runs this file directly (e.g., `streamlit run src/ui/recurring_defects_page.py`).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from src.database import get_session
from src.repositories.inspection_repository import InspectionRepository
from src.services.recurring_defect_service import RecurringDefectService
from src.schemas import DefectStatus


def render_date_range_selector():
    """Display start-date and end-date inputs and return the selected range.

    The user picks a date range that scopes all queries on this page.

    Returns:
        A tuple of (start_date, end_date) as ``datetime.date`` objects.
    """
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start date",
            value=date.today() - timedelta(days=90),
        )
    with col2:
        end_date = st.date_input(
            "End date",
            value=date.today(),
        )
    return start_date, end_date


def render_recurring_filter():
    """Display a checkbox/toggle to filter the table to Recurring-only (AC6).

    Returns:
        ``True`` if the user wants to see only Recurring defects.
    """
    return st.checkbox("Show only Recurring defects", value=False)


def render_defect_summary_table(rows):
    """Render the Recurring Defects summary table (AC5, AC9).

    Each row shows: Defect Code, Status (with a visual badge for Recurring
    per AC6), # weeks, # lots, first seen, last seen, total qty.

    Args:
        rows: A list of ``RecurringDefectRow`` DTOs from the service layer.

    Returns:
        The selected defect_code (str) if the user clicks a row for
        drill-down, or ``None``.
    """
    if not rows:
        st.info("No defects found for the selected date range.")
        return None

    data = []
    for row in rows:
        status_display = row.status.value
        if row.status == DefectStatus.RECURRING:
            status_display = "🔴 Recurring"
        data.append(
            {
                "Defect Code": row.defect_code,
                "Status": status_display,
                "# Weeks": row.num_weeks,
                "# Lots": row.num_lots,
                "First Seen": row.first_seen,
                "Last Seen": row.last_seen,
                "Total Qty Defects": row.total_qty,
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    defect_codes = [row.defect_code for row in rows]
    selected = st.selectbox(
        "Select a defect code to drill down", options=[""] + defect_codes
    )
    return selected if selected else None


def render_defect_detail(defect_code, weekly_rows, inspection_details):
    """Render the drill-down detail view for a single defect code (AC7).

    Shows:
        - A time breakdown by calendar week (week start/end, lots, qty).
        - The raw inspection records underlying the calculation.

    Args:
        defect_code:         The defect being inspected.
        weekly_rows:         List of ``WeeklyBreakdownRow`` DTOs.
        inspection_details:  List of ``InspectionDetail`` DTOs.
    """
    st.subheader(f"Detail View: {defect_code}")

    # Weekly breakdown table
    st.markdown("**Weekly Breakdown**")
    if weekly_rows:
        weekly_data = [
            {
                "Week Start": wr.week_start,
                "Week End": wr.week_end,
                "Lots Involved": ", ".join(wr.lots_involved),
                "Total Qty Defects": wr.total_qty,
            }
            for wr in weekly_rows
        ]
        st.dataframe(
            pd.DataFrame(weekly_data), use_container_width=True, hide_index=True
        )
    else:
        st.info("No weekly data available.")

    # Raw inspection records
    with st.expander("Underlying Inspection Records"):
        if inspection_details:
            detail_data = [
                {
                    "Lot ID": d.lot_id,
                    "Inspection Date": d.inspection_date,
                    "Defect Code": d.defect_code,
                    "Qty Defects": d.qty_defects,
                }
                for d in inspection_details
            ]
            st.dataframe(
                pd.DataFrame(detail_data), use_container_width=True, hide_index=True
            )
        else:
            st.info("No inspection records found.")


def render_insufficient_data_message(missing_periods):
    """Show which time periods are incomplete and why (AC8).

    Displayed when a defect has Status = "Insufficient data".

    Args:
        missing_periods: List of ``MissingPeriod`` DTOs.
    """
    if not missing_periods:
        return
    for mp in missing_periods:
        st.warning(mp.reason)


def main():
    """Entry point — assembles all widgets into the full page.

    Flow:
        1. Show page title.
        2. Render date range selector.
        3. Call the service to get the summary list.
        4. Render the filter toggle and summary table.
        5. If a defect is selected, render the drill-down detail.
        6. If the selected defect has insufficient data, show AC8 messaging.
    """

    load_dotenv()

    st.set_page_config(page_title="Recurring Defects", layout="wide")
    st.title("Recurring Defects Analysis")

    # 1. Date range selector
    start_date, end_date = render_date_range_selector()

    if start_date > end_date:
        st.error("Start date must be before or equal to end date.")
        return

    # 2. Get a database session and build the service
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        st.error("DATABASE_URL not set. Add it to your .env file.")
        return
    session = get_session(database_url)
    repo = InspectionRepository(session)
    service = RecurringDefectService(repo)

    # 3. Get the summary list
    rows = service.get_recurring_defect_list(start_date, end_date)

    # 4. Filter toggle (AC6)
    show_recurring_only = render_recurring_filter()
    if show_recurring_only:
        rows = [r for r in rows if r.status == DefectStatus.RECURRING]

    # 5. Summary table
    selected_defect = render_defect_summary_table(rows)

    # 6. Drill-down detail (AC7)
    if selected_defect:
        weekly_rows, inspection_details = service.get_defect_detail(
            selected_defect, start_date, end_date
        )
        render_defect_detail(selected_defect, weekly_rows, inspection_details)

        # 7. Insufficient data messaging (AC8)
        matching_rows = [r for r in rows if r.defect_code == selected_defect]
        if matching_rows and matching_rows[0].status == DefectStatus.INSUFFICIENT_DATA:
            missing_periods = service.get_missing_periods(
                selected_defect, start_date, end_date
            )
            render_insufficient_data_message(missing_periods)

    session.close()


# Streamlit convention: this block runs when you execute the file directly.
if __name__ == "__main__":
    main()
