# Basket Craft Pipeline

This project is a Python ELT pipeline that extracts order data from a MySQL source database, stages it in PostgreSQL, and builds a monthly analytics table for reporting.

The final output table is:

- `analytics.monthly_sales_by_category`

It contains:

- `order_month`
- `category_name`
- `total_revenue`
- `order_count`
- `avg_order_value`

## Project Structure

- `pipeline/db.py` - creates SQLAlchemy engines for MySQL and PostgreSQL
- `pipeline/extract.py` - reads source tables from MySQL
- `pipeline/load_staging.py` - writes raw tables to PostgreSQL `staging` schema
- `pipeline/transform.py` - transforms staged data into analytics output
- `run_pipeline.py` - command-line entry point for dry-run and full pipeline runs
- `tests/test_transform.py` - unit tests for transform logic

## Prerequisites

- Python 3.10+ (project currently runs with Python 3.14)
- Docker Desktop (or Docker Engine + Compose)
- Access credentials for the source MySQL database

## Setup

### 1) Clone the repository

```bash
git clone https://github.com/yjoe2027/basket-craft-pipeline.git
cd basket-craft-pipeline
```

### 2) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

Copy the template and fill in credentials:

```bash
cp .env.example .env
```

Expected variables in `.env`:

```env
# MySQL source
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_DB=basket_craft
MYSQL_USER=
MYSQL_PASSWORD=

# PostgreSQL destination
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=basket_craft_dw
POSTGRES_USER=pipeline
POSTGRES_PASSWORD=pipeline
```

### 5) Start PostgreSQL (destination warehouse)

```bash
docker compose up -d
docker compose ps
```

PostgreSQL runs via `docker-compose.yml` on `localhost:5432`.

## Running the Pipeline

### Dry Run (connectivity and source row counts only)

Use this to validate DB connections without writing to PostgreSQL:

```bash
python3 run_pipeline.py --dry-run
```

### Full Run (extract -> stage -> transform)

```bash
python3 run_pipeline.py
```

Expected high-level output:

- Phase 1: Extracting from MySQL
- Phase 2: Loading to PostgreSQL staging
- Phase 3: Transforming and loading analytics
- Pipeline complete

## Verify Output

Query the analytics table in PostgreSQL:

```bash
set -a && source .env && set +a
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" \
  -c "SELECT order_month, category_name, total_revenue, order_count, avg_order_value FROM analytics.monthly_sales_by_category ORDER BY order_month, category_name LIMIT 20;"
```

## Run Tests

```bash
pytest tests/test_transform.py -v
```

## Stop PostgreSQL Container

```bash
docker compose down
```
