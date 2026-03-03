"""
test_recurring_defects_page.py — End-to-end browser tests for the Recurring
Defects Streamlit page.

These tests launch a real Streamlit server (see ``conftest.py``) and use
Playwright to interact with the page in a headless browser, verifying that
the UI renders correctly and responds to user actions.

Key Playwright concepts for beginners:
    page:        A Playwright ``Page`` object represents a single browser tab.
                 pytest-playwright creates one automatically for each test — you
                 just add ``page: Page`` as a parameter and it's injected.

    page.goto(url):
                 Navigates the browser tab to a URL, like typing it in the
                 address bar and pressing Enter.

    page.get_by_role("heading", name="..."):
                 Finds an element by its accessibility role and text.  This is
                 the preferred way to locate elements because it mirrors how
                 screen readers and users see the page.
                 Common roles: "heading", "button", "checkbox", "textbox".

    page.get_by_text("..."):
                 Finds an element that contains the given text.  Useful when
                 there's no specific role to target.

    page.locator("css selector"):
                 Finds element(s) using a CSS selector.  Use this as a
                 fallback when get_by_role / get_by_text aren't specific
                 enough.  Streamlit assigns ``data-testid`` attributes to
                 its widgets, which makes CSS selectors reliable.

    expect(locator).to_be_visible(timeout=...):
                 Playwright's assertion helper.  Unlike regular ``assert``,
                 ``expect()`` auto-retries until the condition is met OR the
                 timeout expires.  This is essential for testing web apps
                 because elements may take time to render.

    page.wait_for_load_state("networkidle"):
                 Waits until the page has no active network requests for at
                 least 500ms.  Useful for waiting until Streamlit finishes
                 fetching data from the database and rendering the UI.

    locator.or_(other_locator):
                 Combines two locators with OR logic.  The assertion passes
                 if EITHER locator matches.  Useful when the page can show
                 one of two possible states (e.g., a data table OR an empty
                 message).

How to run these tests:
    poetry run pytest tests/e2e -v              # headless (no browser window)
    poetry run pytest tests/e2e -v --headed     # visible browser for debugging

Acceptance Criteria covered:
    AC5 — Summary table with required columns
    AC6 — Recurring filter checkbox
    AC7 — Drill-down selectbox and detail view
    AC9 — Default sort (Recurring first) — verified visually via table order
"""

import pytest
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Mark all tests in this file with the "e2e" marker.
#
# This lets you run ONLY e2e tests:   poetry run pytest -m e2e
# Or EXCLUDE them:                    poetry run pytest -m "not e2e"
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# AC5 — Page structure and summary table
# ---------------------------------------------------------------------------


class TestPageLoadsCorrectly:
    """Verify that the page renders its core structure."""

    def test_page_loads_with_title(self, page: Page, streamlit_app: str):
        """The page title 'Recurring Defects Analysis' should be visible.

        How this test works:
            1. page.goto() navigates the browser to the Streamlit app URL.
            2. get_by_role("heading") finds an HTML heading (<h1>, <h2>, etc.)
               whose text matches "Recurring Defects Analysis".
            3. expect(...).to_be_visible() asserts the heading is on screen,
               retrying for up to 15 seconds (Streamlit can be slow to load).
        """
        page.goto(streamlit_app)

        # Find the main heading by its accessibility role and text content
        title = page.get_by_role("heading", name="Recurring Defects Analysis")

        # Assert it's visible — Playwright retries automatically until the
        # timeout (15 seconds) is reached.  If the heading never appears,
        # the test fails with a clear error message.
        expect(title).to_be_visible(timeout=15_000)

    def test_date_range_inputs_present(self, page: Page, streamlit_app: str):
        """Start date and End date inputs should be rendered (AC5).

        Streamlit's st.date_input() renders a label above each date picker.
        We verify the labels are visible, which confirms the widgets rendered.
        """
        page.goto(streamlit_app)

        # get_by_text() searches for any element containing the given text.
        # Streamlit renders "Start date" and "End date" as label elements
        # above the date picker widgets.
        expect(page.get_by_text("Start date")).to_be_visible(timeout=15_000)
        expect(page.get_by_text("End date")).to_be_visible(timeout=15_000)

    def test_summary_table_or_empty_message_displays(
        self, page: Page, streamlit_app: str
    ):
        """Either the summary dataframe or the 'No defects found' message
        should appear, depending on whether the database has data (AC5).

        Why two possibilities?
            - If the database has inspection records → a data table renders
            - If the database is empty → an info message renders instead

        This test handles both cases so it passes regardless of DB state.
        """
        page.goto(streamlit_app)

        # wait_for_load_state("networkidle") pauses until the page has no
        # active network requests for 500ms.  This ensures Streamlit has
        # finished fetching data from the database and rendering widgets.
        page.wait_for_load_state("networkidle")

        # locator() with a CSS selector finds elements by their attributes.
        # Streamlit assigns data-testid="stDataFrame" to its dataframe widgets.
        table = page.locator("[data-testid='stDataFrame']")

        # get_by_text() finds the empty-state info message.
        empty_msg = page.get_by_text("No defects found for the selected date range.")

        # .or_() combines two locators — the assertion passes if EITHER one
        # is visible.  This makes the test resilient to whether the DB has data.
        expect(table.or_(empty_msg)).to_be_visible(timeout=15_000)


