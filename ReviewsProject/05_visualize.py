"""
05_visualize.py
Visualization + statistical analysis for the Seoul tourist review corpus.

Analyses:
  1. Sentiment bar chart        — mean ± std by place × language
  2. Sentiment heatmap          — place × language grid
  3. Word clouds                — KO and EN top nouns
  4. Topic distribution heatmap — dominant topic per place × language
  5. TTR (Type-Token Ratio)     — lexical diversity KO vs EN
  6. TF-IDF keyword contrast    — most distinctive words per group
  7. Mann-Whitney U test        — statistical significance of KO > EN sentiment

Output: data/analysis/figures/  (PNG files, 300 dpi)
        data/analysis/stats_mannwhitney.csv
        data/analysis/ttr_results.csv
        data/analysis/tfidf_contrast.csv
"""

import os, warnings, re
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from collections import Counter
from scipy.stats import mannwhitneyu
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
from kiwipiepy import Kiwi
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download("punkt",     quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

# ── paths ─────────────────────────────────────────────────────────────────────
ANALYSIS = Path("data/analysis")
FIGS     = ANALYSIS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

# ── Korean font ───────────────────────────────────────────────────────────────
KO_FONT_PATH = None
for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        KO_FONT_PATH = fp
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break
if KO_FONT_PATH is None:
    print("WARNING: Korean font not found — Korean labels may render as boxes")

PLACE_EN = {
    "경복궁":      "Gyeongbokgung",
    "창덕궁":      "Changdeokgung",
    "북촌한옥마을":  "Bukchon Village",
    "인사동길":     "Insadong-gil",
    "광장시장":     "Gwangjang Mkt",
    "홍대거리":     "Hongdae St.",
    "N서울타워":    "N Seoul Tower",
    "롯데월드":     "Lotte World",
    "광안리해수욕장": "Gwangalli Beach",
    "해운대해수욕장": "Haeundae Beach",
}
PALETTE = {"ko": "#2563EB", "en": "#DC2626"}

# ── load data ─────────────────────────────────────────────────────────────────
df      = pd.read_csv("data/corpus.csv",          encoding="utf-8-sig")
sent_df = pd.read_csv(ANALYSIS / "sentiment_results.csv")
topic_df= pd.read_csv(ANALYSIS / "topic_assignments.csv")

PLACES = [p for p in PLACE_EN if p in df["place"].unique()]

df = df.merge(
    sent_df[["place","language","text","sentiment","sentiment_label"]],
    on=["place","language","text"], how="left"
)

print(f"Loaded {len(df)} reviews, {len(PLACES)} places")

# ── helpers ───────────────────────────────────────────────────────────────────
kiwi = Kiwi()
NOUN_TAGS = {"NNG", "NNP"}
KO_STOP = {
    "것","수","이","가","에","을","를","은","는",
    "우리","너무","정말","진짜","매우","아주","더","좀","잘",
    "서울","한국","관광","여행","방문","관람","입장",
    "곳","때","분","번","명","개","원","층","사람","생각","느낌",
}
EN_STOP = set(stopwords.words("english")) | {
    "place","visit","visited","really","also","one","go","get","got",
    "would","could","like","even","around","much","lot","great","good",
    "beautiful","nice","amazing","wonderful","love","loved","highly",
    "recommend","definitely","must","see","time","day","tour","tourist",
    "korea","korean","seoul","everything","something","thing","things",
}

def nouns_ko(text):
    toks = kiwi.analyze(str(text))[0][0]
    return [t.form for t in toks if t.tag in NOUN_TAGS and len(t.form)>1 and t.form not in KO_STOP]

def nouns_en(text):
    toks = word_tokenize(str(text).lower())
    return [t for t in toks if t.isalpha() and len(t)>2 and t not in EN_STOP]

# ═══════════════════════════════════════════════════════════════════════════════
# 1. SENTIMENT BAR CHART
# ═══════════════════════════════════════════════════════════════════════════════
print("1. Sentiment bar chart...")

agg = df.groupby(["place","language"])["sentiment"].agg(["mean","std","count"]).reset_index()

fig, ax = plt.subplots(figsize=(9, 5))
x      = np.arange(len(PLACES))
width  = 0.35

for i, (lang, offset) in enumerate([("ko", -width/2), ("en", width/2)]):
    vals = [agg.loc[(agg.place==p)&(agg.language==lang), "mean"].values[0] for p in PLACES]
    errs = [agg.loc[(agg.place==p)&(agg.language==lang), "std"].values[0]  for p in PLACES]
    bars = ax.bar(x + offset, vals, width, yerr=errs, label="Korean (Naver)" if lang=="ko" else "English (GMaps)",
                  color=PALETTE[lang], alpha=0.85, capsize=4, error_kw={"linewidth":1.2})
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                f"{v:.2f}", ha="center", va="bottom", fontsize=8.5)

