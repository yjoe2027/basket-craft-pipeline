# Basket Craft Pipeline

This project is a Python ELT pipeline that extracts data from a Basket Craft MySQL source database and loads it into two PostgreSQL destinations:

1. **AWS RDS PostgreSQL** — all 8 raw source tables loaded as-is into the `staging` schema (`run_extract_rds.py`)
2. **Local Docker PostgreSQL** — 3 core tables staged and transformed into a monthly analytics aggregate (`run_pipeline.py`)

### AWS RDS — Raw staging tables (`staging` schema)

| Table | Rows |
|---|---|
| employees | 20 |
| order_item_refunds | 1,731 |
| order_items | 40,025 |
| orders | 32,313 |
| products | 4 |
| users | 31,696 |
| website_pageviews | 1,188,124 |
| website_sessions | 472,871 |

### Local PostgreSQL — Analytics output

- `analytics.monthly_sales_by_category` — monthly revenue, order count, and average order value by product

## Project Structure

- `pipeline/db.py` — SQLAlchemy engine factories for MySQL, local PostgreSQL, and AWS RDS
- `pipeline/extract.py` — reads 3 core tables from MySQL (used by `run_pipeline.py`)
- `pipeline/extract_all.py` — discovers and reads all MySQL tables dynamically (used by `run_extract_rds.py`)
- `pipeline/load_staging.py` — writes raw tables to local PostgreSQL `staging` schema
- `pipeline/load_rds.py` — writes all raw tables to RDS `staging` schema with per-table error isolation
- `pipeline/transform.py` — transforms staged data into analytics output
- `run_pipeline.py` — local pipeline: extract 3 tables → stage → transform → analytics
- `run_extract_rds.py` — RDS extract: dump all MySQL tables to RDS staging (raw, no transforms)
- `tests/test_transform.py` — unit tests for transform logic

## Prerequisites

- Python 3.10+ (project currently runs with Python 3.14)
- Docker Desktop (or Docker Engine + Compose) — only needed for the local pipeline
- Access credentials for the source MySQL database
- AWS RDS PostgreSQL instance credentials — only needed for `run_extract_rds.py`

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

Expected variables in `.env` (see `.env.example` for the full template):

```env
# MySQL source
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_DB=basket_craft
MYSQL_USER=
MYSQL_PASSWORD=

# Local PostgreSQL destination (docker-compose)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=basket_craft_dw
POSTGRES_USER=pipeline
POSTGRES_PASSWORD=pipeline

# AWS RDS PostgreSQL destination
RDS_HOST=
RDS_PORT=5432
RDS_USER=
RDS_PASSWORD=
RDS_DATABASE=
```

### 5) Start PostgreSQL (destination warehouse)

```bash
docker compose up -d
docker compose ps
```

PostgreSQL runs via `docker-compose.yml` on `localhost:5432`.

## Running the Pipeline

### RDS Raw Extract (all 8 tables → AWS RDS staging)

Test connections first without writing:

```bash
python run_extract_rds.py --dry-run
```

Full load (idempotent — replaces staging tables on each run):

```bash
python run_extract_rds.py
```

### Local Analytics Pipeline (3 tables → Docker PostgreSQL → analytics)

Dry run to validate connections only:

```bash
python run_pipeline.py --dry-run
```

Full run (extract → stage → transform):

```bash
python run_pipeline.py
```

Expected output phases:

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
