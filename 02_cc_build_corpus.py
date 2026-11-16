"""
02_cc_build_corpus.py
Build the cross-cultural review corpus:
  places × 2 languages (ko, en) × up to N reviews each

Reviews are taken from a common time window for both languages (as in Lee et al. 2026,
who use a fixed 52-week window), so domestic and foreign reviews describe the same period:
  window: the WINDOW_MONTHS months up to WINDOW_END
  Korean:  Naver reviews, dated by the visit date (parsed from the visible label)
  English: Google Maps reviews detected as English (langdetect, seeded; the platform's
           language field is used when detection fails), dated by publication date
For every place and language, usable reviews in the window (>= 15 characters,
duplicates removed by comparing text without spaces and punctuation) are sorted from
newest to oldest and the N most recent are kept. A place enters the corpus only with
>= MIN_PER_LANG reviews in each language inside the window.

Output: data/corpus.csv
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json, ast, csv, re
from datetime import date, datetime, timezone
from pathlib import Path
from langdetect import detect, LangDetectException, DetectorFactory

DetectorFactory.seed = 0   # langdetect is random unless seeded

WINDOW_END = date(2026, 9, 30)    # last full month before the scrapes (Sep 30 - Oct 7, 2026)
WINDOW_MONTHS = 12


def window_start(end, months):
    """First day of the window: 12 months up to 2026-09-30 -> 2025-10-01."""
    index = end.year * 12 + (end.month - 1) - months + 1
    return date(index // 12, index % 12 + 1, 1)


WINDOW_START = window_start(WINDOW_END, WINDOW_MONTHS)   # inclusive
WEEKDAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

# Single source of truth: places.json, filtered to cross_cultural_corpus=true.
from places_data import CROSS_CULTURAL_PLACES as PLACES
N        = 100      # most recent reviews kept per language and place inside the window
MIN_PER_LANG = 20   # a place enters the corpus only with >= 20 reviews in EACH language
MIN_CHARS = 15
OUT      = Path("data/corpus.csv")

# ── helpers ──────────────────────────────────────────────────────────────────

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def clean_naver(text):
    """Strip the '동영상' (video) badge Naver prepends to reviews with media."""
    return re.sub(r"^(동영상\s*)+", "", clean_text(text)).strip()

def dedup_key(text):
    """Same review scraped with and without line breaks/spaces must collapse to one key."""
    return re.sub(r"[\W_]+", "", text).lower()

def is_duplicate(text, seen):
    key = dedup_key(text)
    if key in seen:
        return True
    return len(key) > 30 and any(len(s) > 30 and (key in s or s in key) for s in seen)

def parse_gmaps_review(r):
    rev = r.get("review", {})
    if isinstance(rev, str):
        try:
            rev = ast.literal_eval(rev)
        except Exception:
            rev = {}
    return rev

def detect_lang(text):
    if not text or len(text.strip()) < 8:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None

def naver_visit_date(visible, scraped_at):
    """Visit date from Naver's visible label ("9.24.목", or "25.9.24.수" for earlier
    years); without a year, the year that is not in the future and matches the weekday.
    Same rule as 02_naver_build_dataset.py (Naver's hidden full date is unreliable)."""
    m = re.match(r"^(?:(\d{2})\.)?(\d{1,2})\.(\d{1,2})\.?(\S)?", str(visible or "").strip())
    if not m:
        return None
    yy, month, day, wd = m.groups()
    scraped = datetime.fromisoformat(scraped_at[:10]).date() if scraped_at else date.today()
    for year in ([2000 + int(yy)] if yy else [scraped.year, scraped.year - 1]):
        try:
            d = date(year, int(month), int(day))
        except ValueError:
            continue
        if d <= scraped and (wd not in WEEKDAYS or d.weekday() == WEEKDAYS[wd]):
            return d
    return None

def gmaps_published_date(r):
    published = (r.get("time") or {}).get("published")
    if not published:
        return None
    return datetime.fromtimestamp(int(published) / 1000, tz=timezone.utc).date()

def in_window(d):
    return d is not None and WINDOW_START <= d <= WINDOW_END

def most_recent(pool):
    return sorted(pool, key=lambda r: r["visit_date"], reverse=True)[:N]

# ── load data ─────────────────────────────────────────────────────────────────

naver_by_place = {
    e["name"]: e
    for e in json.loads(Path("data/naver_reviews_raw.json").read_text(encoding="utf-8"))
}

gmaps_raw = {
    p["name"]: p["reviews"]
    for p in json.loads(Path("data/gmaps_reviews_raw.json").read_text(encoding="utf-8"))
}

# ── build corpus ──────────────────────────────────────────────────────────────

rows = []
print(f"Window: {WINDOW_START} to {WINDOW_END} ({WINDOW_MONTHS} months); "
      f"up to {N} most recent reviews per language and place\n")

for place in PLACES:
    naver_entry = naver_by_place.get(place, {})
    scraped_at = naver_entry.get("scraped_at", "")

    # ── Korean (Naver) ────────────────────────────────────────────────────────
    ko_pool, ko_seen = [], set()
    for r in naver_entry.get("reviews", []):
        text = clean_naver(r.get("text", ""))
        visit = naver_visit_date(r.get("visit_date"), scraped_at)
        if len(text) >= MIN_CHARS and in_window(visit) and not is_duplicate(text, ko_seen):
            ko_seen.add(dedup_key(text))
            ko_pool.append({
                "place":       place,
                "source":      "naver",
                "language":    "ko",
                "text":        text,
                "rating":      r.get("rating"),
                "visit_count": r.get("visit_count"),
                "visit_date":  visit.isoformat(),
            })

    # ── English (GMaps) ───────────────────────────────────────────────────────
    en_pool, en_seen = [], set()
    for r in gmaps_raw.get(place, []):
        rev  = parse_gmaps_review(r)
        text = clean_text(rev.get("text", ""))
        published = gmaps_published_date(r)
        if len(text) < MIN_CHARS or not in_window(published) or is_duplicate(text, en_seen):
            continue
        lang = detect_lang(text)
        field = (rev.get("language") or "").lower()
        if not ((lang and lang.startswith("en")) or (lang is None and field.startswith("en"))):
            continue
        en_seen.add(dedup_key(text))
        en_pool.append({
            "place":       place,
            "source":      "gmaps",
            "language":    "en",
            "text":        text,
            "rating":      rev.get("rating"),
            "visit_count": None,
            "visit_date":  published.isoformat(),
        })

    if len(ko_pool) < MIN_PER_LANG or len(en_pool) < MIN_PER_LANG:
        print(f"{place}: in window KO={len(ko_pool)}  EN={len(en_pool)}  -> SKIPPED "
              f"(needs >= {MIN_PER_LANG} per language in the window)")
        continue

    ko_selected, en_selected = most_recent(ko_pool), most_recent(en_pool)
    rows.extend(ko_selected)
    rows.extend(en_selected)

    print(f"{place}: KO={len(ko_selected)} of {len(ko_pool)}  EN={len(en_selected)} of {len(en_pool)}")

# ── save ──────────────────────────────────────────────────────────────────────

OUT.parent.mkdir(exist_ok=True)
fields = ["place", "source", "language", "text", "rating", "visit_count", "visit_date"]

with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"\nCorpus saved → {OUT}  ({len(rows)} rows)")
