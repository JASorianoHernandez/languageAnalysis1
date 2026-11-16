"""
hypothesis_dictionaries.py
Shared dictionaries, tokenizers and corpus loading for
08_01_hypothesis_tests.py and 07_02_dictionary_check.py.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from kiwipiepy import Kiwi

ANALYSIS = Path("data/analysis")
CHECK_FILE = ANALYSIS / "dictionary_check.csv"
PRECISION_FILE = ANALYSIS / "dictionary_precision.csv"
PRECISION_THRESHOLD = 0.70
MIN_REVIEWED = 5

# Single source of truth: places.json (see places_data.py's docstring).
from places_data import PLACE_EN

# Terms ending in "*" match as prefixes; English plurals in -s/-es match automatically.
HYPOTHESES = [
    {
        "id": "H1", "dimension": "Uncertainty avoidance",
        "label": "Planning & logistics", "direction": "ko>en",
        "statement": "Domestic reviewers mention planning and logistics more than foreign reviewers.",
        "ko": ["시간", "예약", "주차", "주차장", "대기", "기다리", "웨이팅", "줄", "입장",
               "입장료", "매표소", "운영", "휴무", "평일", "주말", "오픈", "마감", "미리",
               "일찍", "계획", "코스", "동선", "교통", "지하철", "버스", "셔틀", "이동", "소요"],
        "en": ["time", "reserv*", "book*", "parking", "wait*", "queue*", "line", "entrance",
               "entry", "admission", "hour", "weekday", "weekend", "opening", "closed",
               "early", "advance", "plan*", "schedul*", "itinerary", "route", "transport*",
               "subway", "metro", "bus", "shuttle"],
    },
    {
        "id": "H2", "dimension": "Collectivism",
        "label": "Family & companions", "direction": "ko>en",
        "statement": "Domestic reviewers mention family and companions more than foreign reviewers.",
        "ko": ["가족", "아이", "애들", "아기", "부모", "부모님", "엄마", "아빠", "어머니",
               "아버지", "친구", "동료", "단체", "일행", "연인", "남편", "아내", "와이프",
               "남친", "여친", "남자친구", "여자친구", "데이트", "조카", "할머니", "할아버지"],
        "en": ["family", "families", "kid*", "child", "children", "baby", "babies", "parent*",
               "mom", "mum", "dad", "mother", "father", "friend", "group*", "partner",
               "husband", "wife", "boyfriend", "girlfriend", "couple*", "toddler*", "son",
               "daughter"],
    },
    {
        "id": "H3", "dimension": "Power distance",
        "label": "Service & staff", "direction": "ko>en",
        "statement": "Domestic reviewers mention service and staff more than foreign reviewers.",
        "ko": ["직원", "서비스", "친절", "불친절", "안내", "응대", "해설", "해설사", "가이드",
               "사장", "사장님", "상인", "매너", "태도", "알바"],
        "en": ["staff", "service*", "employee*", "friendly", "unfriendly", "rude", "rudely",
               "helpful", "unhelpful", "guide*", "vendor*", "seller*", "owner*", "attitude",
               "polite", "worker*", "attendant*"],
    },
    {
        "id": "H4", "dimension": "Indulgence",
        "label": "Hedonic enjoyment", "direction": "en>ko",
        "statement": "Foreign reviewers express hedonic enjoyment more than domestic reviewers.",
        "ko": ["재미", "재밌", "즐겁", "즐기", "즐거움", "신나", "흥미", "행복", "놀", "설레",
               "짜릿", "스릴"],
        "en": ["fun", "enjoy*", "exciting", "excited", "excitement", "thrill*", "blast",
               "happy", "happiness", "play", "playing", "played", "entertain*", "joy*",
               "delight*"],
    },
    {
        "id": "H5", "dimension": "Collectivism",
        "label": "Favourable evaluation", "direction": "ko>en",
        "statement": "Domestic reviewers give more favourable overall evaluations than foreign reviewers.",
        "metric": "sentiment",
    },
]

# Sensitivity run falls back to this list until dictionary_precision.csv exists.
DEFAULT_AMBIGUOUS = {
    "H1": {"ko": ["시간"], "en": ["time", "times"]},
    "H3": {"ko": ["안내"], "en": ["friendly"]},
}


def build_matcher(terms, exclude=()):
    exact = {t for t in terms if not t.endswith("*")}
    prefixes = tuple(t[:-1] for t in terms if t.endswith("*"))
    exclude = set(exclude)

    def match(tok):
        if tok in exclude:
            return False
        if tok in exact:
            return True
        if tok.endswith("es") and tok[:-2] in exact:
            return True
        if tok.endswith("s") and tok[:-1] in exact:
            return True
        return bool(prefixes) and tok.startswith(prefixes)
    return match


kiwi = Kiwi()
KO_TAGS = {"NNG", "NNP", "VV", "VA", "XR", "MAG"}
ALL_EN_TARGETS = {t.rstrip("*") for h in HYPOTHESES for t in h.get("en", [])}


def tokenize_spans(text, lang):
    """Content tokens as (form, start, end) character spans in the original text."""
    text = str(text)
    if lang == "ko":
        return [(t.form, t.start, t.start + t.len) for t in kiwi.tokenize(text)
                if t.tag.split("-")[0] in KO_TAGS]
    spans = []
    for m in re.finditer(r"[a-z]+", text.lower()):
        w = m.group()
        if len(w) > 1 and (w not in ENGLISH_STOP_WORDS or w in ALL_EN_TARGETS):
            spans.append((w, m.start(), m.end()))
    return spans


def load_corpus():
    df = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
    df = df[df["language"].isin(["ko", "en"])].copy()
    sent_df = pd.read_csv(ANALYSIS / "sentiment_results.csv")
    sent_df = sent_df.drop_duplicates(subset=["place", "language", "text"])
    df = df.merge(sent_df[["place", "language", "text", "sentiment"]],
                  on=["place", "language", "text"], how="left")
    df["spans"] = [tokenize_spans(t, lang) for t, lang in zip(df["text"], df["language"])]
    df["tokens"] = [[s[0] for s in spans] for spans in df["spans"]]
    df["n_tokens"] = df["tokens"].str.len()
    return df[df["n_tokens"] > 0].reset_index(drop=True)


def read_csv_any(path):
    """Excel on Korean Windows may save CSV as cp949 instead of UTF-8."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Could not decode {path}")


def load_exclusions():
    """Terms to drop in the sensitivity run, plus a description of their source."""
    if not PRECISION_FILE.exists():
        return DEFAULT_AMBIGUOUS, "default ambiguous list (no manual coding yet)"
    prec = read_csv_any(PRECISION_FILE)
    low = prec[(prec["n_reviewed"] >= MIN_REVIEWED) & (prec["precision"] < PRECISION_THRESHOLD)]
    exclusions = {}
    for _, r in low.iterrows():
        exclusions.setdefault(r["hypothesis"], {}).setdefault(r["language"], []).append(r["term"])
    source = (f"manual coding: precision < {PRECISION_THRESHOLD:.0%} "
              f"with >= {MIN_REVIEWED} reviewed examples")
    return exclusions, source


def describe_exclusions(exclusions):
    parts = []
    for hid in sorted(exclusions):
        for lang in ("ko", "en"):
            terms = exclusions[hid].get(lang, [])
            if terms:
                parts.append(f"{hid} {lang.upper()}: {', '.join(terms)}")
    return "; ".join(parts) if parts else "(none)"
