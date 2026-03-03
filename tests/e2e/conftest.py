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
    1. conftest.py starts the Streamlit app on a random port  (this file)
    2. Each test gets a fresh browser tab (``page``) from pytest-playwright
    3. The test navigates to the app URL and interacts with the page
    4. After ALL tests finish, conftest.py shuts down the Streamlit server
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from dotenv import load_dotenv


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


@pytest.fixture(scope="session")
def streamlit_app():
    """Start a Streamlit server and yield its base URL.

    This is a **session-scoped** fixture, meaning it runs once before all
    E2E tests and tears down once after all E2E tests.  Every test that
    requests ``streamlit_app`` gets the same URL pointing to the same
    running server.

    Lifecycle:
        1. Load .env so the subprocess inherits DATABASE_URL
        2. Pick a random free port
        3. Launch ``streamlit run`` as a background subprocess
        4. Wait for the server to accept connections
        5. Yield the URL (e.g. "http://localhost:54321") to the tests
        6. After all tests finish, terminate the subprocess (cleanup)

    Yields:
        The base URL string, e.g. ``http://localhost:12345``.
    """
    # Load .env so DATABASE_URL is available to the subprocess.
    # load_dotenv() reads the .env file and sets the values as environment
    # variables.  The subprocess inherits our environment, so it will see
    # DATABASE_URL automatically.
    load_dotenv()

    port = _find_free_port()
    project_root = (
        Path(__file__).resolve().parents[2]
    )  # tests/e2e/ → tests/ → project root
    app_path = project_root / "src" / "ui" / "recurring_defects_page.py"

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
