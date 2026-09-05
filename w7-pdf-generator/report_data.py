from datetime import datetime, timedelta
import json
import sqlite3

DB_FILE = "report.db"


def get_report_data(days: int = 30):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    window_cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    # 1. Total orders & Total revenue within window
    cursor.execute("""
        SELECT COUNT(*) AS total_orders, SUM(amount) AS total_revenue 
        FROM orders 
        WHERE created_at >= ?
    """, (window_cutoff,))
    totals = cursor.fetchone()
    total_orders = totals["total_orders"] or 0
    total_revenue = round(totals["total_revenue"] or 0.0, 2)

    # 2. Top 5 products by revenue within window
    cursor.execute("""
        SELECT product, ROUND(SUM(amount), 2) AS revenue, COUNT(*) AS count
        FROM orders
        WHERE created_at >= ?
        GROUP BY product
        ORDER BY revenue DESC
        LIMIT 5
    """, (window_cutoff,))
    top_products = [dict(row) for row in cursor.fetchall()]

    # 3. Daily breakdown within window
    cursor.execute("""
        SELECT strftime('%Y-%m-%d', created_at) AS day,
               COUNT(*) AS order_count,
               ROUND(SUM(amount), 2) AS day_revenue
        FROM orders
        WHERE created_at >= ?
        GROUP BY day
        ORDER BY day ASC
    """, (window_cutoff,))
    daily_orders = [dict(row) for row in cursor.fetchall()]

    # 4. Filtered raw orders
    cursor.execute("""
        SELECT id, customer, product, amount, created_at
        FROM orders
        WHERE created_at >= ?
        ORDER BY created_at DESC
    """, (window_cutoff,))
    all_orders = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "summary": {
            "window_days": days,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "top_products": top_products,
        "daily_breakdown": daily_orders,
        "raw_orders_count": len(all_orders),
        "raw_orders": all_orders,
    }


if __name__ == "__main__":
    data = get_report_data(days=30)
    preview = {k: v for k, v in data.items() if k != "raw_orders"}
    print(json.dumps(preview, indent=2))