ax.set_xticks(x)
ax.set_xticklabels([PLACE_EN[p] for p in PLACES], fontsize=10)
ax.set_ylim(0, 1.15)
ax.set_ylabel("Mean Sentiment Score", fontsize=11)
ax.set_title("Sentiment by Place and Reviewer Group", fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.axhline(0, color="black", linewidth=0.5, linestyle="--")
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
fig.savefig(FIGS / "01_sentiment_bar.png", dpi=300)
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# 2. SENTIMENT HEATMAP
# ═══════════════════════════════════════════════════════════════════════════════
print("2. Sentiment heatmap...")

pivot = agg.pivot(index="place", columns="language", values="mean").reindex(PLACES)
pivot.index = [PLACE_EN[p] for p in PLACES]
pivot.columns = ["English", "Korean"]

cmap = LinearSegmentedColormap.from_list("rg", ["#ef4444","#fef9c3","#22c55e"])
fig, ax = plt.subplots(figsize=(5, 4))
im = ax.imshow(pivot.values, cmap=cmap, vmin=-0.2, vmax=1.0, aspect="auto")
plt.colorbar(im, ax=ax, label="Mean Sentiment")
ax.set_xticks([0,1]); ax.set_xticklabels(pivot.columns, fontsize=11)
ax.set_yticks(range(len(pivot))); ax.set_yticklabels(pivot.index, fontsize=10)
for i in range(len(pivot)):
    for j in range(2):
        ax.text(j, i, f"{pivot.values[i,j]:.2f}", ha="center", va="center",
                fontsize=12, fontweight="bold",
                color="white" if pivot.values[i,j] < 0.3 else "black")
ax.set_title("Sentiment Heatmap\n(place × reviewer group)", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(FIGS / "02_sentiment_heatmap.png", dpi=300)
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# 3. WORD CLOUDS
# ═══════════════════════════════════════════════════════════════════════════════
print("3. Word clouds...")

def make_wc(words_freq, font_path, color, out_path, title):
    wc = WordCloud(
        width=800, height=400, background_color="white",
        max_words=80, colormap=None,
        font_path=font_path if font_path else None,
        color_func=lambda *a, **k: color,
    ).generate_from_frequencies(words_freq)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close()

ko_texts = df[df.language=="ko"]["text"].tolist()
en_texts = df[df.language=="en"]["text"].tolist()

ko_words = Counter()
for t in ko_texts:
    ko_words.update(nouns_ko(t))

en_words = Counter()
for t in en_texts:
    en_words.update(nouns_en(t))

make_wc(dict(ko_words.most_common(100)),
        KO_FONT_PATH, "#2563EB",
        FIGS / "03a_wordcloud_ko.png",
        "Korean Reviewers — Top Nouns (Naver)")

make_wc(dict(en_words.most_common(100)),
        None, "#DC2626",
        FIGS / "03b_wordcloud_en.png",
        "English Reviewers — Top Nouns (Google Maps)")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. TOPIC DISTRIBUTION HEATMAP
# ═══════════════════════════════════════════════════════════════════════════════
print("4. Topic distribution heatmap...")

# load topic labels from CSVs
topic_labels = {}
for lang in ["en", "ko"]:
    tl_df = pd.read_csv(ANALYSIS / f"lda_{lang}_topics.csv")
    if "label" in tl_df.columns:
        topic_labels[lang] = {row["topic"]: row["label"] for _, row in tl_df.iterrows()}
    else:
        topic_labels[lang] = {row["topic"]: f"Topic {row['topic']}" for _, row in tl_df.iterrows()}

for lang, group_label in [("ko","Korean"), ("en","English")]:
    sub = topic_df[topic_df.language==lang].copy()
    sub = sub[sub.dominant_topic > 0]
    cross = pd.crosstab(sub["place"], sub["dominant_topic"])
    cross = cross.reindex(PLACES).fillna(0)
    cross.index = [PLACE_EN[p] for p in PLACES]
    cross_pct = cross.div(cross.sum(axis=1), axis=0) * 100

    col_labels = [topic_labels[lang].get(int(c), f"Topic {c}") for c in cross_pct.columns]

    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(cross_pct.values, cmap="YlOrRd", aspect="auto")
    plt.colorbar(im, ax=ax, label="% of reviews")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=8.5, rotation=20, ha="right")
    ax.set_yticks(range(len(cross_pct)))
    ax.set_yticklabels(cross_pct.index, fontsize=10)
    for i in range(len(cross_pct)):
        for j in range(len(cross_pct.columns)):
            ax.text(j, i, f"{cross_pct.values[i,j]:.0f}%",
                    ha="center", va="center", fontsize=9,
                    color="white" if cross_pct.values[i,j] > 55 else "black")
    ax.set_title(f"Topic Distribution per Place — {group_label} Reviews", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / f"04_topic_dist_{lang}.png", dpi=300)
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# 5. TTR (Type-Token Ratio)
# ═══════════════════════════════════════════════════════════════════════════════
print("5. TTR analysis...")

def ttr(text, lang):
    if lang == "ko":
        tokens = nouns_ko(text)
    else:
        tokens = nouns_en(text)
    if len(tokens) < 5:
        return None
    return len(set(tokens)) / len(tokens)

df["ttr"] = df.apply(lambda r: ttr(r["text"], r["language"]), axis=1)
ttr_agg = df.dropna(subset=["ttr"]).groupby(["place","language"])["ttr"].agg(["mean","std","count"]).reset_index()
ttr_agg.to_csv(ANALYSIS / "ttr_results.csv", index=False, encoding="utf-8-sig")

fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(PLACES))
for lang, offset in [("ko", -width/2), ("en", width/2)]:
    vals = [ttr_agg.loc[(ttr_agg.place==p)&(ttr_agg.language==lang), "mean"].values[0]
            if len(ttr_agg.loc[(ttr_agg.place==p)&(ttr_agg.language==lang)])>0 else 0
            for p in PLACES]
    errs = [ttr_agg.loc[(ttr_agg.place==p)&(ttr_agg.language==lang), "std"].values[0]
            if len(ttr_agg.loc[(ttr_agg.place==p)&(ttr_agg.language==lang)])>0 else 0
            for p in PLACES]
    bars = ax.bar(x + offset, vals, width, yerr=errs,
                  label="Korean (Naver)" if lang=="ko" else "English (GMaps)",
                  color=PALETTE[lang], alpha=0.85, capsize=4)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{v:.2f}", ha="center", va="bottom", fontsize=8.5)

