# Local Docker Test Database Configuration Guide

## Overview

This project has been configured to use a local Docker test database (`DATABASE_URL_TEST`) for integration tests, instead of the production database on Render (`DATABASE_URL`).

## Configuration Files

### 1. `.env.test` File
```bash
DATABASE_URL_TEST=postgresql://devuser:devpass@localhost:5433/testdb
```

### 2. `.env` File (Production Database)
```bash
DATABASE_URL=postgresql://admin:...@dpg-d66dbapr0fns73djsaa0-a.ohio-postgres.render.com/steelworks_ycr6
```

## Changes Made

### `tests/integration/conftest.py` Modifications
Integration tests now prioritize using `DATABASE_URL_TEST` from `.env.test`:
- First check `.env.test` file and `DATABASE_URL_TEST`
- If not found, fall back to `DATABASE_URL` from `.env` file

## How to Start Local Test Database

### Start PostgreSQL with Docker

```bash
docker run -d \
  --name test-postgres \
  -e POSTGRES_USER=devuser \
  -e POSTGRES_PASSWORD=devpass \
  -e POSTGRES_DB=testdb \
  -p 5433:5432 \
  postgres:15
```

### Verify Database Connection

```bash
# Check container status
docker ps --filter name=test-postgres

# Test connection
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://devuser:devpass@localhost:5433/testdb')
print('Connection successful')
conn.close()
"
```

## Run Integration Tests

```bash
# Ensure database is running
# Then run integration tests
poetry run pytest tests/integration/ -v
```

## Automatically Create Database Tables

Integration tests will automatically connect to the database, but will not automatically create tables. If needed, use the following methods:

### Method 1: Manually Create Tables

```python
from dotenv import load_dotenv
from sqlalchemy import create_engine
from src.models import Base

# Load .env.test
load_dotenv(dotenv_path=".env.test")
database_url = os.getenv("DATABASE_URL_TEST")

# Create tables
engine = create_engine(database_url)
Base.metadata.create_all(engine)
```

### Method 2: Use E2E Test Seed Data Functionality

E2E tests (`tests/e2e/conftest.py`) have a `seed_test_database()` fixture that can:
1. Create tables
2. Insert test data
3. Clean up data

You can modify or reuse this function as needed.

## Script Tools

There is a helper script in the project:

```bash
python scripts/setup_test_db.py
```

This script provides:
1. Docker status check
2. Table creation
3. Integration test execution

## Test Type Comparison

| Test Type | Database Usage | Notes |
|-----------|----------------|-------|
| **Unit Tests** | In-memory SQLite | No real database connection |
| **Integration Tests** | Local Docker PostgreSQL | Modified to use `DATABASE_URL_TEST` |
| **E2E Tests** | Local Docker PostgreSQL | Uses `DATABASE_URL_TEST` |

## Advantages

1. **Isolation**: Tests use an independent test database
2. **Repeatability**: Each test runs in a clean environment
3. **Local Development**: No network connection or Render account needed
4. **Cost Savings**: Avoid using cloud database resources

## Important Notes

1. **Database Initialization**: Integration tests will not automatically create tables; manual creation or seed data is required
2. **Port Conflict**: Ensure port 5433 is not in use
3. **Container Naming**: Use `test-postgres` name to avoid conflicts

## Troubleshooting

### Common Issues

1. **Database Connection Failure**
   ```bash
   # Check if container is running
   docker ps
   # Restart container
   docker restart test-postgres
   ```

2. **Port In Use**
   ```bash
   # Check port 5433
   netstat -an | grep 5433
   ```

3. **Tests Skipped**
   ```bash
   # Check if .env.test file exists
   # Check if DATABASE_URL_TEST is set correctly
   ```

## Migration Complete

You have completed the migration from Render production database to local Docker test database. Integration tests will now use the local database for testing.