"""
02_naver_build_dataset.py
Build a review-level dataset from ALL scraped Korean reviews (not only the 30 per
place used in the cross-cultural corpus), with the extra fields the platform exposes.

Steps
  1. Clean and deduplicate (texts: same rule as 02_cc_build_corpus.py; keyword-only reviews
     without text are kept with has_text = 0 and matched on their metadata)
     Reviewers get a pseudonymous ID (user_id = u0001, ...); nicknames and profile URLs
     are not written to the output.
  2. Parse visit keywords into reservation / waiting / purpose / companion dummies
  3. Count selected keyword tags (information diversity, as in Lee et al. 2026) and
     group the 46 tag phrases into themes (tag_visual, tag_crowded, ...)
     Visit season and weekend, verification method, reviewer followers/photos,
     review age, place type and city are added for the extended models.
  4. Score sentiment with the same Korean classifier as 03_01_analyze.py (-1 to +1)

Output: data/analysis/naver/naver_dataset.csv
Run (base env):  python 02_naver_build_dataset.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import json
import re
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path("data/analysis/naver")
OUT_DIR.mkdir(parents=True, exist_ok=True)
MIN_CHARS = 15

COMPANIONS = {
    "comp_alone": {"혼자"},
    "comp_partner": {"연인・배우자"},
    "comp_friend": {"친구"},
    "comp_child": {"아이"},
    "comp_family": {"부모님", "친척・형제자매", "가족모임"},
    "comp_colleague": {"지인・동료"},
}
PURPOSES = {
    "purp_travel": {"여행"},
    "purp_outing": {"나들이"},
    "purp_daily": {"일상"},
    "purp_date": {"데이트", "기념일"},
    "purp_social": {"친목", "회식"},
}
WAITED = {"10분 이내", "30분 이내", "30분 이상", "1시간 이상"}
RESERVED = {"예약 후 이용"}

# Naver's 46 keyword tags (all phrased as praise) grouped into themes
TAG_THEMES = {
    "tag_visual": {"사진이 잘 나와요", "뷰가 좋아요", "경관이 독특해요", "야경이 멋져요",
                   "자연 경관이 좋아요", "컨셉이 독특해요", "인테리어가 멋져요", "트렌디해요"},
    "tag_content": {"볼거리가 많아요", "유익해요", "설명이 잘 되어있어요", "전시 구성이 알차요",
                    "전시 테마가 재밌어요", "체험 프로그램이 다양해요"},
    "tag_crowded": {"방문객이 많아요"},
    "tag_quiet": {"붐비지 않아요", "조용히 쉬기 좋아요"},
    "tag_facilities": {"관리가 잘 되어있어요", "화장실이 깨끗해요", "편의시설이 잘 되어있어요",
                       "시설이 깔끔해요", "샤워실이 잘 되어있어요", "대여장비 상태가 좋아요",
                       "공간이 넓어요", "규모가 커요", "산책로가 잘 되어있어요", "친절해요"},
    "tag_access": {"대중교통이 편해요", "주차하기 편해요", "근처에 갈 곳이 많아요"},
    "tag_family": {"아이와 가기 좋아요", "반려동물과 가기 좋아요", "피크닉하기 좋아요"},
    "tag_value": {"가격이 합리적이에요", "가성비가 좋아요", "비싼 만큼 가치있어요", "품질이 좋아요"},
    "tag_food": {"먹거리가 풍부해요", "야시장이 잘 되어있어요"},
    "tag_water": {"물놀이하기 좋아요", "모래가 고와요", "서핑하기 좋아요", "수상레저 즐기기 좋아요",
                  "물이 맑아요"},
}
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
# Single source of truth: places.json (see places_data.py's docstring).
# This used to be a local 13-place dict that silently fell behind as places
# were added to the scraper -- 10 of 23 places were landing in place_type =
# "other" with no warning. The loader now warns at import time instead.
from places_data import PLACE_TYPE, CITY


def clean_text(text):
    text = re.sub(r"<br\s*/?>", " ", str(text or ""))
    text = re.sub(r"^(동영상\s*)+", "", re.sub(r"\s+", " ", text).strip())
    return text.strip()


def dedup_key(text):
    return re.sub(r"[\W_]+", "", text).lower()


WEEKDAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}


def parse_visit_date(visible, scraped_at):
    """Visit date from the visible label ("9.24.목", or "25.9.24.수" for earlier years).

    The hidden full date Naver provides is one month ahead in ~40% of reviews, so it
    is not used. Without a year, the year is the one (scrape year or the one before)
    that is not in the future and matches the weekday.
    """
    m = re.match(r"^(?:(\d{2})\.)?(\d{1,2})\.(\d{1,2})\.?(\S)?", str(visible or "").strip())
    if not m:
        return None
    yy, month, day, wd = m.groups()
    scraped = pd.Timestamp(scraped_at[:10]) if scraped_at else pd.Timestamp.today()
    years = [2000 + int(yy)] if yy else [scraped.year, scraped.year - 1]
    for year in years:
        try:
            date = pd.Timestamp(year=year, month=int(month), day=int(day))
        except ValueError:
            continue
        if date <= scraped and (wd not in WEEKDAYS or date.weekday() == WEEKDAYS[wd]):
            return date
    return None


raw = json.loads(Path("data/naver_reviews_raw.json").read_text(encoding="utf-8"))
rows, seen, user_ids = [], set(), {}
for entry in raw:
    place = entry["name"]
    for r in entry["reviews"]:
        text = clean_text(r.get("text"))
        has_text = len(text) >= MIN_CHARS
        user = r.get("profile_url") or r.get("nickname") or ""
        # keyword-only reviews have no text to compare, so they are matched on their metadata
        key = (place, dedup_key(text)) if has_text else \
              (place, user, r.get("visit_date_full"), tuple(r.get("tags") or []), r.get("visit_count"))
        if key in seen:
            continue
        seen.add(key)
        # pseudonymous sequential ID: no nickname or profile URL leaves this script
        uid = user_ids.setdefault(user, f"u{len(user_ids) + 1:04d}")

        visit_items = {t.strip() for k in (r.get("visit_keywords") or []) for t in k.split(",")}
        visit_dt = parse_visit_date(r.get("visit_date"), entry.get("scraped_at", ""))
        row = {
            "place": place,
            "user_id": uid,
            "scraped_at": (entry.get("scraped_at") or "")[:10],
            "visit_date": visit_dt.date().isoformat() if visit_dt is not None else None,
            "visit_month": visit_dt.month if visit_dt is not None else np.nan,
            "visit_weekend": int(visit_dt.weekday() >= 5) if visit_dt is not None else np.nan,
            "reactions": int(r.get("reactions") or 0),
            "verification": r.get("verification") or "",
            "user_photos": int(r.get("user_photos") or 0),
            "user_followers": int(r.get("user_followers") or 0),
            "has_text": int(has_text),
            "text": text if has_text else "",
            "visit_count": int(r.get("visit_count") or 1),
            "rating": r.get("rating"),
            "n_tags": len(r.get("tags") or []),
            "tags": " | ".join(r.get("tags") or []),
            # The scraper counted every <img> in the review, including the reaction icons
            # (one per reaction type shown); real review photos are not <img> tags there.
            "n_photos": max(0, int(r.get("n_photos") or 0) - len(r.get("reaction_types") or [])),
            "user_reviews": int(r.get("user_reviews") or 0),
            "has_visit_info": int(bool(visit_items)),
            "waited": int(bool(visit_items & WAITED)),
            "reserved": int(bool(visit_items & RESERVED)),
        }
        for col, words in {**COMPANIONS, **PURPOSES}.items():
            row[col] = int(bool(visit_items & words))
        tags = set(r.get("tags") or [])
        for col, words in TAG_THEMES.items():
            row[col] = int(bool(tags & words))
        rows.append(row)

df = pd.DataFrame(rows)
df["revisit"] = (df["visit_count"] >= 2).astype(int)
df["ln_length"] = np.where(df["has_text"] == 1, np.log(df["text"].str.len().clip(lower=1)), np.nan)
df["ln_photos"] = np.log1p(df["n_photos"])
df["ln_user_reviews"] = np.log1p(df["user_reviews"])
df["ln_user_followers"] = np.log1p(df["user_followers"])
df["ln_user_photos"] = np.log1p(df["user_photos"])
df["place_type"] = df["place"].map(PLACE_TYPE).fillna("other")
df["city"] = df["place"].map(CITY).fillna("Seoul")
_unknown_type = sorted(set(df.loc[df["place_type"] == "other", "place"]))
if _unknown_type:
    print(f"WARNING: {_unknown_type} not in places.json's place_type -- "
          f"add them there, not here.", file=sys.stderr)

season = df["visit_month"].map(SEASONS)
for s in ("summer", "autumn", "winter"):          # reference: spring
    df[f"season_{s}"] = (season == s).astype(int)

# 영수증 (receipt) and 결제내역 (payment record) both verify a purchase; reference: none
df["verif_reservation"] = (df["verification"] == "예약").astype(int)
df["verif_receipt"] = df["verification"].isin(["영수증", "결제내역"]).astype(int)

# Days between the visit and the scrape: older reviews had more time to collect reactions
age = (pd.to_datetime(df["scraped_at"], errors="coerce") - pd.to_datetime(df["visit_date"])).dt.days
df["ln_review_age"] = np.log1p(age.clip(lower=0))
print(f"Visit dates parsed: {df.visit_date.notna().mean():.1%}  "
      f"(range {df.visit_date.min()} to {df.visit_date.max()})  |  "
      f"reviews with reactions: {(df.reactions > 0).mean():.1%}")
print(f"Unique Korean reviews: {len(df)}  (with text: {df.has_text.sum()}, keyword-only: "
      f"{(df.has_text == 0).sum()})  |  users: {df.user_id.nunique()}")
print(df.groupby(["place", "has_text"]).size().unstack(fill_value=0).to_string())

# ── sentiment: same model and polarity mapping as 03_01_analyze.py ──────────────
from transformers import pipeline

print("\nScoring sentiment (hun3359/klue-bert-base-sentiment, CPU)...")
ko_pipe = pipeline("text-classification", model="hun3359/klue-bert-base-sentiment",
                   truncation=True, max_length=512, device=-1, top_k=None)
KO_POSITIVE = {"신이 난", "기쁨", "만족스러운", "흥분", "감사하는",
               "느긋", "편안한", "안도", "신뢰하는", "자신하는"}
KO_NEGATIVE = {"눈물이 나는", "버려진", "짜증내는", "툴툴대는", "억울한", "악의적인", "배신당한",
               "초조한", "우울한", "분노", "성가신", "불안", "슬픔", "염세적인", "구역질 나는",
               "후회되는", "비통한", "노여워하는", "낙담한", "걱정스러운", "상처", "실망한",
               "스트레스 받는", "괴로워하는", "좌절한", "환멸을 느끼는", "두려운", "외로운",
               "혐오스러운", "한심한"}

texts = df.loc[df.has_text == 1, "text"]
scores = []
for i, text in enumerate(texts, start=1):
    res = ko_pipe(text[:400])[0]
    pos = sum(r["score"] for r in res if r["label"] in KO_POSITIVE)
    neg = sum(r["score"] for r in res if r["label"] in KO_NEGATIVE)
    scores.append(round(pos - neg, 4))
    if i % 200 == 0 or i == len(texts):
        print(f"  {i}/{len(texts)}")
df["sentiment"] = np.nan
df.loc[texts.index, "sentiment"] = scores

out = OUT_DIR / "naver_dataset.csv"
df.to_csv(out, index=False, encoding="utf-8-sig")

print(f"\nSaved: {out}")
print(f"Revisit rate: {df['revisit'].mean():.1%}  |  "
      f"with visit info: {df['has_visit_info'].mean():.1%}")
print("Keyword tags per review:", df["n_tags"].value_counts().sort_index().to_dict())
