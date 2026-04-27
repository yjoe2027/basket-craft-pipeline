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
