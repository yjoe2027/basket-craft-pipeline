# MySQL → RDS Raw Extract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a standalone script that dynamically discovers all MySQL tables and loads them as-is into the `staging` schema of AWS RDS PostgreSQL, without touching the existing pipeline.

**Architecture:** A thin entry point (`run_extract_rds.py`) wires together two new modules — `extract_all.py` (SQLAlchemy `inspect` for dynamic table discovery + pandas reads) and `load_rds.py` (staging schema creation + `df.to_sql` per table). `db.py` gains a single new `get_rds_engine()` function; no other existing files are modified.

**Tech Stack:** Python 3, SQLAlchemy, pandas, pymysql, psycopg2-binary, python-dotenv (all already in `requirements.txt`)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `pipeline/db.py` | Add `get_rds_engine()` reading `RDS_*` env vars |
| Create | `pipeline/extract_all.py` | Discover all MySQL tables; return `dict[str, DataFrame]` |
| Create | `pipeline/load_rds.py` | Write DataFrames to `staging` schema on RDS with per-table error isolation |
| Create | `run_extract_rds.py` | Entry point: parse args, connect, extract, load, print summary |

---

### Task 1: Add `get_rds_engine()` to `pipeline/db.py`

**Files:**
- Modify: `pipeline/db.py`

- [ ] **Step 1: Open `pipeline/db.py` and read its current contents**

  Verify the file ends after `get_postgres_engine()`. Confirm `os` and `create_engine` are already imported.

- [ ] **Step 2: Append `get_rds_engine()` to `pipeline/db.py`**

  Add the following function at the bottom of the file (after `get_postgres_engine()`):

  ```python
  def get_rds_engine():
      url = (
          "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
              user=os.environ["RDS_USER"],
              password=os.environ["RDS_PASSWORD"],
              host=os.environ["RDS_HOST"],
              port=os.environ.get("RDS_PORT", "5432"),
              db=os.environ["RDS_DATABASE"],
          )
      )
      return create_engine(url)
  ```

- [ ] **Step 3: Verify the import works**

  Run from the project root (virtual environment must be active):

  ```bash
  python -c "from pipeline.db import get_rds_engine; print('OK')"
  ```

  Expected output: `OK`

- [ ] **Step 4: Commit**

  ```bash
  git add pipeline/db.py
  git commit -m "feat: add get_rds_engine() to db.py"
  ```

---

### Task 2: Create `pipeline/extract_all.py`

**Files:**
- Create: `pipeline/extract_all.py`

- [ ] **Step 1: Create the file**

  ```python
  import pandas as pd
  from sqlalchemy import inspect


  def extract_all(engine):
      """Discover every table in the MySQL database and read each into a DataFrame."""
      table_names = inspect(engine).get_table_names()
      return {name: pd.read_sql_table(name, engine) for name in table_names}
  ```

- [ ] **Step 2: Verify the import works**

  ```bash
  python -c "from pipeline.extract_all import extract_all; print('OK')"
  ```

  Expected output: `OK`

- [ ] **Step 3: Commit**

  ```bash
  git add pipeline/extract_all.py
  git commit -m "feat: add extract_all() with dynamic table discovery"
  ```

---

### Task 3: Create `pipeline/load_rds.py`

**Files:**
- Create: `pipeline/load_rds.py`

- [ ] **Step 1: Create the file**

  ```python
  from sqlalchemy import text


  def load_rds(dataframes, engine):
      """
      Write raw DataFrames into the staging schema on RDS, replacing all existing data.

      Returns a list of table names that failed to load (empty list on full success).
      """
      with engine.connect() as conn:
          conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
          conn.commit()

      failed = []
      for name, df in dataframes.items():
          try:
              df.to_sql(name, engine, schema="staging", if_exists="replace", index=False)
              print(f"  {name}: {len(df):,} rows")
          except Exception as e:
              print(f"  {name}: FAILED — {e}")
              failed.append(name)

      return failed
  ```

- [ ] **Step 2: Verify the import works**

  ```bash
  python -c "from pipeline.load_rds import load_rds; print('OK')"
  ```

  Expected output: `OK`

- [ ] **Step 3: Commit**

  ```bash
  git add pipeline/load_rds.py
  git commit -m "feat: add load_rds() with staging schema and per-table error isolation"
  ```

---

### Task 4: Create `run_extract_rds.py`

**Files:**
- Create: `run_extract_rds.py`

- [ ] **Step 1: Create the entry point**

  ```python
  import argparse
  import sys

  from pipeline.db import get_mysql_engine, get_rds_engine
  from pipeline.extract_all import extract_all
  from pipeline.load_rds import load_rds


  def main():
      parser = argparse.ArgumentParser(
          description="Extract all MySQL tables to AWS RDS PostgreSQL (staging schema)"
      )
      parser.add_argument(
          "--dry-run",
          action="store_true",
          help="Test connections and print table names/row counts without writing to RDS",
      )
      args = parser.parse_args()

      print("Extracting from MySQL...")
      try:
          mysql_engine = get_mysql_engine()
          dataframes = extract_all(mysql_engine)
          for name, df in dataframes.items():
              print(f"  {name}: {len(df):,} rows")
      except Exception as e:
          print(f"MySQL failed: {e}")
          sys.exit(1)

      print("Connecting to RDS...")
      try:
          rds_engine = get_rds_engine()
          with rds_engine.connect():
              pass
          print("  RDS connection OK")
      except Exception as e:
          print(f"RDS connection failed: {e}")
          sys.exit(1)

      if args.dry_run:
          print(f"\nDry run complete. {len(dataframes)} tables found, nothing written.")
          return

      print("Loading to RDS staging...")
      failed = load_rds(dataframes, rds_engine)

      total = len(dataframes)
      loaded = total - len(failed)
      print(f"\nDone. {loaded}/{total} tables loaded to staging schema.")
      if failed:
          print(f"Failed tables: {', '.join(failed)}")
          sys.exit(1)


  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 2: Verify the import works**

  ```bash
  python -c "import run_extract_rds; print('OK')"
  ```

  Expected output: `OK`

- [ ] **Step 3: Commit**

  ```bash
  git add run_extract_rds.py
  git commit -m "feat: add run_extract_rds.py entry point with --dry-run flag"
  ```

---

### Task 5: Verify with `--dry-run`

**Files:** none (verification only)

- [ ] **Step 1: Run dry-run to confirm both connections work and all tables are discovered**

  ```bash
  python run_extract_rds.py --dry-run
  ```

  Expected output (table names and counts will vary):
  ```
  Extracting from MySQL...
    orders: 1,234 rows
    order_items: 5,678 rows
    products: 42 rows
    ...
  Connecting to RDS...
    RDS connection OK

  Dry run complete. N tables found, nothing written.
  ```

  If MySQL fails: check `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD` in `.env`.
  If RDS fails: check `RDS_HOST`, `RDS_PORT`, `RDS_USER`, `RDS_PASSWORD`, `RDS_DATABASE` in `.env`.

- [ ] **Step 2: Run the full load once dry-run passes**

  ```bash
  python run_extract_rds.py
  ```

  Expected output:
  ```
  Extracting from MySQL...
    orders: 1,234 rows
    ...
  Connecting to RDS...
    RDS connection OK
  Loading to RDS staging...
    orders: 1,234 rows
    ...

  Done. N/N tables loaded to staging schema.
  ```

  Any `FAILED` lines will include the table name and exception — fix the specific table or re-run; other tables are unaffected.
