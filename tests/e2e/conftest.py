"""
conftest.py — Shared fixtures for end-to-end (E2E) browser tests.

This module starts a real Streamlit server as a subprocess before the test
session begins and tears it down when all E2E tests are finished.

Key concepts for beginners:
    Session-scoped fixture:  A fixture with ``scope="session"`` runs once for
                             the entire test session, not once per test.  This
                             avoids restarting the server for every single test.
    Subprocess:              We launch Streamlit in a child process so it runs
                             in the background while Playwright drives a browser
                             against it.
    Playwright ``page``:     A Playwright ``Page`` object represents a browser
                             tab.  pytest-playwright provides it automatically
                             (you don't need to create it yourself — just add
                             ``page: Page`` as a test parameter and pytest
                             injects it for you).

How E2E testing works (big picture):
    1. conftest.py seeds the test database with known data        (this file)
    2. conftest.py starts the Streamlit app on a random port      (this file)
    3. Each test gets a fresh browser tab (``page``) from pytest-playwright
    4. The test navigates to the app URL and interacts with the page
    5. After ALL tests finish, conftest.py shuts down the server and cleans up
"""

import os
import socket
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path so we can import src modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models import Base, Defect, InspectionRecord, Lot


def _find_free_port() -> int:
    """Find and return an available TCP port on localhost.

    How it works:
        - Opens a TCP socket and binds it to port 0 (the OS picks a free port).
        - Reads back which port the OS assigned.
        - Closes the socket, freeing the port for our Streamlit server to use.

    Returns:
        An integer port number that is currently not in use.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))  # Bind to port 0 → OS assigns a free port
        return s.getsockname()[1]  # getsockname() returns (host, port)


def _wait_for_server(port: int, timeout: float = 30.0) -> None:
    """Block until the Streamlit server is accepting connections.

    Streamlit takes a few seconds to start up.  This function repeatedly
    tries to open a TCP connection to localhost:<port>.  Once it succeeds,
    we know the server is ready and tests can begin.

    Args:
        port:    The port to poll.
        timeout: Maximum seconds to wait before giving up.

    Raises:
        TimeoutError: If the server is not ready within *timeout* seconds.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            # Try to connect — if the server is up, this succeeds immediately
            with socket.create_connection(("localhost", port), timeout=1):
                return  # Server is ready!
        except OSError:
            # Server not ready yet — wait briefly and retry
            time.sleep(0.5)
    raise TimeoutError(
        f"Streamlit server did not start on port {port} within {timeout}s"
    )


def _build_seed_data():
    """Build the seed data objects for E2E tests.

    Returns known data so workflow tests can assert against exact values.

    Seed data design:
        E2E-REC-001 (Recurring):
            3 distinct weeks, 2 distinct lots → RECURRING
        E2E-NOTREC-001 (Not Recurring):
            2 distinct weeks, 1 lot → NOT RECURRING

    Returns:
        A tuple of (defects, lots, records) lists ready to add to a session.
    """
    today = date.today()
    # Pick Mondays in the recent past (within the default 90-day window)
    week1_monday = today - timedelta(days=today.weekday() + 7 * 6)  # ~6 weeks ago
    week2_monday = today - timedelta(days=today.weekday() + 7 * 4)  # ~4 weeks ago
    week3_monday = today - timedelta(days=today.weekday() + 7 * 2)  # ~2 weeks ago

    # --- Defects ---
    defect_rec = Defect(defect_code="E2E-REC-001")
    defect_notrec = Defect(defect_code="E2E-NOTREC-001")

    # --- Lots ---
    lot_a = Lot(lot_id="E2E-LOT-A")
    lot_b = Lot(lot_id="E2E-LOT-B")
    lot_c = Lot(lot_id="E2E-LOT-C")

    # --- Inspection Records ---
    # Recurring defect: 3 weeks × 2 lots
    records = [
        InspectionRecord(
            inspection_id="E2E-INS-001",
            lot=lot_a,
            defect=defect_rec,
            inspection_date=week1_monday,
            qty_defects=5,
            is_data_complete=True,
        ),
        InspectionRecord(
            inspection_id="E2E-INS-002",
            lot=lot_b,
            defect=defect_rec,
            inspection_date=week1_monday + timedelta(days=1),
            qty_defects=3,
            is_data_complete=True,
        ),
        InspectionRecord(
            inspection_id="E2E-INS-003",
            lot=lot_a,
            defect=defect_rec,
            inspection_date=week2_monday,
            qty_defects=2,
            is_data_complete=True,
        ),
        InspectionRecord(
            inspection_id="E2E-INS-004",
            lot=lot_b,
            defect=defect_rec,
            inspection_date=week3_monday,
            qty_defects=4,
            is_data_complete=True,
        ),
        # Not-recurring defect: 2 weeks × 1 lot
        InspectionRecord(
            inspection_id="E2E-INS-005",
            lot=lot_c,
            defect=defect_notrec,
            inspection_date=week1_monday + timedelta(days=2),
            qty_defects=1,
            is_data_complete=True,
        ),
        InspectionRecord(
            inspection_id="E2E-INS-006",
            lot=lot_c,
            defect=defect_notrec,
            inspection_date=week2_monday + timedelta(days=1),
            qty_defects=2,
            is_data_complete=True,
        ),
    ]

    return [defect_rec, defect_notrec], [lot_a, lot_b, lot_c], records


