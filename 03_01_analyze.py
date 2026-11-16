"""
03_01_analyze.py
Analysis pipeline for the Seoul tourist review corpus (238 reviews).

Steps:
  1. Sentiment analysis  — VADER (EN) + KoBERT-based (KO)
  2. LDA topic modeling  — separate models for EN and KO
  3. Summary tables      — sentiment by place × language, top topics

Outputs (all in data/analysis/):
  sentiment_results.csv   — per-review sentiment scores
  lda_en_topics.csv       — top words per EN topic
  lda_ko_topics.csv       — top words per KO topic
  topic_assignments.csv   — topic distribution per review
  summary_sentiment.csv   — mean sentiment by place × language
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os, warnings
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
warnings.filterwarnings("ignore")

import re
import pandas as pd
import numpy as np
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
CORPUS = Path("data/corpus.csv")
OUT    = Path("data/analysis")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CORPUS, encoding="utf-8-sig")
print(f"Corpus loaded: {len(df)} reviews")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. SENTIMENT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Sentiment analysis ──")

# ── English: VADER ────────────────────────────────────────────────────────────
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

vader = SentimentIntensityAnalyzer()

def vader_sentiment(text):
    scores = vader.polarity_scores(str(text))
    return scores["compound"]  # -1 to +1

# ── Korean: multilingual transformer (sentiment) ──────────────────────────────
# Uses snunlp/KR-FinBert-SC or fallback to XLM-RoBERTa-based multilingual model
# We use a lightweight approach: translate polarity via a pre-trained pipeline

from transformers import pipeline

print("  Loading KO sentiment model (hun3359/klue-bert-base-sentiment)...")
ko_pipe = pipeline(
    "text-classification",
    model="hun3359/klue-bert-base-sentiment",
    truncation=True,
    max_length=512,
    device=-1,
    top_k=None,
)
# 60 fine-grained emotion labels → grouped into polarity buckets
KO_POSITIVE = {
    "신이 난", "기쁨", "만족스러운", "흥분", "감사하는",
    "느긋", "편안한", "안도", "신뢰하는", "자신하는",
}
KO_NEGATIVE = {
    "눈물이 나는", "버려진", "짜증내는", "툴툴대는", "억울한",
    "악의적인", "배신당한", "초조한", "우울한", "분노", "성가신",
    "불안", "슬픔", "염세적인", "구역질 나는", "후회되는", "비통한",
    "노여워하는", "낙담한", "걱정스러운", "상처", "실망한",
    "스트레스 받는", "괴로워하는", "좌절한", "환멸을 느끼는",
    "두려운", "외로운", "혐오스러운", "한심한",
}

def ko_sentiment(text):
    try:
        results = ko_pipe(str(text)[:400])[0]  # list of {label, score}
        pos_score = sum(r["score"] for r in results if r["label"] in KO_POSITIVE)
        neg_score = sum(r["score"] for r in results if r["label"] in KO_NEGATIVE)
        return round(pos_score - neg_score, 4)  # -1..+1 range
    except Exception:
        return 0.0

print("  klue-bert-base-sentiment loaded OK")

# ── apply ─────────────────────────────────────────────────────────────────────
en_mask = df["language"] == "en"
ko_mask = df["language"] == "ko"

df["sentiment"] = 0.0

print("  Scoring English reviews (VADER)...")
df.loc[en_mask, "sentiment"] = df.loc[en_mask, "text"].apply(vader_sentiment)

print("  Scoring Korean reviews (transformer)...")
ko_texts = df.loc[ko_mask, "text"].tolist()
ko_scores = []
for i, t in enumerate(ko_texts):
    ko_scores.append(ko_sentiment(t))
    if (i + 1) % 20 == 0:
        print(f"    {i+1}/{len(ko_texts)}")
df.loc[ko_mask, "sentiment"] = ko_scores

# label
def label(s):
    if s > 0.05:  return "positive"
    if s < -0.05: return "negative"
    return "neutral"

df["sentiment_label"] = df["sentiment"].apply(label)

sent_out = df[["place","source","language","sentiment","sentiment_label","text"]].copy()
sent_out.to_csv(OUT / "sentiment_results.csv", index=False, encoding="utf-8-sig")
print("  Saved: sentiment_results.csv")

# quick summary
summary = df.groupby(["place","language"])["sentiment"].agg(
    mean="mean", std="std", count="count"
).round(4)
summary.to_csv(OUT / "summary_sentiment.csv", encoding="utf-8-sig")
print("  Saved: summary_sentiment.csv")
print(summary.to_string())

# ═══════════════════════════════════════════════════════════════════════════════
# 2. TOPIC MODELING (LDA)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Topic modeling (LDA) ──")

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from gensim import corpora
from gensim.models import LdaModel

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

EN_STOP = set(stopwords.words("english")) | {
    "place", "visit", "visited", "really", "also", "one", "go", "get",
    "got", "would", "could", "like", "even", "around", "much", "lot",
    "great", "good", "beautiful", "nice", "amazing", "wonderful", "love",
    "loved", "highly", "recommend", "definitely", "must", "see",
    "time", "day", "tour", "tourist", "korea", "korean", "seoul",
    "everything", "something", "nothing", "thing", "things",
}

def tokenize_en(text):
    tokens = word_tokenize(str(text).lower())
    return [t for t in tokens if t.isalpha() and len(t) > 2 and t not in EN_STOP]

# Korean tokenization via KoNLPy Okt (nouns only)
from kiwipiepy import Kiwi
kiwi = Kiwi()

KO_STOP = {
    "것", "수", "이", "가", "에", "을", "를", "은", "는",
    "우리", "너무", "정말", "진짜", "매우", "아주", "더", "좀", "잘",
    "서울", "한국", "관광", "여행", "방문", "관람", "입장",
    "곳", "때", "분", "번", "명", "개", "원", "층",
    "사람", "생각", "느낌", "이유", "때문",
}
# Kiwi POS tags for nouns: NNG (general noun), NNP (proper noun), NNB (bound noun)
NOUN_TAGS = {"NNG", "NNP"}

def tokenize_ko(text):
    tokens = kiwi.analyze(str(text))[0][0]
    nouns = [t.form for t in tokens if t.tag in NOUN_TAGS and len(t.form) > 1 and t.form not in KO_STOP]
    return nouns

N_TOPICS = 5
N_WORDS  = 10
PASSES   = 20
SEED     = 42

def run_lda(texts, tokenize_fn, label, n_topics=N_TOPICS):
    tokenized = [tokenize_fn(t) for t in texts]
    tokenized = [t for t in tokenized if len(t) >= 3]
    dictionary = corpora.Dictionary(tokenized)
    dictionary.filter_extremes(no_below=2, no_above=0.9)
    corpus = [dictionary.doc2bow(t) for t in tokenized]
    model  = LdaModel(
        corpus, num_topics=n_topics, id2word=dictionary,
        passes=PASSES, random_state=SEED, alpha="auto",
    )
    # top words per topic
    rows = []
    for i in range(n_topics):
        words = model.show_topic(i, topn=N_WORDS)
        rows.append({
            "topic": i + 1,
            "top_words": ", ".join(w for w, _ in words),
            "weights":   ", ".join(f"{p:.3f}" for _, p in words),
        })
    topics_df = pd.DataFrame(rows)
    topics_df.to_csv(OUT / f"lda_{label}_topics.csv", index=False, encoding="utf-8-sig")
    print(f"  Saved: lda_{label}_topics.csv")
    for _, r in topics_df.iterrows():
        print(f"    Topic {r['topic']}: {r['top_words']}")
    return model, dictionary, tokenized

print("  English LDA...")
en_texts = df.loc[en_mask, "text"].tolist()
en_model, en_dict, en_tok = run_lda(en_texts, tokenize_en, "en")

print("  Korean LDA...")
ko_texts_lda = df.loc[ko_mask, "text"].tolist()
ko_model, ko_dict, ko_tok = run_lda(ko_texts_lda, tokenize_ko, "ko")

# ── topic assignments per review ──────────────────────────────────────────────
def get_dominant_topic(model, dictionary, text, tokenize_fn):
    tokens = tokenize_fn(str(text))
    bow    = dictionary.doc2bow(tokens)
    if not bow:
        return -1, 0.0
    topics = model.get_document_topics(bow)
    if not topics:
        return -1, 0.0
    dominant = max(topics, key=lambda x: x[1])
    return dominant[0] + 1, round(dominant[1], 4)

assign_rows = []
for _, row in df.iterrows():
    if row["language"] == "en":
        topic, prob = get_dominant_topic(en_model, en_dict, row["text"], tokenize_en)
    else:
        topic, prob = get_dominant_topic(ko_model, ko_dict, row["text"], tokenize_ko)
    assign_rows.append({
        "place":          row["place"],
        "language":       row["language"],
        "dominant_topic": topic,
        "topic_prob":     prob,
        "sentiment":      row["sentiment"],
        "sentiment_label":row["sentiment_label"],
        "text":           row["text"][:120],
    })

assign_df = pd.DataFrame(assign_rows)
assign_df.to_csv(OUT / "topic_assignments.csv", index=False, encoding="utf-8-sig")
print("  Saved: topic_assignments.csv")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. DONE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Complete ──")
print(f"Output files in {OUT}/")
for f in sorted(OUT.iterdir()):
    print(f"  {f.name}")
