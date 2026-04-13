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
    Orchestrate Phase 3: read staging tables, delegate to transform(), write analytics.

    Delegates aggregation logic to transform() to keep that function pure and
    independently testable without a database connection.

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
