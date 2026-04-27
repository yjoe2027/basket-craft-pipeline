import pandas as pd
from sqlalchemy import inspect


def extract_all(engine):
    """Discover every table in the MySQL database and read each into a DataFrame."""
    table_names = inspect(engine).get_table_names()
    with engine.connect() as conn:
        return {name: pd.read_sql_table(name, conn) for name in table_names}
