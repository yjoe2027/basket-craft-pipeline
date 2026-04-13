import pandas as pd

TABLES = ["orders", "order_items", "products"]


def extract(engine):
    """Read all three source tables from MySQL. Returns a dict of DataFrames."""
    return {table: pd.read_sql_table(table, engine) for table in TABLES}