ax.set_xticks(x)
ax.set_xticklabels([PLACE_EN[p] for p in PLACES], fontsize=10)
ax.set_ylim(0, 1.1)
ax.set_ylabel("Type-Token Ratio (TTR)", fontsize=11)
ax.set_title("Lexical Diversity (TTR) by Place and Reviewer Group", fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
fig.savefig(FIGS / "05_ttr_bar.png", dpi=300)
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# 6. TF-IDF KEYWORD CONTRAST
# ═══════════════════════════════════════════════════════════════════════════════
print("6. TF-IDF keyword contrast...")

def get_top_tfidf(texts, tokenize_fn, top_n=15):
    tokenized = [" ".join(tokenize_fn(t)) for t in texts]
    vec = TfidfVectorizer(max_features=200, min_df=2)
    try:
        X = vec.fit_transform(tokenized)
        scores = np.asarray(X.mean(axis=0)).flatten()
        top_idx = scores.argsort()[::-1][:top_n]
        words = np.array(vec.get_feature_names_out())
        return list(zip(words[top_idx], scores[top_idx].round(4)))
    except Exception:
        return []

ko_tfidf = get_top_tfidf(ko_texts, nouns_ko)
en_tfidf = get_top_tfidf(en_texts, nouns_en)

contrast_rows = []
max_len = max(len(ko_tfidf), len(en_tfidf))
for i in range(max_len):
    contrast_rows.append({
        "rank": i + 1,
        "ko_word":  ko_tfidf[i][0] if i < len(ko_tfidf) else "",
        "ko_score": ko_tfidf[i][1] if i < len(ko_tfidf) else "",
        "en_word":  en_tfidf[i][0] if i < len(en_tfidf) else "",
        "en_score": en_tfidf[i][1] if i < len(en_tfidf) else "",
    })
contrast_df = pd.DataFrame(contrast_rows)
contrast_df.to_csv(ANALYSIS / "tfidf_contrast.csv", index=False, encoding="utf-8-sig")

# horizontal bar chart side-by-side
n_show = 12
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
for ax, data, lang, color, title in [
    (axes[0], ko_tfidf[:n_show], "ko", "#2563EB", "Korean — Top TF-IDF Keywords"),
    (axes[1], en_tfidf[:n_show], "en", "#DC2626", "English — Top TF-IDF Keywords"),
]:
    words  = [w for w, _ in reversed(data)]
    scores = [s for _, s in reversed(data)]
    bars = ax.barh(words, scores, color=color, alpha=0.8)
    ax.set_xlabel("Mean TF-IDF Score", fontsize=10)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.spines[["top","right"]].set_visible(False)
    for bar, s in zip(bars, scores):
        ax.text(bar.get_width() + 0.0005, bar.get_y() + bar.get_height()/2,
                f"{s:.4f}", va="center", fontsize=8)

fig.tight_layout()
fig.savefig(FIGS / "06_tfidf_contrast.png", dpi=300)
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# 7. MANN-WHITNEY U TEST
# ═══════════════════════════════════════════════════════════════════════════════
print("7. Mann-Whitney U tests...")

mw_rows = []
for place in PLACES + ["ALL"]:
    if place == "ALL":
        ko_s = df[df.language=="ko"]["sentiment"].dropna().values
        en_s = df[df.language=="en"]["sentiment"].dropna().values
    else:
        ko_s = df[(df.place==place)&(df.language=="ko")]["sentiment"].dropna().values
        en_s = df[(df.place==place)&(df.language=="en")]["sentiment"].dropna().values
    stat, p = mannwhitneyu(ko_s, en_s, alternative="greater")
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "n.s."))
    mw_rows.append({
        "place":    place,
        "ko_mean":  round(ko_s.mean(), 4),
        "en_mean":  round(en_s.mean(), 4),
        "U_stat":   round(stat, 2),
        "p_value":  round(p, 6),
        "sig":      sig,
    })
    print(f"  {place:<16} KO={ko_s.mean():.3f}  EN={en_s.mean():.3f}  p={p:.4f} {sig}")

