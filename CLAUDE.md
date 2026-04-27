Use a Python virtual environment to manage dependencies.

## Pipeline scripts

- `run_pipeline.py` — original pipeline: extracts 3 tables from MySQL (orders, order_items, products), loads them into the local Docker PostgreSQL `staging` schema, then writes an analytics aggregate to `analytics.monthly_sales_by_category`.
- `run_extract_rds.py` — standalone raw extract: discovers **all** MySQL tables dynamically and loads them as-is into the `staging` schema on AWS RDS PostgreSQL. No transformations. Run with `--dry-run` to test connections and print row counts without writing.

## Databases

- **MySQL source** — Basket Craft production database. Credentials in `.env` under `MYSQL_*`.
- **Local PostgreSQL** — Docker-based, used by `run_pipeline.py`. Credentials in `.env` under `POSTGRES_*`.
- **AWS RDS PostgreSQL** — used by `run_extract_rds.py`. Credentials in `.env` under `RDS_*`. All 8 source tables land in the `staging` schema.

## Running the RDS extract

```bash
# Test connections only (no writes)
python run_extract_rds.py --dry-run

# Full load (idempotent — replaces staging tables each run)
python run_extract_rds.py
```
