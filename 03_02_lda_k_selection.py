"""
03_02_lda_k_selection.py
Justify the number of LDA topics (K) with coherence and perplexity,
following Chen et al. (2024, Figs. 2-3).

For K = 2..15 and each language, LDA is fitted with the same tokenization
and settings as 03_01_analyze.py, repeated over several seeds (small corpora make
LDA unstable). Coherence = c_v (higher is better); perplexity = 2^(-bound)
from gensim's per-word likelihood bound (lower is better).

Outputs (data/analysis/):
  lda_k_selection.csv
  figures/14_lda_k_selection.png

Run (base env):  python 03_02_lda_k_selection.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger("gensim").setLevel(logging.ERROR)
from pathlib import Path

import numpy as np
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from gensim import corpora
from gensim.models import LdaModel, CoherenceModel
from kiwipiepy import Kiwi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ANALYSIS = Path("data/analysis")
FIGS = ANALYSIS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

K_RANGE = range(2, 16)
SEEDS = [42, 7, 2026]
PASSES = 20
CHOSEN_K = 5

# ── tokenization: identical to 03_01_analyze.py ─────────────────────────────────
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
KO_STOP = {
    "것", "수", "이", "가", "에", "을", "를", "은", "는",
    "우리", "너무", "정말", "진짜", "매우", "아주", "더", "좀", "잘",
    "서울", "한국", "관광", "여행", "방문", "관람", "입장",
    "곳", "때", "분", "번", "명", "개", "원", "층",
    "사람", "생각", "느낌", "이유", "때문",
}
NOUN_TAGS = {"NNG", "NNP"}
kiwi = Kiwi()


def tokenize_en(text):
    tokens = word_tokenize(str(text).lower())
    return [t for t in tokens if t.isalpha() and len(t) > 2 and t not in EN_STOP]


def tokenize_ko(text):
    tokens = kiwi.analyze(str(text))[0][0]
    return [t.form for t in tokens
            if t.tag in NOUN_TAGS and len(t.form) > 1 and t.form not in KO_STOP]


def prepare(texts, tokenize_fn):
    tokenized = [tokenize_fn(t) for t in texts]
    tokenized = [t for t in tokenized if len(t) >= 3]
    dictionary = corpora.Dictionary(tokenized)
    dictionary.filter_extremes(no_below=2, no_above=0.9)
    corpus = [dictionary.doc2bow(t) for t in tokenized]
    return tokenized, dictionary, corpus


# ── grid ─────────────────────────────────────────────────────────────────────
df = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
rows = []
for lang, fn in [("en", tokenize_en), ("ko", tokenize_ko)]:
    tokenized, dictionary, corpus = prepare(df.loc[df.language == lang, "text"], fn)
    print(f"{lang.upper()}: {len(corpus)} documents, {len(dictionary)} terms")
    for k in K_RANGE:
        for seed in SEEDS:
            model = LdaModel(corpus, num_topics=k, id2word=dictionary,
                             passes=PASSES, random_state=seed, alpha="auto")
            coherence = CoherenceModel(model=model, texts=tokenized, dictionary=dictionary,
                                       coherence="c_v", processes=1).get_coherence()
            perplexity = 2 ** (-model.log_perplexity(corpus))
            rows.append({"language": lang, "k": k, "seed": seed,
                         "coherence_cv": coherence, "perplexity": perplexity})
        last = pd.DataFrame(rows[-len(SEEDS):])
        print(f"  K={k:>2}  c_v={last.coherence_cv.mean():.3f}  "
              f"perplexity={last.perplexity.mean():.1f}")

raw = pd.DataFrame(rows)
summary = raw.groupby(["language", "k"]).agg(
    coherence_mean=("coherence_cv", "mean"), coherence_sd=("coherence_cv", "std"),
    perplexity_mean=("perplexity", "mean"), perplexity_sd=("perplexity", "std"),
).reset_index()
summary.to_csv(ANALYSIS / "lda_k_selection.csv", index=False, encoding="utf-8-sig")

print("\nBest K by mean coherence (c_v):")
for lang in ("en", "ko"):
    sub = summary[summary.language == lang].sort_values("coherence_mean", ascending=False)
    top3 = ", ".join(f"K={int(r.k)} ({r.coherence_mean:.3f})" for _, r in sub.head(3).iterrows())
    chosen = sub[sub.k == CHOSEN_K].iloc[0]
    rank = int((sub.coherence_mean > chosen.coherence_mean).sum()) + 1
    print(f"  {lang.upper()}: top-3 {top3} | K={CHOSEN_K}: {chosen.coherence_mean:.3f} "
          f"(rank {rank} of {len(sub)})")


# ── figure (dual axis, as in Chen et al. 2024) ───────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
titles = {"en": "English-language reviews", "ko": "Korean-language reviews"}
for ax, lang in zip(axes, ("en", "ko")):
    sub = summary[summary.language == lang]
    ax.errorbar(sub.k, sub.coherence_mean, yerr=sub.coherence_sd, color="#111827",
                marker="o", ms=4, capsize=3, lw=1.6, label="Coherence (c_v)")
    ax.set_xlabel("Number of topics (K)")
    ax.set_ylabel("Coherence c_v (higher = better)")
    ax.set_xticks(list(K_RANGE))
    ax.spines[["top"]].set_visible(False)

    ax2 = ax.twinx()
    ax2.plot(sub.k, sub.perplexity_mean, "--", color="#6B7280", lw=1.4, label="Perplexity")
    ax2.set_ylabel("Perplexity (lower = better)", color="#6B7280")
    ax2.tick_params(axis="y", colors="#6B7280")
    ax2.spines[["top"]].set_visible(False)

    ax.axvline(CHOSEN_K, color="#DC2626", lw=1.2, alpha=0.7)
    ax.text(CHOSEN_K + 0.15, ax.get_ylim()[1], f"K = {CHOSEN_K} (used)", color="#DC2626",
            va="top", fontsize=9)
    ax.set_title(titles[lang], fontweight="bold")

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8.5, frameon=False)

fig.suptitle(f"LDA model selection: coherence and perplexity by K "
             f"(mean ± SD over {len(SEEDS)} seeds)", fontweight="bold")
fig.tight_layout()
fig.savefig(FIGS / "14_lda_k_selection.png", dpi=300, bbox_inches="tight")
plt.close()

print(f"\nSaved: {ANALYSIS / 'lda_k_selection.csv'}")
print(f"Saved: {FIGS / '14_lda_k_selection.png'}")
