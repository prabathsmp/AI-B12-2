"""Generate a realistic, deterministic retail sales dataset (sales_2026.csv).

The data deliberately contains a story so the demo question has a clear answer:
Electronics revenue drops sharply in September vs August, driven mostly by the
South region (Earbuds X2 and Smartwatch Lite).

Run:  python sample_data/generate_sales.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 2026
ROWS = 12_480
OUT = Path(__file__).with_name("sales_2026.csv")

REGIONS = ["North", "South", "East", "West"]
CATALOG = {
    "Electronics": [("Earbuds X2", 1999), ("Smartwatch Lite", 3499), ("Power Bank 20K", 1499), ("BT Speaker Mini", 2299)],
    "Grocery": [("Millet Mix 1kg", 249), ("Cold Pressed Oil 1L", 399), ("Basmati Rice 5kg", 649), ("Green Tea 100", 299)],
    "Apparel": [("Cotton Kurta", 899), ("Denim Jeans", 1499), ("Running Tee", 599), ("Rain Jacket", 1899)],
    "Home": [("Steel Bottle", 449), ("Bedsheet Set", 1199), ("LED Lamp", 799), ("Cookware Trio", 2499)],
    "Beauty": [("Herbal Face Wash", 199), ("Sunscreen SPF50", 449), ("Hair Serum", 549), ("Lip Balm Duo", 149)],
}


def main() -> None:
    rnd = random.Random(SEED)
    start = date(2026, 1, 1)
    days = (date(2026, 12, 31) - start).days + 1
    rows = []
    for _ in range(ROWS):
        d = start + timedelta(days=rnd.randrange(days))
        region = rnd.choices(REGIONS, weights=[26, 30, 22, 22])[0]
        category = rnd.choices(list(CATALOG), weights=[24, 26, 20, 16, 14])[0]
        product, price = rnd.choice(CATALOG[category])

        units = max(1, int(rnd.gauss(18 if category == "Grocery" else 9, 4)))
        discount = rnd.choice([0.0, 0.0, 0.05, 0.10, 0.15])

        # Seasonal bump for festive months
        if d.month in (10, 11):
            units = int(units * 1.25) + 1

        # The story: September Electronics slump, mostly South, two products.
        if d.month == 9 and category == "Electronics":
            if region == "South" and product in ("Earbuds X2", "Smartwatch Lite"):
                units = max(1, int(units * 0.25))
                discount = rnd.choice([0.0, 0.0, 0.05])
            elif region == "South":
                units = max(1, int(units * 0.8))
            else:
                units = max(1, int(units * 0.93))

        rows.append([d.isoformat(), region, category, product, units, price, f"{discount:.2f}"])

    rows.sort(key=lambda r: r[0])
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["order_date", "region", "category", "product", "units", "unit_price", "discount"])
        w.writerows(rows)
    print(f"Wrote {len(rows):,} rows -> {OUT}")


if __name__ == "__main__":
    main()
