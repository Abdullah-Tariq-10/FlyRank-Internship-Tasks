from datetime import datetime, timedelta
import random
import sqlite3

DB_FILE = "report.db"

CUSTOMERS = [
    "Alice Smith",
    "Bob Jones",
    "Charlie Brown",
    "Diana Prince",
    "Evan Wright",
    "Fiona Gallagher",
    "George Clark",
    "Hannah Abbott",
]

PRODUCTS = [
    "Mechanical Keyboard",
    "Wireless Mouse",
    "USB-C Dock",
    "Noise Cancelling Headphones",
    "Monitor Stand",
    "Desk Mat",
]


def seed_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. Ensure table schema exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 2. Idempotency reset: clear all rows first so running twice leaves exactly 200 rows
    cursor.execute("DELETE FROM orders")

    # 3. Generate 200 orders over the past 30 days
    orders = []
    base_date = datetime.now()

    for _ in range(200):
        customer = random.choice(CUSTOMERS)
        product = random.choice(PRODUCTS)
        amount = round(random.uniform(5.0, 200.0), 2)

        random_days = random.randint(0, 29)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        order_date = base_date - timedelta(
            days=random_days, hours=random_hours, minutes=random_minutes
        )
        created_at_str = order_date.strftime("%Y-%m-%d %H:%M:%S")

        orders.append((customer, product, amount, created_at_str))

    cursor.executemany(
        """
        INSERT INTO orders (customer, product, amount, created_at)
        VALUES (?, ?, ?, ?)
    """,
        orders,
    )

    conn.commit()

    # 4. Verification count query
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"Database seeded successfully. Total rows in 'orders': {count}")


if __name__ == "__main__":
    seed_database()