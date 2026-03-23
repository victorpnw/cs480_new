#!/usr/bin/env python3
"""Script to help set up local Docker test database for integration tests."""

import os
import subprocess
from pathlib import Path


def print_instructions():
    """Print instructions for setting up local Docker test database."""
    print("\n=== SETTING UP LOCAL DOCKER TEST DATABASE ===\n")

    # Check if .env.test exists
    test_env_path = Path(__file__).parent.parent / ".env.test"
    print("1. Check .env.test file:")
    print(f"   Path: {test_env_path}")
    print(f"   Exists: {test_env_path.exists()}")

    if test_env_path.exists():
        with open(test_env_path, "r") as f:
            content = f.read()
            print(f"   Content: {content}")

    print("\n2. Start PostgreSQL database with Docker:")
    print("   Command:")
    print("   docker run -d \\")
    print("     --name test-postgres \\")
    print("     -e POSTGRES_USER=devuser \\")
    print("     -e POSTGRES_PASSWORD=devpass \\")
    print("     -e POSTGRES_DB=testdb \\")
    print("     -p 5433:5432 \\")
    print("     postgres:15")

    print("\n3. Create tables and seed data (optional):")
    print("   The integration tests will automatically use the database.")
    print("   You can run integration tests to verify:")
    print("   poetry run pytest tests/integration/ -v")

    print("\n4. Alternative: Use existing E2E test seeding:")
    print("   The E2E tests have a fixture that seeds the database:")
    print("   - seed_test_database() in tests/e2e/conftest.py")
    print("   - You can adapt this for integration tests if needed")

    print("\n=== AUTOMATED SETUP ===\n")
    print("You can use this script to:")
    print("  a. Check Docker status")
    print("  b. Create tables manually")
    print("  c. Run integration tests")


def check_docker():
    """Check if Docker is installed and PostgreSQL container is running."""
    print("\nChecking Docker status...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=test-postgres"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print("✓ PostgreSQL container is running:")
            print(result.stdout)
        else:
            print("✗ PostgreSQL container 'test-postgres' not found")

        # Check if PostgreSQL is available
        try:
            import psycopg2
            from .env.test import DATABASE_URL_TEST

            conn = psycopg2.connect(DATABASE_URL_TEST)
            conn.close()
            print("✓ Database connection successful!")
        except ImportError:
            print("⚠ psycopg2 not installed, can't test connection")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
    except FileNotFoundError:
        print("✗ Docker not found or not installed")


def create_tables():
    """Create database tables using SQLAlchemy."""
    print("\nCreating database tables...")
    try:
        from dotenv import load_dotenv
        from sqlalchemy import create_engine
        from src.models import Base

        # Load .env.test
        project_root = Path(__file__).parent.parent
        test_env_path = project_root / ".env.test"
        load_dotenv(dotenv_path=test_env_path)

        database_url = os.getenv("DATABASE_URL_TEST")
        if not database_url:
            print("✗ DATABASE_URL_TEST not found in .env.test")
            return

        print(f"Using database URL: {database_url}")

        # Create engine and tables
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        print("✓ Tables created successfully!")

    except Exception as e:
        print(f"✗ Failed to create tables: {e}")


def main():
    """Main function."""
    print_instructions()

    print("\nWhat would you like to do?")
    print("1. Check Docker status")
    print("2. Create tables")
    print("3. Run integration tests")
    print("4. Exit")

    choice = input("\nEnter choice (1-4): ")

    if choice == "1":
        check_docker()
    elif choice == "2":
        create_tables()
    elif choice == "3":
        print("\nRunning integration tests...")
        subprocess.run(["poetry", "run", "pytest", "tests/integration/", "-v"])
    elif choice == "4":
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
