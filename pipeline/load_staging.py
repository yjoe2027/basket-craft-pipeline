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
