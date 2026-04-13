import pandas as pd
from pipeline.transform import transform


def test_revenue_order_count_and_aov_by_month_and_product():
    """
    Verify transform correctly aggregates by month and product.

    Real schema: no categories table; product_name is the grouping dimension.
    Revenue = price_usd per order_items row (no quantity column).
    Date = created_at timestamp on the orders table.

    Setup:
      - Order 1 (Jan): Original Gift Basket ($49.99) + Valentine's Gift Basket ($59.99) = $109.98
      - Order 2 (Jan): Original Gift Basket ($49.99)
      - Order 3 (Feb): Valentine's Gift Basket ($59.99)

    Expected:
      Jan / The Original Gift Basket:    total_revenue=99.98,  order_count=2, avg_order_value=49.99
      Jan / The Valentine's Gift Basket: total_revenue=59.99,  order_count=1, avg_order_value=59.99
      Feb / The Valentine's Gift Basket: total_revenue=59.99,  order_count=1, avg_order_value=59.99
    """
    orders = pd.DataFrame({
        "order_id":   [1, 2, 3],
        "created_at": pd.to_datetime(["2025-01-10", "2025-01-20", "2025-02-05"]),
    })
    order_items = pd.DataFrame({
        "order_id":   [1,     1,     2,     3],
        "product_id": [1,     2,     1,     2],
        "price_usd":  [49.99, 59.99, 49.99, 59.99],
    })
    products = pd.DataFrame({
        "product_id":   [1,                          2],
        "product_name": ["The Original Gift Basket", "The Valentine's Gift Basket"],
    })

    result = transform(orders, order_items, products)

    assert set(result.columns) == {"order_month", "category_name", "total_revenue", "order_count", "avg_order_value"}

    jan_original = result.loc[
        (result["order_month"] == pd.Timestamp("2025-01-01")) &
        (result["category_name"] == "The Original Gift Basket")
    ].iloc[0]
    assert round(jan_original["total_revenue"], 2) == 99.98
    assert jan_original["order_count"] == 2
    assert round(jan_original["avg_order_value"], 2) == 49.99

    jan_valentine = result.loc[
        (result["order_month"] == pd.Timestamp("2025-01-01")) &
        (result["category_name"] == "The Valentine's Gift Basket")
    ].iloc[0]
    assert round(jan_valentine["total_revenue"], 2) == 59.99
    assert jan_valentine["order_count"] == 1
    assert round(jan_valentine["avg_order_value"], 2) == 59.99


def test_order_count_counts_distinct_orders_not_line_items():
    """
    Verify that one order with 3 items of the same product
    counts as 1 order, not 3. Guards against using len() instead of nunique().
    """
    orders = pd.DataFrame({
        "order_id":   [1],
        "created_at": pd.to_datetime(["2025-03-15"]),
    })
    order_items = pd.DataFrame({
        "order_id":   [1,     1,     1],
        "product_id": [1,     1,     1],
        "price_usd":  [20.00, 30.00, 50.00],
    })
    products = pd.DataFrame({
        "product_id":   [1],
        "product_name": ["The Original Gift Basket"],
    })

    result = transform(orders, order_items, products)

    row = result.iloc[0]
    assert row["order_count"] == 1       # one order, not three line items
    assert round(row["total_revenue"], 2) == 100.0
    assert round(row["avg_order_value"], 2) == 100.0
