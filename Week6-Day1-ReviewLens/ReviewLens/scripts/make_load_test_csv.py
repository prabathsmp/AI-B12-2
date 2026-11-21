"""Generate a 250-row CSV (by remixing the sample) to verify the 200+ row 'done' criterion.

Usage:  python scripts/make_load_test_csv.py [rows] [out.csv]
"""
import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
rows = int(sys.argv[1]) if len(sys.argv) > 1 else 250
out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "app" / "sample_data" / f"reviews_load_{rows}.csv"

base = pd.read_csv(ROOT / "app" / "sample_data" / "reviews_week40.csv", dtype=str, keep_default_na=False)
base = base[base["review_text"].str.strip() != ""]
random.seed(42)
suffixes = ["", " Please check.", " Very disappointed.", " Thanks!", " Will try again.", " 🙏", " Pathetic.",
            " Overall ok.", " Semma!", " Not happy."]
dates = pd.date_range("2026-09-29", "2026-10-05").strftime("%Y-%m-%d").tolist()

recs = []
for i in range(rows):
    r = base.sample(1, random_state=random.randint(0, 10**6)).iloc[0]
    recs.append({"review_id": f"L-{2000 + i}", "date": random.choice(dates), "platform": r["platform"],
                 "rating": r["rating"], "review_text": r["review_text"] + random.choice(suffixes)})
pd.DataFrame(recs).to_csv(out, index=False, encoding="utf-8")
print(f"wrote {rows} rows -> {out}")
