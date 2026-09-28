"""
Seed script — populates the ecommerce database with realistic synthetic data.
Run once after `docker compose up -d`:
    uv run python db/seed.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from app.config import DATABASE_URL
from datetime import datetime, timedelta
import random

engine = create_engine(DATABASE_URL)

CATEGORIES = ["Electronics", "Clothing", "Books", "Home & Kitchen", "Sports"]

PRODUCTS = [
    ("Wireless Headphones",     "Electronics",    89.99, 50),
    ("Smartphone Stand",        "Electronics",    19.99, 120),
    ("USB-C Hub",               "Electronics",    34.99, 80),
    ("Running Shoes",           "Clothing",       59.99, 60),
    ("Yoga Pants",              "Clothing",       39.99, 90),
    ("Winter Jacket",           "Clothing",      119.99, 30),
    ("Python Programming Book", "Books",          29.99, 200),
    ("Data Science Handbook",   "Books",          34.99, 150),
    ("Coffee Maker",            "Home & Kitchen", 49.99, 40),
    ("Air Fryer",               "Home & Kitchen", 79.99, 35),
    ("Resistance Bands",        "Sports",         14.99, 200),
    ("Dumbbells Set",           "Sports",         69.99, 25),
]

CUSTOMERS = [
    ("Alice Johnson", "alice@example.com",   "New York"),
    ("Bob Smith",     "bob@example.com",     "Los Angeles"),
    ("Carol White",   "carol@example.com",   "Chicago"),
    ("David Brown",   "david@example.com",   "Houston"),
    ("Eve Davis",     "eve@example.com",     "Phoenix"),
    ("Frank Miller",  "frank@example.com",   "Philadelphia"),
    ("Grace Wilson",  "grace@example.com",   "San Antonio"),
    ("Henry Moore",   "henry@example.com",   "San Diego"),
    ("Ivy Taylor",    "ivy@example.com",     "Dallas"),
    ("Jack Anderson", "jack@example.com",    "San Jose"),
]


def seed():
    with engine.begin() as conn:
        # Truncate in reverse FK order
        conn.execute(text("TRUNCATE order_items, orders, products, categories, customers RESTART IDENTITY CASCADE"))

        # Insert categories
        for cat in CATEGORIES:
            conn.execute(text("INSERT INTO categories (name) VALUES (:n)"), {"n": cat})

        # Build category_id map
        rows = conn.execute(text("SELECT category_id, name FROM categories")).fetchall()
        cat_map = {r.name: r.category_id for r in rows}

        # Insert products
        for pname, pcat, pprice, pstock in PRODUCTS:
            conn.execute(
                text("INSERT INTO products (name, category_id, price, stock) VALUES (:n, :c, :p, :s)"),
                {"n": pname, "c": cat_map[pcat], "p": pprice, "s": pstock},
            )

        # Build product_id list
        prod_rows = conn.execute(text("SELECT product_id, price FROM products")).fetchall()
        prod_ids = [(r.product_id, float(r.price)) for r in prod_rows]

        # Insert customers
        for cname, cemail, ccity in CUSTOMERS:
            conn.execute(
                text("INSERT INTO customers (name, email, city) VALUES (:n, :e, :c)"),
                {"n": cname, "e": cemail, "c": ccity},
            )

        cust_rows = conn.execute(text("SELECT customer_id FROM customers")).fetchall()
        cust_ids = [r.customer_id for r in cust_rows]

        # Insert orders + order_items (last 90 days, weighted toward last 30)
        now = datetime.utcnow()
        random.seed(42)

        for _ in range(300):
            cust_id = random.choice(cust_ids)
            # Spread over last 18 months; weight recent 30 days 3x
            days_ago = random.choices(
                range(1, 550),
                weights=[3 if d <= 30 else 2 if d <= 365 else 1 for d in range(1, 550)],
            )[0]
            ordered_at = now - timedelta(days=days_ago)
            status = random.choices(["completed", "pending", "cancelled"], weights=[80, 10, 10])[0]

            result = conn.execute(
                text("INSERT INTO orders (customer_id, status, ordered_at) VALUES (:c, :s, :o) RETURNING order_id"),
                {"c": cust_id, "s": status, "o": ordered_at},
            )
            order_id = result.fetchone()[0]

            # 1–4 items per order
            items = random.sample(prod_ids, k=random.randint(1, 4))
            for pid, uprice in items:
                qty = random.randint(1, 5)
                conn.execute(
                    text("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (:o, :p, :q, :u)"),
                    {"o": order_id, "p": pid, "q": qty, "u": uprice},
                )

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed()