mw_df = pd.DataFrame(mw_rows)
mw_df.to_csv(ANALYSIS / "stats_mannwhitney.csv", index=False, encoding="utf-8-sig")
print("  Saved: stats_mannwhitney.csv")

# ═══════════════════════════════════════════════════════════════════════════════
# 8. DUMP ALL DATA AS JSON (machine-readable, no PNG scanning needed)
# ═══════════════════════════════════════════════════════════════════════════════
print("8. Saving analysis_data.json...")
import json

# topic distribution per place × language
topic_dist = {}
for lang in ["ko", "en"]:
    sub = topic_df[topic_df.language == lang]
    sub = sub[sub.dominant_topic > 0]
    for place in PLACES:
        counts = sub[sub.place == place]["dominant_topic"].value_counts().to_dict()
        total  = sum(counts.values()) or 1
        topic_dist.setdefault(place, {})[lang] = {
            str(t): {"count": int(c), "pct": round(c / total * 100, 1)}
            for t, c in sorted(counts.items())
        }

# LDA top words
lda_en = pd.read_csv(ANALYSIS / "lda_en_topics.csv").to_dict(orient="records")
lda_ko = pd.read_csv(ANALYSIS / "lda_ko_topics.csv").to_dict(orient="records")

# TTR per place × language
ttr_json = {}
for _, row in ttr_agg.iterrows():
    ttr_json.setdefault(row["place"], {})[row["language"]] = {
        "mean": round(row["mean"], 4),
        "std":  round(row["std"],  4),
        "n":    int(row["count"]),
    }

analysis_data = {
    "corpus_size": int(len(df)),
    "places": PLACES,
    "sentiment": {
        place: {
            lang: {
                "mean": round(float(agg.loc[(agg.place==place)&(agg.language==lang), "mean"].values[0]), 4),
                "std":  round(float(agg.loc[(agg.place==place)&(agg.language==lang), "std"].values[0]),  4),
                "n":    int(agg.loc[(agg.place==place)&(agg.language==lang), "count"].values[0]),
            }
            for lang in ["ko", "en"]
        }
        for place in PLACES
    },
    "mann_whitney": mw_rows,
    "ttr": ttr_json,
    "tfidf_top15": {
        "ko": [{"word": w, "score": float(s)} for w, s in ko_tfidf],
        "en": [{"word": w, "score": float(s)} for w, s in en_tfidf],
    },
    "wordcloud_top50": {
        "ko": [{"word": w, "freq": int(c)} for w, c in ko_words.most_common(50)],
        "en": [{"word": w, "freq": int(c)} for w, c in en_words.most_common(50)],
    },
    "topic_distribution": topic_dist,
    "lda_topics": {
        "en": lda_en,
        "ko": lda_ko,
    },
    "topic_labels": {
        lang: {str(t): lbl for t, lbl in topic_labels[lang].items()}
        for lang in ["en", "ko"]
    },
}

with open(ANALYSIS / "analysis_data.json", "w", encoding="utf-8") as f:
    json.dump(analysis_data, f, ensure_ascii=False, indent=2)
print("  Saved: analysis_data.json")

# ═══════════════════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n── All figures saved to {FIGS} ──")
for f in sorted(FIGS.iterdir()):
    print(f"  {f.name}")
