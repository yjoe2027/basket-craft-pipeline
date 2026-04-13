# Basket Craft Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python ELT pipeline that extracts data from MySQL, stages it in PostgreSQL, and produces a `monthly_sales_by_category` analytics table with revenue, order count, and AOV.

**Architecture:** Three-phase script (`extract → load_staging → transform`) run via `run_pipeline.py`. SQLAlchemy handles both database connections; pandas performs all joins and aggregations in-memory. Full truncate-and-reload on every run.

**Tech Stack:** Python 3, SQLAlchemy, pandas, pymysql, psycopg2-binary, python-dotenv, pytest, Docker (postgres:15)

---

## File Map

| File | Responsibility |
|---|---|
| `requirements.txt` | Python dependencies |
| `.env` | DB credentials (gitignored) |
| `docker-compose.yml` | Local PostgreSQL container |
| `pipeline/__init__.py` | Package marker |
| `pipeline/db.py` | SQLAlchemy engine factories for MySQL and PostgreSQL |
| `pipeline/extract.py` | Phase 1: read 4 tables from MySQL → dict of DataFrames |
| `pipeline/load_staging.py` | Phase 2: write DataFrames to `staging` schema in PostgreSQL |
| `pipeline/transform.py` | Phase 3: join + aggregate staging data → `analytics.monthly_sales_by_category` |
| `run_pipeline.py` | Entry point: runs all three phases; supports `--dry-run` |
| `tests/__init__.py` | Test package marker |
| `tests/test_transform.py` | Unit tests for transform logic (no DB required) |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env`
- Create: `docker-compose.yml`
- Create: `pipeline/__init__.py`
- Create: `tests/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `requirements.txt`**

```
sqlalchemy
pymysql
psycopg2-binary
pandas
python-dotenv
pytest
```

- [ ] **Step 2: Create `.env` credentials template**

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
POSTGRES_USER=pipeline
POSTGRES_PASSWORD=pipeline
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 4: Create package markers**

Create `pipeline/__init__.py` as an empty file.
Create `tests/__init__.py` as an empty file.

- [ ] **Step 5: Add `.superpowers/` to `.gitignore`**

Append to the existing `.gitignore`:
```
# Visual companion brainstorming sessions
.superpowers/
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: no errors, all packages install successfully.

- [ ] **Step 7: Start PostgreSQL container**

```bash
docker compose up -d
```

Expected output includes `Container basket-craft-pipeline-postgres-1  Started`.

Verify it's running:
```bash
docker compose ps
```

Expected: postgres service shows `running`.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .env docker-compose.yml pipeline/__init__.py tests/__init__.py .gitignore
git commit -m "chore: project scaffolding — deps, docker, env template"
```

---

## Task 2: Database Engine Factory

**Files:**
- Create: `pipeline/db.py`

- [ ] **Step 1: Create `pipeline/db.py`**

```python
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def get_mysql_engine():
    url = (
        "mysql+pymysql://{user}:{password}@{host}:{port}/{db}".format(
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            host=os.environ["MYSQL_HOST"],
            port=os.environ.get("MYSQL_PORT", "3306"),
            db=os.environ["MYSQL_DB"],
        )
    )
    return create_engine(url)


def get_postgres_engine():
    url = (
        "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ["POSTGRES_HOST"],
            port=os.environ.get("POSTGRES_PORT", "5432"),
            db=os.environ["POSTGRES_DB"],
        )
    )
    return create_engine(url)
```

- [ ] **Step 2: Verify PostgreSQL engine connects**

Open a Python shell:
```python
from pipeline.db import get_postgres_engine
engine = get_postgres_engine()
with engine.connect() as conn:
    print("Connected OK")
```

Expected: `Connected OK` with no exceptions. (MySQL engine cannot be tested until you have real credentials.)

- [ ] **Step 3: Commit**

```bash
git add pipeline/db.py
git commit -m "feat: SQLAlchemy engine factories for MySQL and PostgreSQL"
```

---

## Task 3: Extract Module

**Files:**
- Create: `pipeline/extract.py`

- [ ] **Step 1: Create `pipeline/extract.py`**

```python
import pandas as pd

TABLES = ["orders", "order_items", "products", "categories"]


def extract(engine):
    """Read all four source tables from MySQL. Returns a dict of DataFrames."""
    return {table: pd.read_sql_table(table, engine) for table in TABLES}
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/extract.py
git commit -m "feat: extract phase — read 4 MySQL tables into DataFrames"
```

---

## Task 4: Load Staging Module

**Files:**
- Create: `pipeline/load_staging.py`

- [ ] **Step 1: Create `pipeline/load_staging.py`**

```python
from sqlalchemy import text


def load_staging(dataframes, engine):
    """
    Write raw DataFrames into the staging schema, replacing all existing data.

    Args:
        dataframes: dict mapping table name → DataFrame (from extract())
        engine: SQLAlchemy engine connected to PostgreSQL
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.commit()

    for name, df in dataframes.items():
        df.to_sql(name, engine, schema="staging", if_exists="replace", index=False)
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/load_staging.py
git commit -m "feat: load staging phase — write raw DataFrames to PostgreSQL staging schema"
```

