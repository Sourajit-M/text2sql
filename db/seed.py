"""
Seed script — populates the ecommerce database with realistic synthetic data.
Optimized with bulk multi-row inserts for fast execution over remote connections (Neon, Supabase).
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
    print("Connecting to database...")
    with engine.begin() as conn:
        print("Resetting tables...")
        conn.execute(text("TRUNCATE order_items, orders, products, categories, customers RESTART IDENTITY CASCADE"))

        # 1. Bulk insert categories
        print("Inserting categories...")
        cat_values = ", ".join(f"('{c}')" for c in CATEGORIES)
        conn.execute(text(f"INSERT INTO categories (name) VALUES {cat_values}"))

        rows = conn.execute(text("SELECT category_id, name FROM categories")).fetchall()
        cat_map = {r.name: r.category_id for r in rows}

        # 2. Bulk insert products
        print("Inserting products...")
        prod_values = ", ".join(
            f"('{pname}', {cat_map[pcat]}, {pprice}, {pstock})"
            for pname, pcat, pprice, pstock in PRODUCTS
        )
        conn.execute(text(f"INSERT INTO products (name, category_id, price, stock) VALUES {prod_values}"))

        prod_rows = conn.execute(text("SELECT product_id, price FROM products")).fetchall()
        prod_ids = [(r.product_id, float(r.price)) for r in prod_rows]

        # 3. Bulk insert customers
        print("Inserting customers...")
        cust_values = ", ".join(
            f"('{cname}', '{cemail}', '{ccity}')"
            for cname, cemail, ccity in CUSTOMERS
        )
        conn.execute(text(f"INSERT INTO customers (name, email, city) VALUES {cust_values}"))

        cust_rows = conn.execute(text("SELECT customer_id FROM customers")).fetchall()
        cust_ids = [r.customer_id for r in cust_rows]

        # 4. Generate orders and order_items in memory
        print("Generating orders and items...")
        now = datetime.utcnow()
        random.seed(42)

        raw_orders = []
        for _ in range(150):
            cust_id = random.choice(cust_ids)
            days_ago = random.choices(
                range(1, 550),
                weights=[3 if d <= 30 else 2 if d <= 365 else 1 for d in range(1, 550)],
            )[0]
            ordered_at = (now - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            status = random.choices(["completed", "pending", "cancelled"], weights=[80, 10, 10])[0]
            raw_orders.append((cust_id, status, ordered_at))

        # Single bulk insert for all orders
        order_tuples = ", ".join(f"({c}, '{s}', '{o}')" for c, s, o in raw_orders)
        result = conn.execute(text(f"INSERT INTO orders (customer_id, status, ordered_at) VALUES {order_tuples} RETURNING order_id"))
        order_ids = [r[0] for r in result.fetchall()]

        # Single bulk insert for all order items
        raw_items = []
        for order_id in order_ids:
            items = random.sample(prod_ids, k=random.randint(1, 4))
            for pid, uprice in items:
                qty = random.randint(1, 5)
                raw_items.append((order_id, pid, qty, uprice))

        item_tuples = ", ".join(f"({o}, {p}, {q}, {u})" for o, p, q, u in raw_items)
        conn.execute(text(f"INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES {item_tuples}"))

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed()
