import pandas as pd
from sqlalchemy import text


def transform(orders, order_items, products):
    """
    Join and aggregate staging DataFrames into monthly sales by product.

    Real schema notes:
        - No categories table; product_name serves as the category dimension.
        - Order date is created_at (timestamp) on the orders table.
        - Each order_items row is one item; revenue = price_usd (no quantity column).

    Args:
        orders:      DataFrame with columns order_id, created_at
        order_items: DataFrame with columns order_id, product_id, price_usd
        products:    DataFrame with columns product_id, product_name

    Returns:
        DataFrame with columns:
            order_month, category_name, total_revenue, order_count, avg_order_value
    """
    # Rename created_at on orders before merging to avoid collision with
    # order_items.created_at (both tables have this column).
    orders_slim = orders[["order_id", "created_at"]].rename(columns={"created_at": "order_date"})
    df = order_items.merge(orders_slim, on="order_id")
    df = df.merge(
        products[["product_id", "product_name"]].rename(columns={"product_name": "category_name"}),
        on="product_id",
    )

    df["order_month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()

    result = (
        df.groupby(["order_month", "category_name"])
        .agg(
            total_revenue=("price_usd", "sum"),
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

    result = transform(orders, order_items, products)
    result.to_sql(
        "monthly_sales_by_category",
        engine,
        schema="analytics",
        if_exists="replace",
        index=False,
    )