---

## Task 5: Transform Module (TDD)

**Files:**
- Create: `tests/test_transform.py`
- Create: `pipeline/transform.py`

- [ ] **Step 1: Write the failing tests in `tests/test_transform.py`**

```python
import pandas as pd
from pipeline.transform import transform


def test_revenue_order_count_and_aov_by_month_and_category():
    """
    Verify transform correctly aggregates by month and category.

    Setup:
      - Order 1 (Jan): product 10 (qty 2 × $50) + product 11 (qty 1 × $30) = $130, Wicker Baskets
      - Order 2 (Jan): product 10 (qty 3 × $50) = $150, Wicker Baskets
      - Order 3 (Feb): product 12 (qty 1 × $100) = $100, Gift Sets

    Expected:
      Jan / Wicker Baskets: total_revenue=280.0, order_count=2, avg_order_value=140.0
      Feb / Gift Sets:      total_revenue=100.0, order_count=1, avg_order_value=100.0
    """
    orders = pd.DataFrame({
        "order_id":   [1, 2, 3],
        "order_date": pd.to_datetime(["2025-01-10", "2025-01-20", "2025-02-05"]),
    })
    order_items = pd.DataFrame({
        "order_id":   [1,    1,    2,    3],
        "product_id": [10,   11,   10,   12],
        "quantity":   [2,    1,    3,    1],
        "unit_price": [50.0, 30.0, 50.0, 100.0],
    })
    products = pd.DataFrame({
        "product_id":  [10, 11, 12],
        "category_id": [1,  1,  2],
    })
    categories = pd.DataFrame({
        "category_id": [1,               2],
        "name":        ["Wicker Baskets", "Gift Sets"],
    })

    result = transform(orders, order_items, products, categories)

    jan_wicker = result.loc[
        (result["order_month"] == pd.Timestamp("2025-01-01")) &
        (result["category_name"] == "Wicker Baskets")
    ].iloc[0]
    assert jan_wicker["total_revenue"] == 280.0
    assert jan_wicker["order_count"] == 2
    assert jan_wicker["avg_order_value"] == 140.0

    feb_gift = result.loc[
        (result["order_month"] == pd.Timestamp("2025-02-01")) &
        (result["category_name"] == "Gift Sets")
    ].iloc[0]
    assert feb_gift["total_revenue"] == 100.0
    assert feb_gift["order_count"] == 1
    assert feb_gift["avg_order_value"] == 100.0


def test_order_count_counts_distinct_orders_not_line_items():
    """
    Verify that one order with 3 items in the same category counts as 1 order,
    not 3. This guards against the common bug of using len() instead of nunique().
    """
    orders = pd.DataFrame({
        "order_id":   [1],
        "order_date": pd.to_datetime(["2025-03-15"]),
    })
    order_items = pd.DataFrame({
        "order_id":   [1,    1,    1],
        "product_id": [10,   11,   12],
        "quantity":   [1,    1,    1],
        "unit_price": [20.0, 30.0, 50.0],
    })
    products = pd.DataFrame({
        "product_id":  [10, 11, 12],
        "category_id": [1,  1,  1],
    })
    categories = pd.DataFrame({
        "category_id": [1],
        "name":        ["Storage"],
    })

    result = transform(orders, order_items, products, categories)

    row = result.iloc[0]
    assert row["order_count"] == 1        # one order, not three line items
    assert row["total_revenue"] == 100.0
    assert row["avg_order_value"] == 100.0
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_transform.py -v
```

Expected: `ImportError: cannot import name 'transform' from 'pipeline.transform'` (module does not exist yet).

- [ ] **Step 3: Create `pipeline/transform.py`**

```python
import pandas as pd
from sqlalchemy import text


def transform(orders, order_items, products, categories):
    """
    Join and aggregate staging DataFrames into monthly sales by category.

    Args:
        orders:      DataFrame with columns order_id, order_date
        order_items: DataFrame with columns order_id, product_id, quantity, unit_price
        products:    DataFrame with columns product_id, category_id
        categories:  DataFrame with columns category_id, name

    Returns:
        DataFrame with columns:
            order_month, category_name, total_revenue, order_count, avg_order_value
    """
    df = order_items.merge(orders[["order_id", "order_date"]], on="order_id")
    df = df.merge(products[["product_id", "category_id"]], on="product_id")
    df = df.merge(
        categories[["category_id", "name"]].rename(columns={"name": "category_name"}),
        on="category_id",
    )

    df["line_revenue"] = df["quantity"] * df["unit_price"]
    df["order_month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()

    result = (
        df.groupby(["order_month", "category_name"])
        .agg(
            total_revenue=("line_revenue", "sum"),
            order_count=("order_id", "nunique"),
        )
        .reset_index()
    )
    result["avg_order_value"] = result["total_revenue"] / result["order_count"]
    return result


def run_transform(engine):
    """
    Read staging tables from PostgreSQL, run transform(), write to analytics schema.

    Args:
        engine: SQLAlchemy engine connected to PostgreSQL
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
        conn.commit()

    orders = pd.read_sql_table("orders", engine, schema="staging")
    order_items = pd.read_sql_table("order_items", engine, schema="staging")
    products = pd.read_sql_table("products", engine, schema="staging")
    categories = pd.read_sql_table("categories", engine, schema="staging")

    result = transform(orders, order_items, products, categories)
    result.to_sql(
        "monthly_sales_by_category",
        engine,
        schema="analytics",
        if_exists="replace",
        index=False,
    )
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_transform.py -v
```

