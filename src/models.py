"""
models.py — SQLAlchemy ORM models.

ORM (Object-Relational Mapping) lets you represent database tables as Python
classes.  Each class below maps to exactly one table in ``db/schema.sql``.

Key concepts for beginners:
    DeclarativeBase:  The parent class that all ORM models inherit from.
                      SQLAlchemy uses it to track which classes are "models".
    Column / mapped_column:  Declares a column in the table.
    relationship:     Declares a link *between* tables (like a foreign key),
                      so you can navigate from one object to its related objects
                      in Python (e.g., ``lot.inspection_records``).

See also:
    db/schema.sql          — the raw SQL that creates these tables
    docs/data_design.md    — the ERD and relationship descriptions
"""

from datetime import date, datetime
from sqlalchemy import String, Integer, Boolean, Date, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base class — every model inherits from this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all ORM models.  You never instantiate this directly."""

    pass


# ---------------------------------------------------------------------------
# Defect master table
# ---------------------------------------------------------------------------
class Defect(Base):
    """Represents a type of defect (e.g., 'DEF-001').

    Maps to the ``defects`` table.  The ``defect_code`` is the business key
    that quality engineers recognise; ``id`` is an internal surrogate key.

    Attributes:
        id:           Auto-incremented primary key (internal use only).
        defect_code:  Human-readable code like 'DEF-001' (unique).
        created_at:   Timestamp when this row was inserted.
        inspection_records:  List of related ``InspectionRecord`` objects.
    """

    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=True)

    # One defect → many inspection records
    inspection_records: Mapped[list["InspectionRecord"]] = relationship(
        back_populates="defect"
    )


# ---------------------------------------------------------------------------
# Lot master table
# ---------------------------------------------------------------------------
class Lot(Base):
    """Represents a production lot (e.g., 'LOT-2026-0042').

    Maps to the ``lots`` table.

    Attributes:
        id:           Auto-incremented primary key (internal use only).
        lot_id:       Human-readable lot identifier (unique).
        created_at:   Timestamp when this row was inserted.
        inspection_records:  List of related ``InspectionRecord`` objects.
    """

    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=True)

    # One lot → many inspection records
    inspection_records: Mapped[list["InspectionRecord"]] = relationship(
        back_populates="lot"
    )


# ---------------------------------------------------------------------------
# Inspection record (transactional table)
# ---------------------------------------------------------------------------
class InspectionRecord(Base):
    """A single inspection event linking a lot, a defect, a date, and a count.

    Maps to the ``inspection_records`` table.  This is the main transactional
    table — most queries in this application start here.

    Attributes:
        id:               Auto-incremented primary key.
        inspection_id:    External business identifier (unique).
        lot_fk:           Foreign key → ``lots.id``.
        defect_fk:        Foreign key → ``defects.id``.
        inspection_date:  The date the inspection was performed.
        qty_defects:      Number of defects found (>= 0).
        is_data_complete: Flag indicating whether the data for this record is
                          trustworthy.  ``False`` triggers AC4 (insufficient
                          data) logic.
        lot:              The related ``Lot`` object.
        defect:           The related ``Defect`` object.
    """

    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    lot_fk: Mapped[int] = mapped_column("lot_id", ForeignKey("lots.id"), nullable=False)
    defect_fk: Mapped[int] = mapped_column(
        "defect_id", ForeignKey("defects.id"), nullable=False
    )
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    qty_defects: Mapped[int] = mapped_column(Integer, nullable=False)
    is_data_complete: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships (back-references to parent tables)
    lot: Mapped["Lot"] = relationship(back_populates="inspection_records")
    defect: Mapped["Defect"] = relationship(back_populates="inspection_records")
