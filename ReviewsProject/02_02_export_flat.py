"""
export_flat.py
Flatten the raw review JSONs into CSVs for manual inspection in Excel.

Writes data/flat_naver.csv and data/flat_gmaps.csv — one row per review, all
fields as columns. Handles both the old and new record shapes so the files
stay readable while the re-scrape is only partly done.

Run: python export_flat.py
"""
import ast
import csv
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"

NAVER_COLS = [
    "place", "rating", "visit_date", "visit_date_full", "visit_count",
    "nickname", "user_reviews", "user_photos", "user_followers",
    "reactions", "n_photos", "tags", "visit_keywords", "text_len", "text",
    "profile_url",
]

GMAPS_COLS = [
    "place", "rating", "language", "language_source", "published", "published_relative",
    "author_name", "author_id", "author_review_count", "author_photo_count",
    "n_photos", "text_len", "text", "text_translated", "review_id", "permalink",
]


def collapse(value):
    return re.sub(r"\s+", " ", str(value)).strip() if value else ""


def export_naver():
    src = DATA / "naver_reviews_raw.json"
    if not src.exists():
        print(f"  {src.name} not found — skipping")
        return
    places = json.loads(src.read_text(encoding="utf-8"))
    rows = []
    for place in places:
        for r in place["reviews"]:
            text = collapse(r.get("text"))
            rows.append({
                "place":           place["name"],
                "rating":          r.get("rating"),
                "visit_date":      r.get("visit_date", ""),
                "visit_date_full": r.get("visit_date_full", ""),
                "visit_count":     r.get("visit_count"),
                "nickname":        r.get("nickname", ""),
                "user_reviews":    r.get("user_reviews"),
                "user_photos":     r.get("user_photos"),
                "user_followers":  r.get("user_followers"),
                "reactions":       r.get("reactions"),
                "n_photos":        r.get("n_photos"),
                "tags":            " | ".join(r.get("tags") or []),
                "visit_keywords":  " | ".join(r.get("visit_keywords") or []),
                "text_len":        len(text),
                "text":            text,
                "profile_url":     r.get("profile_url", ""),
            })
    out = DATA / "flat_naver.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=NAVER_COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"  {out.name}: {len(rows)} rows")


def export_gmaps():
    src = DATA / "gmaps_reviews_raw.json"
    if not src.exists():
        print(f"  {src.name} not found — skipping")
        return
    places = json.loads(src.read_text(encoding="utf-8"))
    rows = []
    for place in places:
        for r in place["reviews"]:
            review = r.get("review", {})
            if isinstance(review, str):          # old package shape
                try:
                    review = ast.literal_eval(review)
                except Exception:
                    review = {}
            author = r.get("author") or {}
            time = r.get("time") or {}
            text = collapse(review.get("text"))
            images = r.get("images") or []
            rows.append({
                "place":               place["name"],
                "rating":              review.get("rating"),
                "language":            review.get("language"),
                "language_source":     review.get("language_source", ""),
                "published":           time.get("published", ""),
                "published_relative":  time.get("published_relative", ""),
                "author_name":         author.get("name", ""),
                "author_id":           author.get("id", ""),
                "author_review_count": author.get("review_count"),
                "author_photo_count":  author.get("photo_count"),
                "n_photos":            r.get("n_photos", len(images)),
                "text_len":            len(text),
                "text":                text,
                "text_translated":     collapse(review.get("text_translated")),
                "review_id":           r.get("review_id", ""),
                "permalink":           r.get("permalink", ""),
            })
    out = DATA / "flat_gmaps.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=GMAPS_COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"  {out.name}: {len(rows)} rows")


print("Exporting flat CSVs...")
export_naver()
export_gmaps()
print(f"\nSaved in {DATA}")
