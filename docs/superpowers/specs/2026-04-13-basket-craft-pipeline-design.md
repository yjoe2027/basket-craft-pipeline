# Basket Craft Data Pipeline — Design Spec

**Date:** 2026-04-13
**Project:** ISBA 4715 — basket-craft-pipeline
**Status:** Approved

---

## Overview

A Python-based ELT pipeline that extracts data from the Basket Craft MySQL database, stages raw tables into a local PostgreSQL instance (Docker), and transforms them into a monthly sales summary by product category. The output powers a monthly sales dashboard showing revenue, order counts, and average order value (AOV) per category per month.

---

## Architecture

**Approach:** SQLAlchemy + pandas, script-based (manual or cron trigger), full refresh on every run.

**Three-phase flow:**

```
MySQL (basket_craft)
  └── Phase 1: Extract     extract.py       → raw DataFrames (4 tables)
  └── Phase 2: Stage       load_staging.py  → PostgreSQL staging schema
  └── Phase 3: Transform   transform.py     → PostgreSQL analytics schema
```

**File structure:**

```
basket-craft-pipeline/
├── pipeline/
│   ├── __init__.py
│   ├── extract.py          # Phase 1: MySQL → raw DataFrames
│   ├── load_staging.py     # Phase 2: DataFrames → PostgreSQL staging schema
│   ├── transform.py        # Phase 3: staging → analytics.monthly_sales_by_category
│   └── db.py               # SQLAlchemy engine factories for MySQL and PostgreSQL
├── run_pipeline.py         # Entry point — runs all three phases in sequence
├── tests/
│   └── test_transform.py   # Unit tests for transform logic (no DB required)
├── .env                    # DB credentials (gitignored)
├── requirements.txt
└── docker-compose.yml      # Local PostgreSQL (postgres:15)
```

---

## Assumed MySQL Schema

Database: `basket_craft`

```sql
orders        (order_id PK, customer_id, order_date DATE, status VARCHAR)
order_items   (item_id PK, order_id FK, product_id FK, quantity INT, unit_price DECIMAL)
products      (product_id PK, name VARCHAR, category_id FK, sku VARCHAR)
categories    (category_id PK, name VARCHAR)
```

**Assumptions to verify against real schema:**
1. Order date is on the `orders` table (not `order_items`)
2. Revenue = `quantity × unit_price` (no separate discounts or tax columns)

If the real schema differs, only `extract.py` and `transform.py` need updating. `load_staging.py` is schema-agnostic.

---

## Phase 1 — Extract (`pipeline/extract.py`)

- Connect to MySQL using a SQLAlchemy engine from `db.py`
- Run `pd.read_sql(table_name, engine)` for each of the four tables
- Return a dict: `{"orders": df, "order_items": df, "products": df, "categories": df}`
- No filtering — full tables on every run (full-refresh strategy)

---

## Phase 2 — Stage (`pipeline/load_staging.py`)

- Connect to PostgreSQL using a SQLAlchemy engine from `db.py`
- Write each DataFrame to the `staging` schema using `df.to_sql(name, engine, schema='staging', if_exists='replace', index=False)`
- Resulting tables: `staging.orders`, `staging.order_items`, `staging.products`, `staging.categories`
- No manual DDL required — pandas infers and creates the schema

---

## Phase 3 — Transform (`pipeline/transform.py`)

Steps performed in-memory with pandas:

1. **Read staging tables** from PostgreSQL back into DataFrames
2. **Join** `order_items → orders → products → categories` into one flat DataFrame
3. **Compute line revenue:** `line_revenue = quantity × unit_price`
4. **Floor to month:** `order_month = order_date.dt.to_period('M').dt.to_timestamp()` (stored as first day of month, e.g. `2025-01-01`)
5. **Group & aggregate** by `(order_month, category_name)`:
   - `total_revenue = line_revenue.sum()`
   - `order_count = order_id.nunique()` — distinct orders, not line items
   - `avg_order_value = total_revenue / order_count`
6. **Write** result to `analytics.monthly_sales_by_category` with `if_exists='replace'`

> **Key design note:** `order_id.nunique()` is required for correct order counts and AOV. A single order with multiple products creates multiple rows after the join — counting rows would inflate both metrics.

---

## PostgreSQL Target Schema

**`staging` schema** — auto-created by pandas, raw mirror of MySQL source tables.

**`analytics` schema** — single output table:

```sql
CREATE TABLE analytics.monthly_sales_by_category (
    order_month       DATE        NOT NULL,
    category_name     VARCHAR     NOT NULL,
    total_revenue     NUMERIC(12,2),
    order_count       INTEGER,
    avg_order_value   NUMERIC(10,2)
);
```

---

## Docker Setup (`docker-compose.yml`)

- Image: `postgres:15`
- Port: `5432` exposed to localhost
- Named volume for data persistence across container restarts
- Environment: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` sourced from `.env`

---

## Credentials & Configuration (`.env`)

```
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
POSTGRES_USER=
POSTGRES_PASSWORD=
```

Loaded at runtime via `python-dotenv`. Already covered by the Python `.gitignore` in this repo.

---

## Error Handling

- Each phase wrapped in `try/except` in `run_pipeline.py` with a printed message identifying the failing phase
- SQLAlchemy connection errors surface the original exception — no silent swallowing
- Fail fast on connectivity issues; no retries
- `--dry-run` flag on `run_pipeline.py`: connects to both databases, prints MySQL table row counts, writes nothing to PostgreSQL

---

## Testing

**Unit tests** (`tests/test_transform.py`):
- Construct minimal in-memory DataFrames with known values
- Run transform logic and assert correct `total_revenue`, `order_count`, and `avg_order_value`
- No database required

**Smoke test** (`run_pipeline.py --dry-run`):
- Validates credentials and connectivity for both MySQL and PostgreSQL
- Prints row counts from source tables without writing anything

---

## Dependencies (`requirements.txt`)

```
sqlalchemy
pymysql          # MySQL dialect for SQLAlchemy
psycopg2-binary  # PostgreSQL dialect for SQLAlchemy
pandas
python-dotenv
```