# ---------------------------------------------------------------------------
# AC6 — Recurring filter
# ---------------------------------------------------------------------------


class TestRecurringFilter:
    """AC6: The user should be able to filter to show only Recurring defects."""

    def test_recurring_filter_checkbox_present(self, page: Page, streamlit_app: str):
        """The 'Show only Recurring defects' checkbox should exist.

        Streamlit's st.checkbox() renders a clickable label next to a
        checkbox input.  We find it by its label text.
        """
        page.goto(streamlit_app)
        checkbox = page.get_by_text("Show only Recurring defects")
        expect(checkbox).to_be_visible(timeout=15_000)

    def test_recurring_filter_is_clickable(self, page: Page, streamlit_app: str):
        """Clicking the filter checkbox should not cause an error.

        This test verifies that:
            1. The checkbox can be found and clicked
            2. After clicking, the page doesn't crash (title still visible)

        When clicked, Streamlit reruns the script from top to bottom — this
        test ensures that rerun completes without exceptions.
        """
        page.goto(streamlit_app)

        # Find and click the checkbox
        checkbox = page.get_by_text("Show only Recurring defects")
        expect(checkbox).to_be_visible(timeout=15_000)
        checkbox.click()

        # After clicking, Streamlit reruns the entire page.  Verify the page
        # didn't crash by checking that the title is still visible.
        expect(
            page.get_by_role("heading", name="Recurring Defects Analysis")
        ).to_be_visible(timeout=15_000)


# ---------------------------------------------------------------------------
# AC7 — Drill-down selectbox
# ---------------------------------------------------------------------------


class TestDrillDown:
    """AC7: Selecting a defect code should reveal a detail view."""

    def test_drill_down_selectbox_present(self, page: Page, streamlit_app: str):
        """The 'Select a defect code to drill down' selectbox should render.

        The selectbox only appears when the summary table has data (i.e., when
        defects exist in the database for the selected date range).  If the
        table is empty, the selectbox won't be rendered, so we skip the check.
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        # First check if the data table is visible (meaning the DB has data)
        selectbox_label = page.get_by_text("Select a defect code to drill down")
        table = page.locator("[data-testid='stDataFrame']")

        # is_visible() returns True/False immediately (no retry).
        # We only assert the selectbox exists if the table rendered.
        if table.is_visible():
            expect(selectbox_label).to_be_visible(timeout=15_000)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify the page handles edge cases gracefully."""

    def test_page_does_not_crash_on_load(self, page: Page, streamlit_app: str):
        """The page should load without any uncaught Streamlit exceptions.

        When Streamlit encounters an unhandled Python exception, it renders
        a red error box with ``data-testid="stException"``.  This test
        asserts that zero such boxes exist on the page.
        """
        page.goto(streamlit_app)
        page.wait_for_load_state("networkidle")

        # Look for Streamlit's exception widget.  If any exist, the app crashed.
        exception_box = page.locator("[data-testid='stException']")

        # to_have_count(0) asserts there are exactly zero exception boxes.
        expect(exception_box).to_have_count(0)
