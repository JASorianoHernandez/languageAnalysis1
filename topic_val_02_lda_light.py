"""
topic_val_02_lda_light.py
Lightweight LDA: just K=5 (matches our 5 ABSA aspects) and K=10 (sanity check for finer structure).
Fast, no grid search, no multi-seed. ~2-5 minutes.

Outputs (data/analysis/naver/topic_validation/):
  lda_light_topics.csv     topic_id, k, top_words
  lda_light_summary.txt    quick human-readable view

Run (base env):  python topic_val_02_lda_light.py
"""
import sys, os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger("gensim").setLevel(logging.ERROR)
from pathlib import Path
import time

import pandas as pd
from gensim import corpora
from gensim.models import LdaModel, CoherenceModel
from kiwipiepy import Kiwi

OUT = Path("data/analysis/naver/topic_validation")
OUT.mkdir(parents=True, exist_ok=True)

KO_STOP = {
    "것", "수", "이", "가", "에", "을", "를", "은", "는",
    "우리", "너무", "정말", "진짜", "매우", "아주", "더", "좀", "잘",
    "서울", "한국", "관광", "여행", "방문", "관람", "입장",
    "곳", "때", "분", "번", "명", "개", "원", "층",
    "사람", "생각", "느낌", "이유", "때문",
}
NOUN_TAGS = {"NNG", "NNP"}
kiwi = Kiwi()

def tokenize_ko(text):
    tokens = kiwi.analyze(str(text))[0][0]
    return [t.form for t in tokens
            if t.tag in NOUN_TAGS and len(t.form) > 1 and t.form not in KO_STOP]

print("Loading dataset...")
df = pd.read_csv("data/analysis/naver/naver_dataset.csv", encoding="utf-8")
texts = df.loc[df["text"].notna() & (df["text"].str.len() > 10), "text"].tolist()
print(f"  {len(texts)} reviews with text.")

print("Tokenizing...")
t0 = time.time()
tokenized = [tokenize_ko(t) for t in texts]
tokenized = [t for t in tokenized if len(t) >= 3]
print(f"  {len(tokenized)} tokenized docs ({time.time()-t0:.0f}s).")

dictionary = corpora.Dictionary(tokenized)
dictionary.filter_extremes(no_below=5, no_above=0.9)
corpus = [dictionary.doc2bow(t) for t in tokenized]
print(f"  Vocabulary: {len(dictionary)} terms.")

rows = []
for k in (5, 10):
    print(f"\nFitting LDA (K={k})...")
    t0 = time.time()
    model = LdaModel(corpus, num_topics=k, id2word=dictionary,
                     passes=10, random_state=42, alpha="auto")
    coh = CoherenceModel(model=model, texts=tokenized, dictionary=dictionary,
                          coherence="c_v", processes=1).get_coherence()
    print(f"  Done in {time.time()-t0:.0f}s. Coherence c_v = {coh:.3f}")
    for topic_id, topic_tokens in model.show_topics(num_topics=k, num_words=12, formatted=False):
        rows.append({
            "k": k, "topic_id": topic_id, "coherence_cv": round(coh, 3),
            "top_words": ", ".join(w for w, _ in topic_tokens),
        })

out = pd.DataFrame(rows)
out.to_csv(OUT / "lda_light_topics.csv", index=False, encoding="utf-8-sig")

with open(OUT / "lda_light_summary.txt", "w", encoding="utf-8") as f:
    for k in (5, 10):
        sub = out[out["k"] == k]
        f.write(f"=== K = {k}  (coherence c_v = {sub['coherence_cv'].iloc[0]}) ===\n")
        for _, r in sub.iterrows():
            f.write(f"  Topic {r['topic_id']:>2}: {r['top_words']}\n")
        f.write("\n")

print(f"\nSaved: {OUT}")
print(f"  lda_light_topics.csv    ({len(out)} topic rows)")
print(f"  lda_light_summary.txt   (readable)")
