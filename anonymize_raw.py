"""
anonymize_raw.py — strip PII from naver_reviews_raw.json for public distribution.

Removes per-review:
  - nickname     (reviewer display name)
  - profile_url  (unique profile hash)

Keeps everything else (ratings, text, dates, tags, counts, reactions...).
Reviewer lifetime stats (user_reviews, user_photos, user_followers) are kept
as they are aggregates without a direct identifier attached.

Output: data/naver_reviews_raw_anon.json  (safe to commit publicly).
"""

import sys, json
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

ROOT = Path(__file__).parent
SRC  = ROOT / "data" / "naver_reviews_raw.json"
DST  = ROOT / "data" / "naver_reviews_raw_anon.json"

PII_FIELDS = {"nickname", "profile_url"}

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

n_reviews = 0
for place in data:
    for r in place.get("reviews", []):
        for field in PII_FIELDS:
            r.pop(field, None)
        n_reviews += 1

with open(DST, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Anonymized {n_reviews} reviews across {len(data)} places")
print(f"Removed fields: {sorted(PII_FIELDS)}")
print(f"Output: {DST}  ({DST.stat().st_size / 1024 / 1024:.1f} MB)")
