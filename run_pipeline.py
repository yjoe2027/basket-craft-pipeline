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