@pytest.fixture(scope="session")
def _test_database_url():
    """Load and return DATABASE_URL_TEST, skipping if not set.

    This is the connection string for the dedicated E2E test database.
    It is separate from the production/dev DATABASE_URL to avoid
    polluting real data.
    """
    load_dotenv()
    url = os.environ.get("DATABASE_URL_TEST")
    if not url:
        pytest.skip("DATABASE_URL_TEST not set — skipping E2E tests")
    return url


@pytest.fixture(scope="session", autouse=True)
def seed_test_database(_test_database_url):
    """Create tables and insert seed data into the test database.

    This runs once before all E2E tests (session-scoped) and cleans up
    after all tests are done.  The ``autouse=True`` means every E2E test
    automatically gets the seeded database without requesting this
    fixture explicitly.

    Lifecycle:
        1. Create all tables (if they don't exist)
        2. Insert seed defects, lots, and inspection records
        3. Yield (tests run against this data)
        4. Delete seed data and close the session
    """
    engine = create_engine(_test_database_url)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    defects, lots, records = _build_seed_data()
    try:
        session.add_all(defects + lots + records)
        session.commit()
        yield
    finally:
        # Clean up: delete seed data (order matters due to foreign keys)
        for r in records:
            session.delete(r)
        for obj in lots + defects:
            session.delete(obj)
        session.commit()
        session.close()
        engine.dispose()


@pytest.fixture(scope="session")
def streamlit_app(_test_database_url):
    """Start a Streamlit server and yield its base URL.

    This is a **session-scoped** fixture, meaning it runs once before all
    E2E tests and tears down once after all E2E tests.  Every test that
    requests ``streamlit_app`` gets the same URL pointing to the same
    running server.

    The subprocess receives ``DATABASE_URL`` set to the test database URL
    so the Streamlit app connects to the isolated test DB, not the
    production/dev database.

    Lifecycle:
        1. Pick a random free port
        2. Launch ``streamlit run`` with DATABASE_URL pointing to test DB
        3. Wait for the server to accept connections
        4. Yield the URL (e.g. "http://localhost:54321") to the tests
        5. After all tests finish, terminate the subprocess (cleanup)

    Yields:
        The base URL string, e.g. ``http://localhost:12345``.
    """
    port = _find_free_port()
    project_root = (
        Path(__file__).resolve().parents[2]
    )  # tests/e2e/ → tests/ → project root
    app_path = project_root / "src" / "ui" / "recurring_defects_page.py"

    # Build the subprocess environment: inherit current env but override
    # DATABASE_URL to point at the test database.
    env = os.environ.copy()
    env["DATABASE_URL"] = _test_database_url

    # Launch Streamlit as a child process.
    #
    # Key flags:
    #   --server.port <port>             Use our chosen port (not the default 8501)
    #   --server.headless true           Don't try to open a browser window
    #   --browser.gatherUsageStats false Don't send anonymous usage data
    #
    # subprocess.Popen() starts the process and returns immediately (non-blocking).
    # The server keeps running in the background while our tests execute.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",  # python -m streamlit run ...
            str(app_path),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(project_root),  # Run from the project root so imports work
        env=env,  # Use test database, not production
        stdout=subprocess.PIPE,  # Capture stdout (prevents it from cluttering test output)
        stderr=subprocess.PIPE,  # Capture stderr
    )

    try:
        # Wait until the server is accepting TCP connections before running tests
        _wait_for_server(port)
        yield f"http://localhost:{port}"
    finally:
        # Cleanup: stop the Streamlit server after all tests are done.
        # terminate() sends SIGTERM (graceful shutdown).
        # wait() blocks until the process actually exits.
        proc.terminate()
        proc.wait(timeout=10)


# ---------------------------------------------------------------------------
# Slow-motion mode for teaching / demos
# ---------------------------------------------------------------------------
#
# pytest-playwright's built-in ``--slowmo`` flag adds a delay (in ms)
# before every browser action (click, type, navigate, etc.).  This makes
# it easy to watch what the tests are doing in headed mode.
#
# Usage:
#     poetry run pytest tests/e2e -v --headed --slowmo 1000
#
# The number is milliseconds — 1000 = 1 second pause between each action.
# Adjust to taste:  500 for a quick walkthrough, 2000 for a slow demo.
