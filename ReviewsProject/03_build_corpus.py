"""
03_build_corpus.py
Build a balanced review corpus:
  N places × 2 languages (ko, en) × 30 reviews each

Korean: first 30 Naver reviews with sufficient text (platform order)
English: first 30 GMaps English reviews with sufficient text (platform order)
         Language detected via langdetect (GMaps language field is unreliable)

Output: data/corpus.csv
"""
import json, ast, csv, re
from pathlib import Path
from langdetect import detect, LangDetectException

PLACES = [
    "경복궁", "창덕궁",
    "북촌한옥마을", "인사동길",
    "광장시장",
    "홍대거리",
    "N서울타워", "롯데월드",
    "광안리해수욕장", "해운대해수욕장",
]
N        = 30
MIN_CHARS = 15
OUT      = Path("data/corpus.csv")

# ── helpers ──────────────────────────────────────────────────────────────────

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

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

# ── load data ─────────────────────────────────────────────────────────────────

naver_raw = {
    e["name"]: e["reviews"]
    for e in json.loads(Path("data/naver_reviews_raw.json").read_text(encoding="utf-8"))
}

gmaps_raw = {
    p["name"]: p["reviews"]
    for p in json.loads(Path("data/gmaps_reviews_raw.json").read_text(encoding="utf-8"))
}

# ── build corpus ──────────────────────────────────────────────────────────────

rows = []

for place in PLACES:
    # ── Korean (Naver) ────────────────────────────────────────────────────────
    ko_reviews = naver_raw.get(place, [])
    ko_selected = []
    for r in ko_reviews:
        text = clean_text(r.get("text", ""))
        if len(text) >= MIN_CHARS:
            ko_selected.append({
                "place":       place,
                "source":      "naver",
                "language":    "ko",
                "text":        text,
                "rating":      r.get("rating"),
                "visit_count": r.get("visit_count"),
                "visit_date":  r.get("visit_date", ""),
            })
        if len(ko_selected) == N:
            break

    # ── English (GMaps) ───────────────────────────────────────────────────────
    gm_reviews = gmaps_raw.get(place, [])
    en_selected = []
    for r in gm_reviews:
        rev  = parse_gmaps_review(r)
        text = clean_text(rev.get("text", ""))
        if len(text) < MIN_CHARS:
            continue
        lang = detect_lang(text)
        if lang and lang.startswith("en"):
            pass
        elif (rev.get("language") or "").lower().startswith("en"):
            pass  # trust the field when langdetect fails
        else:
            continue
        if True:
            en_selected.append({
                "place":       place,
                "source":      "gmaps",
                "language":    "en",
                "text":        text,
                "rating":      rev.get("rating"),
                "visit_count": None,
                "visit_date":  r.get("time", ""),
            })
        if len(en_selected) == N:
            break

    rows.extend(ko_selected)
    rows.extend(en_selected)

    print(f"{place}: KO={len(ko_selected)}  EN={len(en_selected)}")

# ── save ──────────────────────────────────────────────────────────────────────

OUT.parent.mkdir(exist_ok=True)
fields = ["place", "source", "language", "text", "rating", "visit_count", "visit_date"]

with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"\nCorpus saved → {OUT}  ({len(rows)} rows)")
