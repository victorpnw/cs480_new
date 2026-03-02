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


def render_date_range_selector():
    """Display start-date and end-date inputs and return the selected range.

    The user picks a date range that scopes all queries on this page.

    Returns:
        A tuple of (start_date, end_date) as ``datetime.date`` objects.
    """
    # TODO: implement — use st.date_input for start and end dates
    pass


def render_recurring_filter():
    """Display a checkbox/toggle to filter the table to Recurring-only (AC6).

    Returns:
        ``True`` if the user wants to see only Recurring defects.
    """
    # TODO: implement — use st.checkbox or st.toggle
    pass


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
    # TODO: implement — use st.dataframe or st.table, highlight Recurring rows
    pass


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
    # TODO: implement — use st.subheader, st.dataframe, st.expander, etc.
    pass


def render_insufficient_data_message(missing_periods):
    """Show which time periods are incomplete and why (AC8).

    Displayed when a defect has Status = "Insufficient data".

    Args:
        missing_periods: List of ``MissingPeriod`` DTOs.
    """
    # TODO: implement — use st.warning or st.info to show each missing period
    pass


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
    # TODO: implement — wire together the functions above with the service
    pass


# Streamlit convention: this block runs when you execute the file directly.
if __name__ == "__main__":
    main()
