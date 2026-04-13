import pandas as pd
from pipeline.transform import transform


def test_revenue_order_count_and_aov_by_month_and_category():
    """
    Verify transform correctly aggregates by month and category.

    Setup:
      - Order 1 (Jan): product 10 (qty 2 × $50) + product 11 (qty 1 × $30) = $130, Wicker Baskets
      - Order 2 (Jan): product 10 (qty 3 × $50) = $150, Wicker Baskets
      - Order 3 (Feb): product 12 (qty 1 × $100) = $100, Gift Sets

    Expected:
      Jan / Wicker Baskets: total_revenue=280.0, order_count=2, avg_order_value=140.0
      Feb / Gift Sets:      total_revenue=100.0, order_count=1, avg_order_value=100.0
    """
    orders = pd.DataFrame({
        "order_id":   [1, 2, 3],
        "order_date": pd.to_datetime(["2025-01-10", "2025-01-20", "2025-02-05"]),
    })
    order_items = pd.DataFrame({
        "order_id":   [1,    1,    2,    3],
        "product_id": [10,   11,   10,   12],
        "quantity":   [2,    1,    3,    1],
        "unit_price": [50.0, 30.0, 50.0, 100.0],
    })
    products = pd.DataFrame({
        "product_id":  [10, 11, 12],
        "category_id": [1,  1,  2],
    })
    categories = pd.DataFrame({
        "category_id": [1,               2],
        "name":        ["Wicker Baskets", "Gift Sets"],
    })

    result = transform(orders, order_items, products, categories)

    assert set(result.columns) == {"order_month", "category_name", "total_revenue", "order_count", "avg_order_value"}

    jan_wicker = result.loc[
        (result["order_month"] == pd.Timestamp("2025-01-01")) &
        (result["category_name"] == "Wicker Baskets")
    ].iloc[0]
    assert jan_wicker["total_revenue"] == 280.0
    assert jan_wicker["order_count"] == 2
    assert jan_wicker["avg_order_value"] == 140.0

    feb_gift = result.loc[
        (result["order_month"] == pd.Timestamp("2025-02-01")) &
        (result["category_name"] == "Gift Sets")
    ].iloc[0]
    assert feb_gift["total_revenue"] == 100.0
    assert feb_gift["order_count"] == 1
    assert feb_gift["avg_order_value"] == 100.0


def test_order_count_counts_distinct_orders_not_line_items():
    """
    Verify that one order with 3 items in the same category
    counts as 1 order, not 3. This guards against the common bug
    of using len() instead of nunique().
    """
    orders = pd.DataFrame({
        "order_id":   [1],
        "order_date": pd.to_datetime(["2025-03-15"]),
    })
    order_items = pd.DataFrame({
        "order_id":   [1,    1,    1],
        "product_id": [10,   11,   12],
        "quantity":   [1,    1,    1],
        "unit_price": [20.0, 30.0, 50.0],
    })
    products = pd.DataFrame({
        "product_id":  [10, 11, 12],
        "category_id": [1,  1,  1],
    })
    categories = pd.DataFrame({
        "category_id": [1],
        "name":        ["Storage"],
    })

    result = transform(orders, order_items, products, categories)

    row = result.iloc[0]
    assert row["order_count"] == 1        # one order, not three line items
    assert row["total_revenue"] == 100.0
    assert row["avg_order_value"] == 100.0
