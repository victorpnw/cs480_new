# CS480 SteelWorks — Recurring Defect Analysis

An internal web application for SteelWorks, LLC quality engineers to identify whether the same defect type appears across multiple lots over time, distinguishing recurring issues from one-off incidents.

## Tech Stack

- **Python 3.11+**
- **Streamlit** — web UI
- **SQLAlchemy** — ORM / data access
- **PostgreSQL** — database
- **Pytest** — testing
- **Poetry** — dependency management

## Architecture

Layered monolith (UI → Service → Repository → DB):

```
src/
├── ui/                        # Presentation layer (Streamlit)
│   └── recurring_defects_page.py
├── services/                  # Business logic layer
│   └── recurring_defect_service.py
├── repositories/              # Data access layer
│   └── inspection_repository.py
├── models.py                  # SQLAlchemy ORM models
├── schemas.py                 # DTOs (dataclasses)
└── database.py                # Engine and session setup
```

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- [Poetry](https://python-poetry.org/docs/#installation)

## Getting Started

### 1. Install dependencies

```bash
poetry install --no-root
```

### 2. Configure the database

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### 3. Set up the database schema

Run the schema against your PostgreSQL database:

```bash
psql -U your_user -d your_db -f db/schema.sql
```

### 4. Run the application

```bash
poetry run streamlit run src/ui/recurring_defects_page.py
```

### 5. Run tests

**Unit tests** (no database required — uses in-memory SQLite):

```bash
poetry run pytest tests/unit -v
```

**E2E browser tests** (requires database connection in `.env`):

```bash
# One-time setup: install Playwright browsers
poetry run playwright install chromium

# Run E2E tests (headless)
poetry run pytest tests/e2e -v

# Run E2E tests with visible browser (headed mode)
poetry run pytest tests/e2e -v --headed

# Run all tests (unit + E2E)
poetry run pytest -v
```

## Features

| Feature | Description |
|---|---|
| **Recurring Defect Classification** | Defects appearing in >1 calendar week AND >1 lot are flagged as recurring |
| **Zero-Defect Filtering** | Records with `qty_defects = 0` are excluded from occurrence counts |
| **Insufficient Data Detection** | Incomplete inspection periods are identified with explanatory messages |
| **Summary List View** | Table with defect code, status, # weeks, # lots, date range, and total qty |
| **Recurring Filter** | Toggle to show only recurring defects |
| **Drill-Down Detail** | Weekly breakdown by defect code with lots involved and underlying records |
| **Default Sorting** | Recurring defects first, then by # weeks descending, then # lots descending |
