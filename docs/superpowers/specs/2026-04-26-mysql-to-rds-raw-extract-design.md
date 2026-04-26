# MySQL → RDS Raw Extract — Design Spec

**Date:** 2026-04-26
**Status:** Approved

## Goal

Extract every table from the Basket Craft MySQL database and load them as-is into the `staging` schema of the AWS RDS PostgreSQL instance. No transformations. Existing pipeline files are not modified.

## New Files

| File | Purpose |
|------|---------|
| `pipeline/extract_all.py` | Discovers all MySQL tables dynamically via `inspect()`, returns `dict[str, DataFrame]` |
| `pipeline/load_rds.py` | Creates `staging` schema on RDS if absent, writes each DataFrame with `if_exists="replace"` |
| `run_extract_rds.py` | Entry point — wires engines, calls extract_all + load_rds, prints progress |

## Modified Files

| File | Change |
|------|--------|
| `pipeline/db.py` | Add `get_rds_engine()` reading `RDS_HOST`, `RDS_PORT`, `RDS_USER`, `RDS_PASSWORD`, `RDS_DATABASE` from `.env` |

**No other existing files are changed.**

## Architecture

```
run_extract_rds.py
  ├── db.get_mysql_engine()       ← reads MYSQL_* from .env
  ├── db.get_rds_engine()         ← reads RDS_* from .env  [NEW]
  ├── extract_all.extract_all()   ← inspect + pd.read_sql_table for every table  [NEW]
  └── load_rds.load_rds()         ← staging schema + df.to_sql per table  [NEW]
```

## Data Flow

1. Load `.env` via `python-dotenv`
2. Build MySQL engine and RDS engine; fail fast if either connection fails
3. `extract_all`: call `inspect(mysql_engine).get_table_names()` to get all table names, then `pd.read_sql_table(name, mysql_engine)` for each
4. `load_rds`: `CREATE SCHEMA IF NOT EXISTS staging`, then `df.to_sql(name, rds_engine, schema="staging", if_exists="replace", index=False)` for each table
5. Print `  <table>: <n> rows` as each table loads; print a final summary

## Error Handling

- MySQL or RDS connection failure at startup → print error, `sys.exit(1)`
- Individual table load failure → print table name + error, continue to next table (partial run is better than no run)
- `--dry-run` flag → test both connections, print all table names + row counts, write nothing to RDS

## Credentials

Read exclusively from `.env`. The file already contains separate `RDS_*` keys:

```
RDS_HOST=
RDS_PORT=
RDS_USER=
RDS_PASSWORD=
RDS_DATABASE=
```

`get_rds_engine()` in `db.py` follows the same pattern as the existing `get_postgres_engine()`.

## Testing Strategy

- `--dry-run` is the primary verification path (live connection test + row count preview)
- Post-run summary line per table confirms counts match MySQL source
- No unit tests added — no pure logic to isolate (unlike `transform.py`)

## Out of Scope

- Schema inference / type mapping overrides
- Incremental / CDC loading
- Any transformation or aggregation
- Changes to the existing `run_pipeline.py` flow
