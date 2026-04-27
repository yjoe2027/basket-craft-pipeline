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
