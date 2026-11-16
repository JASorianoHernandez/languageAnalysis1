"""
topic_val_01_lda_full.py
Full LDA grid (K=2..15, 3 seeds) on Naver Korean reviews with text.
Validates whether our 5 hand-picked ABSA aspects correspond to data-driven topics.

Outputs (data/analysis/naver/topic_validation/):
  lda_full_grid.csv        coherence + perplexity per (K, seed)
  lda_full_topwords.csv    top-10 words for best-K topics
  lda_full_bestk.txt       summary of best K and top words
  figures/lda_full_curve.png

Run (base env):  python topic_val_01_lda_full.py
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

import numpy as np
import pandas as pd
from gensim import corpora
from gensim.models import LdaModel, CoherenceModel
from kiwipiepy import Kiwi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("data/analysis/naver/topic_validation")
OUT.mkdir(parents=True, exist_ok=True)
FIGS = OUT / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

K_RANGE = range(2, 16)
SEEDS = [42, 7, 2026]
PASSES = 10  # fewer passes than 03_02 since the Naver corpus is larger

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
print(f"  {len(texts)} reviews with text (10+ chars).")

print("Tokenizing with Kiwi...")
t0 = time.time()
tokenized = [tokenize_ko(t) for t in texts]
tokenized = [t for t in tokenized if len(t) >= 3]
print(f"  {len(tokenized)} docs after min-3-noun filter ({time.time()-t0:.0f}s).")

dictionary = corpora.Dictionary(tokenized)
dictionary.filter_extremes(no_below=5, no_above=0.9)
corpus = [dictionary.doc2bow(t) for t in tokenized]
print(f"  Vocabulary: {len(dictionary)} terms.")

print(f"\nFitting LDA across K={list(K_RANGE)} with {len(SEEDS)} seeds...")
rows = []
best_models = {}  # keep one model per K for top-words extraction
for k in K_RANGE:
    for seed in SEEDS:
        model = LdaModel(corpus, num_topics=k, id2word=dictionary,
                         passes=PASSES, random_state=seed, alpha="auto")
        coh = CoherenceModel(model=model, texts=tokenized, dictionary=dictionary,
                              coherence="c_v", processes=1).get_coherence()
        perp = 2 ** (-model.log_perplexity(corpus))
        rows.append({"k": k, "seed": seed, "coherence_cv": coh, "perplexity": perp})
        if seed == SEEDS[0]:
            best_models[k] = model
    recent = [r for r in rows if r["k"] == k]
    coh_mean = np.mean([r["coherence_cv"] for r in recent])
    print(f"  K={k:>2}: c_v={coh_mean:.3f}")

grid = pd.DataFrame(rows)
grid.to_csv(OUT / "lda_full_grid.csv", index=False, encoding="utf-8-sig")

summary = grid.groupby("k").agg(
    coherence_mean=("coherence_cv", "mean"),
    coherence_sd=("coherence_cv", "std"),
    perplexity_mean=("perplexity", "mean"),
).reset_index()

best_k = int(summary.loc[summary["coherence_mean"].idxmax(), "k"])
print(f"\nBest K by coherence: {best_k}")

best_model = best_models[best_k]
tw_rows = []
for topic_id, topic_tokens in best_model.show_topics(num_topics=best_k, num_words=10, formatted=False):
    tw_rows.append({
        "k": best_k, "topic_id": topic_id,
        "top_words": ", ".join(w for w, _ in topic_tokens),
    })
tw = pd.DataFrame(tw_rows)
tw.to_csv(OUT / "lda_full_topwords.csv", index=False, encoding="utf-8-sig")

with open(OUT / "lda_full_bestk.txt", "w", encoding="utf-8") as f:
    f.write(f"Best K by mean coherence (c_v): {best_k}\n")
    f.write(f"Coherence={summary.loc[summary['k']==best_k, 'coherence_mean'].iloc[0]:.3f}\n\n")
    f.write("Top-3 K values by coherence:\n")
    for _, r in summary.sort_values("coherence_mean", ascending=False).head(3).iterrows():
        f.write(f"  K={int(r['k'])}: c_v={r['coherence_mean']:.3f}\n")
    f.write(f"\nTopics for K={best_k}:\n")
    for _, r in tw.iterrows():
        f.write(f"  Topic {r['topic_id']}: {r['top_words']}\n")

# figure
fig, ax = plt.subplots(figsize=(9, 4))
ax.errorbar(summary.k, summary.coherence_mean, yerr=summary.coherence_sd,
            marker="o", capsize=3, color="#111827")
ax.set_xlabel("Number of topics K")
ax.set_ylabel("Coherence c_v (higher = better)")
ax.axvline(best_k, color="#DC2626", lw=1.2, alpha=0.7)
ax.text(best_k + 0.15, ax.get_ylim()[1], f"K* = {best_k}", color="#DC2626", va="top", fontsize=9)
ax.set_xticks(list(K_RANGE))
ax.set_title(f"LDA on Naver Korean reviews (N={len(tokenized)} docs)")
fig.tight_layout()
fig.savefig(FIGS / "lda_full_curve.png", dpi=200, bbox_inches="tight")

print(f"\nSaved: {OUT}")
print(f"  lda_full_grid.csv       ({len(grid)} rows)")
print(f"  lda_full_topwords.csv   ({len(tw)} topics)")
print(f"  lda_full_bestk.txt      (best K + top words)")
print(f"  figures/lda_full_curve.png")
