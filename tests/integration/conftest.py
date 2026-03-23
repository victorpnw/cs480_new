"""Shared fixtures for integration tests.

Why this file exists:
    Unit tests in this project use mocks or in-memory SQLite.
    End-to-end tests run the full browser app.
    Integration tests sit in the middle: they call real repository/service
    code against a real PostgreSQL database, but without the UI/browser layer.

Fixtures below provide that wiring so each test can focus on behavior, not
setup boilerplate.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from src.database import get_session
from src.repositories.inspection_repository import InspectionRepository
from src.services.recurring_defect_service import RecurringDefectService


@pytest.fixture(scope="session")
def database_url() -> str | None:
    """Resolve the database URL once per test session.

    Steps:
        1. Load project `.env.test` for test-specific configuration.
        2. Read `DATABASE_URL_TEST` from environment variables.
        3. If missing, fall back to `.env` and `DATABASE_URL`.
        4. If still missing, skip integration tests with a clear reason.

    Why `scope="session"`:
        This value does not change between tests, so loading it once is faster.
    """
    project_root = Path(__file__).resolve().parents[2]

    # First try to load .env.test for test-specific configuration
    test_env_path = project_root / ".env.test"
    if test_env_path.exists():
        load_dotenv(dotenv_path=test_env_path)
        database_url = os.getenv("DATABASE_URL_TEST")
        if database_url:
            return database_url

    # Fall back to .env if .env.test doesn't exist or DATABASE_URL_TEST is not set
    load_dotenv(dotenv_path=project_root / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Neither DATABASE_URL_TEST nor DATABASE_URL is set; skipping integration tests."
        )
    return database_url


@pytest.fixture
def db_session(database_url: str) -> Session:
    """Create a real SQLAlchemy session for one test function.

    Why function scope:
        Each test gets a fresh session object so identity-map state from one
        test does not leak into another.
    """
    session = get_session(database_url)
    try:
        yield session
    finally:
        # Always close the connection even if a test fails.
        session.close()


@pytest.fixture
def repository(db_session: Session) -> InspectionRepository:
    """Build a repository that uses the real PostgreSQL-backed session."""
    return InspectionRepository(db_session)


@pytest.fixture
def service(repository: InspectionRepository) -> RecurringDefectService:
    """Build the service with the real repository dependency.

    This gives us a true integration chain:
        Service -> Repository -> SQLAlchemy -> PostgreSQL
    """
    return RecurringDefectService(repository)
