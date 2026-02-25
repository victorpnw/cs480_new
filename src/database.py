"""
database.py — Database connection setup.

This module creates the SQLAlchemy "engine" and "session" that the rest of the
application uses to talk to PostgreSQL.

Key concepts for beginners:
    Engine:  A factory that manages the connection pool to your database.
             Think of it like a phone switchboard that routes calls.
    Session: A short-lived workspace where you read/write data.  You open one,
             do your work, then close it.  (Similar to a database transaction.)

Usage:
    from src.database import get_session

    with get_session() as session:
        results = session.execute(...)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def get_engine(database_url: str):
    """Create and return a SQLAlchemy engine.

    Args:
        database_url: A connection string in the format
            ``postgresql://user:password@host:port/dbname``

    Returns:
        A SQLAlchemy ``Engine`` instance.
    """
    # TODO: implement — create engine from database_url
    pass


def get_session(database_url: str) -> Session:
    """Create and return a new database session.

    A session is like a "scratch pad" for database operations.  You use it to
    query data and commit changes.

    Args:
        database_url: A connection string (same format as ``get_engine``).

    Returns:
        A SQLAlchemy ``Session`` instance.
    """
    # TODO: implement — build a sessionmaker from the engine, return a session
    pass