Expected output:
```
tests/test_transform.py::test_revenue_order_count_and_aov_by_month_and_category PASSED
tests/test_transform.py::test_order_count_counts_distinct_orders_not_line_items PASSED

2 passed in 0.XXs
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_transform.py pipeline/transform.py
git commit -m "feat: transform phase with unit tests — monthly sales aggregation by category"
```

---

## Task 6: Entry Point

**Files:**
- Create: `run_pipeline.py`

- [ ] **Step 1: Create `run_pipeline.py`**

```python
import argparse
import sys

from pipeline.db import get_mysql_engine, get_postgres_engine
from pipeline.extract import extract
from pipeline.load_staging import load_staging
from pipeline.transform import run_transform


def main():
    parser = argparse.ArgumentParser(description="Basket Craft data pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test connections and print row counts without writing to PostgreSQL",
    )
    args = parser.parse_args()

    mysql_engine = get_mysql_engine()
    pg_engine = get_postgres_engine()

    if args.dry_run:
        print("Dry run — testing connections...")
        try:
            dataframes = extract(mysql_engine)
            for name, df in dataframes.items():
                print(f"  MySQL {name}: {len(df):,} rows")
        except Exception as e:
            print(f"  MySQL connection failed: {e}")
            sys.exit(1)
        try:
            with pg_engine.connect():
                pass
            print("  PostgreSQL connection OK")
        except Exception as e:
            print(f"  PostgreSQL connection failed: {e}")
            sys.exit(1)
        print("Dry run complete. Nothing written.")
        return

    print("Phase 1: Extracting from MySQL...")
    try:
        dataframes = extract(mysql_engine)
        for name, df in dataframes.items():
            print(f"  {name}: {len(df):,} rows")
    except Exception as e:
        print(f"Extract failed: {e}")
        sys.exit(1)

    print("Phase 2: Loading to PostgreSQL staging...")
    try:
        load_staging(dataframes, pg_engine)
        print("  Staging tables written.")
    except Exception as e:
        print(f"Stage failed: {e}")
        sys.exit(1)

    print("Phase 3: Transforming and loading analytics...")
    try:
        run_transform(pg_engine)
        print("  analytics.monthly_sales_by_category written.")
    except Exception as e:
        print(f"Transform failed: {e}")
        sys.exit(1)

    print("Pipeline complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the dry-run flag works against PostgreSQL**

Fill in your `.env` with real PostgreSQL credentials (the Docker container you started in Task 1 uses `pipeline` / `pipeline` by default), then run:

```bash
python run_pipeline.py --dry-run
```

Expected (MySQL will fail until you have real credentials — that's fine for now):
```
Dry run — testing connections...
  MySQL connection failed: ...
```

Once MySQL credentials are available, expected full output:
```
Dry run — testing connections...
  MySQL orders: X rows
  MySQL order_items: X rows
  MySQL products: X rows
  MySQL categories: X rows
  PostgreSQL connection OK
Dry run complete. Nothing written.
```

- [ ] **Step 3: Run the full pipeline once MySQL credentials are available**

```bash
python run_pipeline.py
```

Expected:
```
Phase 1: Extracting from MySQL...
  orders: X rows
  order_items: X rows
  products: X rows
  categories: X rows
Phase 2: Loading to PostgreSQL staging...
  Staging tables written.
Phase 3: Transforming and loading analytics...
  analytics.monthly_sales_by_category written.
Pipeline complete.
```

- [ ] **Step 4: Verify output in PostgreSQL**

```bash
docker exec -it basket-craft-pipeline-postgres-1 psql -U pipeline -d basket_craft_dw -c \
  "SELECT order_month, category_name, total_revenue, order_count, avg_order_value FROM analytics.monthly_sales_by_category ORDER BY order_month, category_name LIMIT 10;"
```

Expected: rows with populated `order_month`, `category_name`, numeric `total_revenue`, integer `order_count`, numeric `avg_order_value`.

- [ ] **Step 5: Commit**

```bash
git add run_pipeline.py
git commit -m "feat: pipeline entry point with --dry-run flag"
```
