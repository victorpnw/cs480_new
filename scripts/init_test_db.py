#!/usr/bin/env python3
"""Initialize test database with schema and seed data for CI."""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models import Base, Defect, InspectionRecord, Lot


def create_schema():
    """Create all database tables."""
    database_url = os.environ.get("DATABASE_URL_TEST")
    if not database_url:
        print("ERROR: DATABASE_URL_TEST environment variable not set")
        sys.exit(1)

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    print("✓ Database schema created successfully")
    engine.dispose()


def seed_test_data():
    """Insert test data for integration tests."""
    database_url = os.environ.get("DATABASE_URL_TEST")
    if not database_url:
        print("ERROR: DATABASE_URL_TEST environment variable not set")
        sys.exit(1)

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Build seed data (same as E2E tests)
        today = date.today()
        week1_monday = today - timedelta(days=today.weekday() + 7 * 6)
        week2_monday = today - timedelta(days=today.weekday() + 7 * 4)
        week3_monday = today - timedelta(days=today.weekday() + 7 * 2)

        defect_rec = Defect(defect_code="CI-REC-001")
        defect_notrec = Defect(defect_code="CI-NOTREC-001")
        lot_a = Lot(lot_id="CI-LOT-A")
        lot_b = Lot(lot_id="CI-LOT-B")
        lot_c = Lot(lot_id="CI-LOT-C")

        records = [
            InspectionRecord(
                inspection_id="CI-INS-001",
                lot=lot_a,
                defect=defect_rec,
                inspection_date=week1_monday,
                qty_defects=5,
                is_data_complete=True,
            ),
            InspectionRecord(
                inspection_id="CI-INS-002",
                lot=lot_b,
                defect=defect_rec,
                inspection_date=week1_monday + timedelta(days=1),
                qty_defects=3,
                is_data_complete=True,
            ),
            InspectionRecord(
                inspection_id="CI-INS-003",
                lot=lot_a,
                defect=defect_rec,
                inspection_date=week2_monday,
                qty_defects=2,
                is_data_complete=True,
            ),
            InspectionRecord(
                inspection_id="CI-INS-004",
                lot=lot_b,
                defect=defect_rec,
                inspection_date=week3_monday,
                qty_defects=4,
                is_data_complete=True,
            ),
            InspectionRecord(
                inspection_id="CI-INS-005",
                lot=lot_c,
                defect=defect_notrec,
                inspection_date=week1_monday + timedelta(days=2),
                qty_defects=1,
                is_data_complete=True,
            ),
            InspectionRecord(
                inspection_id="CI-INS-006",
                lot=lot_c,
                defect=defect_notrec,
                inspection_date=week2_monday + timedelta(days=1),
                qty_defects=2,
                is_data_complete=True,
            ),
        ]

        session.add_all([defect_rec, defect_notrec, lot_a, lot_b, lot_c] + records)
        session.commit()
        print("✓ Test data seeded successfully")
    finally:
        session.close()
        engine.dispose()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: init_test_db.py [schema|seed|all]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "schema":
        create_schema()
    elif action == "seed":
        seed_test_data()
    elif action == "all":
        create_schema()
        seed_test_data()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
