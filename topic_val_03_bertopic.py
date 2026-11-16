"""
topic_val_03_bertopic.py
BERTopic (embeddings + UMAP + HDBSCAN) on Naver Korean reviews.
Discovers topics inductively without specifying K up front.

Uses multilingual MiniLM for Korean-capable embeddings (small, fast, no HF login).

Outputs (data/analysis/naver/topic_validation/):
  bertopic_topics.csv        topic_id, size, top_words
  bertopic_summary.txt       readable list of all topics
  bertopic_doc_topics.csv    per-review topic assignment (for cross-tabulation later)

Run (base env):  python topic_val_03_bertopic.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os, warnings
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")
from pathlib import Path
import time

import numpy as np
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from kiwipiepy import Kiwi

OUT = Path("data/analysis/naver/topic_validation")
OUT.mkdir(parents=True, exist_ok=True)

EMBED_MODEL = "intfloat/multilingual-e5-base"  # already cached locally, strong multilingual model (Korean inc.)
MIN_TOPIC_SIZE = 50  # a topic must contain at least 50 reviews to count
NR_TOPICS = "auto"   # let HDBSCAN decide; alternative: fix (e.g. 10) to compare to K=10 LDA

KO_STOP = [
    "것", "수", "이", "가", "에", "을", "를", "은", "는",
    "우리", "너무", "정말", "진짜", "매우", "아주", "더", "좀", "잘",
    "서울", "한국", "관광", "여행", "방문", "관람", "입장",
    "곳", "때", "분", "번", "명", "개", "원", "층",
    "사람", "생각", "느낌", "이유", "때문", "그리고", "하지만", "그래서",
]
NOUN_TAGS = {"NNG", "NNP"}
kiwi = Kiwi()

def kiwi_tokenize(text):
    """Korean noun-only tokenizer for the CountVectorizer that drives c-TF-IDF."""
    tokens = kiwi.analyze(str(text))[0][0]
    return [t.form for t in tokens
            if t.tag in NOUN_TAGS and len(t.form) > 1 and t.form not in KO_STOP]

print("Loading dataset...")
df = pd.read_csv("data/analysis/naver/naver_dataset.csv", encoding="utf-8")
docs = df.loc[df["text"].notna() & (df["text"].str.len() > 10), "text"].tolist()
print(f"  {len(docs)} reviews with text.")

print(f"Loading embedding model: {EMBED_MODEL}")
t0 = time.time()
embed_model = SentenceTransformer(EMBED_MODEL)
print(f"  Loaded in {time.time()-t0:.0f}s.")

print("Encoding reviews (this is the slow step)...")
t0 = time.time()
embeddings = embed_model.encode(docs, show_progress_bar=True, batch_size=64)
print(f"  Done in {time.time()-t0:.0f}s. Shape: {embeddings.shape}")

# CountVectorizer with Kiwi tokens so topic words are Korean nouns, not substrings
vectorizer = CountVectorizer(tokenizer=kiwi_tokenize, min_df=5, max_df=0.9)

print("Running BERTopic...")
t0 = time.time()
topic_model = BERTopic(
    embedding_model=embed_model,
    vectorizer_model=vectorizer,
    min_topic_size=MIN_TOPIC_SIZE,
    nr_topics=NR_TOPICS,
    calculate_probabilities=False,
    verbose=True,
)
topics, _ = topic_model.fit_transform(docs, embeddings)
print(f"  Done in {time.time()-t0:.0f}s.")

info = topic_model.get_topic_info()
print(f"\nDiscovered {len(info)-1} topics (excluding noise topic -1).")
print(info[["Topic", "Count"]].head(15).to_string(index=False))

rows = []
for topic_id in sorted(set(topics)):
    if topic_id == -1:  # BERTopic's "unassigned/noise" bucket
        continue
    words = topic_model.get_topic(topic_id)
    top = ", ".join(w for w, _ in words[:12])
    size = int(sum(1 for t in topics if t == topic_id))
    rows.append({"topic_id": topic_id, "size": size, "top_words": top})

out = pd.DataFrame(rows).sort_values("size", ascending=False)
out.to_csv(OUT / "bertopic_topics.csv", index=False, encoding="utf-8-sig")

doc_topic = pd.DataFrame({
    "text": docs,
    "topic_id": topics,
})
doc_topic.to_csv(OUT / "bertopic_doc_topics.csv", index=False, encoding="utf-8-sig")

with open(OUT / "bertopic_summary.txt", "w", encoding="utf-8") as f:
    f.write(f"BERTopic on Naver Korean reviews  (N={len(docs)})\n")
    f.write(f"Embedding model: {EMBED_MODEL}\n")
    f.write(f"min_topic_size={MIN_TOPIC_SIZE}, nr_topics={NR_TOPICS}\n")
    noise = int(sum(1 for t in topics if t == -1))
    f.write(f"Unassigned (noise): {noise} docs ({noise/len(docs):.1%})\n\n")
    f.write(f"Topics found: {len(out)}\n\n")
    for _, r in out.iterrows():
        f.write(f"  Topic {r['topic_id']:>3}  (n={r['size']:>4}):  {r['top_words']}\n")

print(f"\nSaved: {OUT}")
print(f"  bertopic_topics.csv       ({len(out)} topics)")
print(f"  bertopic_doc_topics.csv   (per-document assignment)")
print(f"  bertopic_summary.txt      (readable)")
