"""
06_advanced_nlp.py
Two advanced NLP analyses using multilingual-e5-base embeddings
(intfloat/multilingual-e5-base — already cached, no download needed).

Part 1 — Zero-shot motivation classification
  Categories: Cultural Heritage, Food & Gastronomy, Photography & Visual,
              Shopping & Entertainment, Nature & Scenery
  Method: cosine similarity between review embedding and category label embedding.
  Works for BOTH Korean and English reviews in the same semantic space.

Part 2 — Cross-lingual cosine similarity KO vs EN per place
  For each place: embed all KO reviews → mean vector
                  embed all EN reviews → mean vector
  Cosine similarity(KO_mean, EN_mean) measures how "aligned" the two groups
  are in what they talk about. Low similarity = divergent experiences.

Outputs → data/analysis/
  motivation_results.csv       per-review motivation label + scores
  motivation_summary.csv       % per motivation × place × language
  crosslingual_similarity.csv  cosine sim per place (+ intra-group baseline)
  analysis_data.json           updated with new results
"""

import os, warnings, json
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TRANSFORMERS_OFFLINE"]  = "1"
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from torch import no_grad
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

# ── paths ─────────────────────────────────────────────────────────────────────
ANALYSIS = Path("data/analysis")
FIGS     = ANALYSIS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

# ── Korean font ───────────────────────────────────────────────────────────────
for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

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

df = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
PLACES = [p for p in PLACE_EN if p in df["place"].unique()]
print(f"Corpus: {len(df)} reviews, {len(PLACES)} places")

# ══════════════════════════════════════════════════════════════════════════════
# EMBEDDING MODEL
# ══════════════════════════════════════════════════════════════════════════════
print("\nLoading multilingual-e5-base...")
MODEL_ID  = "intfloat/multilingual-e5-base"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model     = AutoModel.from_pretrained(MODEL_ID)
model.eval()
print("  Model loaded OK")

def average_pool(last_hidden, attention_mask):
    mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)

def embed(texts, prefix="passage"):
    """Return L2-normalised embeddings, shape (n, 768)."""
    tagged = [f"{prefix}: {t}" for t in texts]
    BATCH  = 16
    vecs   = []
    for i in range(0, len(tagged), BATCH):
        batch = tagged[i:i+BATCH]
        enc   = tokenizer(batch, padding=True, truncation=True,
                          max_length=256, return_tensors="pt")
        with no_grad():
            out = model(**enc)
        v = average_pool(out.last_hidden_state, enc["attention_mask"])
        v = torch.nn.functional.normalize(v, p=2, dim=1)
        vecs.append(v.numpy())
    return np.vstack(vecs)

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — ZERO-SHOT MOTIVATION CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════
print("\n── Part 1: Zero-shot motivation classification ──")

# Category labels defined in both languages for robustness;
# e5 maps them to the same space, so one English label is enough.
MOTIVATIONS = {
    "Cultural Heritage & History":   "cultural heritage, history, historical site, traditional architecture, dynasty",
    "Food & Gastronomy":             "food, eating, traditional food, local cuisine, street food, restaurant, snack",
    "Photography & Visual Experience": "photography, photo spot, Instagram, scenic view, beautiful scenery, visual",
    "Shopping & Entertainment":      "shopping, clothes, stores, nightlife, entertainment, young people, street fashion",
    "Nature & Scenery":              "nature, scenery, landscape, mountains, sky, outdoor, garden, walking",
}

print("  Embedding motivation labels...")
label_names = list(MOTIVATIONS.keys())
label_texts = list(MOTIVATIONS.values())
label_vecs  = embed(label_texts, prefix="query")   # (5, 768)

print("  Embedding reviews...")
review_texts = df["text"].tolist()
review_vecs  = embed(review_texts, prefix="passage")  # (238, 768)

# cosine similarity: (238, 5)
sims = cosine_similarity(review_vecs, label_vecs)

# assign dominant motivation
dominant_idx    = sims.argmax(axis=1)
dominant_labels = [label_names[i] for i in dominant_idx]
dominant_scores = sims.max(axis=1).round(4)

motiv_df = df[["place","language","text"]].copy()
motiv_df["motivation"]       = dominant_labels
motiv_df["motivation_score"] = dominant_scores
for i, lbl in enumerate(label_names):
    motiv_df[f"sim_{i+1}"] = sims[:, i].round(4)

motiv_df.to_csv(ANALYSIS / "motivation_results.csv", index=False, encoding="utf-8-sig")
print("  Saved: motivation_results.csv")

# ── summary: % per motivation × place × language ─────────────────────────────
rows = []
for place in PLACES:
    for lang in ["ko","en"]:
        sub   = motiv_df[(motiv_df.place==place) & (motiv_df.language==lang)]
        total = len(sub)
        counts = sub["motivation"].value_counts()
        for m in label_names:
            rows.append({
                "place":      place,
                "language":   lang,
                "motivation": m,
                "count":      int(counts.get(m, 0)),
                "pct":        round(counts.get(m, 0) / total * 100, 1) if total else 0,
            })
summ_df = pd.DataFrame(rows)
summ_df.to_csv(ANALYSIS / "motivation_summary.csv", index=False, encoding="utf-8-sig")
print("  Saved: motivation_summary.csv")

# ── print table ───────────────────────────────────────────────────────────────
print("\n  Motivation distribution (% by language, all places):")
overall = motiv_df.groupby(["language","motivation"]).size().unstack(fill_value=0)
overall_pct = overall.div(overall.sum(axis=1), axis=0).mul(100).round(1)
print(overall_pct.to_string())

# ── figure: stacked bar per place × language ─────────────────────────────────
MOTIV_COLORS = {
    "Cultural Heritage & History":      "#1d4ed8",
    "Food & Gastronomy":                "#ea580c",
    "Photography & Visual Experience":  "#9333ea",
    "Shopping & Entertainment":         "#16a34a",
    "Nature & Scenery":                 "#0891b2",
}

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
for ax, lang, group_label in [(axes[0],"ko","Korean (Naver)"), (axes[1],"en","English (GMaps)")]:
    sub  = summ_df[summ_df.language == lang]
    piv  = sub.pivot(index="place", columns="motivation", values="pct").reindex(PLACES)
    piv.index = [PLACE_EN[p] for p in PLACES]
    piv  = piv[label_names]

    bottom = np.zeros(len(piv))
    for motiv in label_names:
        vals = piv[motiv].values
        bars = ax.bar(piv.index, vals, bottom=bottom,
                      color=MOTIV_COLORS[motiv], label=motiv, alpha=0.88)
        for bar, v, b in zip(bars, vals, bottom):
            if v >= 8:
                ax.text(bar.get_x() + bar.get_width()/2, b + v/2,
                        f"{v:.0f}%", ha="center", va="center",
                        fontsize=7.5, color="white", fontweight="bold")
        bottom += vals

    ax.set_ylim(0, 110)
    ax.set_ylabel("% of reviews", fontsize=10)
    ax.set_title(f"Travel Motivations — {group_label}", fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", rotation=15, labelsize=9)
    ax.spines[["top","right"]].set_visible(False)

handles, lbls = axes[0].get_legend_handles_labels()
fig.legend(handles, lbls, loc="lower center", ncol=3, fontsize=8.5,
           bbox_to_anchor=(0.5, -0.12))
fig.tight_layout()
fig.savefig(FIGS / "07_motivations_stacked.png", dpi=300, bbox_inches="tight")
plt.close()
print("  Saved: 07_motivations_stacked.png")

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — CROSS-LINGUAL COSINE SIMILARITY KO vs EN per place
# ══════════════════════════════════════════════════════════════════════════════
print("\n── Part 2: Cross-lingual cosine similarity ──")

sim_rows = []
for place in PLACES:
    ko_vecs = review_vecs[((df.place == place) & (df.language == "ko")).values]
    en_vecs = review_vecs[((df.place == place) & (df.language == "en")).values]

    ko_mean = ko_vecs.mean(axis=0, keepdims=True)
    en_mean = en_vecs.mean(axis=0, keepdims=True)

    # cross-group similarity (main metric)
    cross_sim = float(cosine_similarity(ko_mean, en_mean)[0, 0])

    # intra-group similarity (baseline: how coherent is each group internally?)
    ko_intra = float(cosine_similarity(ko_vecs).mean()) if len(ko_vecs) > 1 else 1.0
    en_intra = float(cosine_similarity(en_vecs).mean()) if len(en_vecs) > 1 else 1.0

    # divergence = 1 - cross/max(intra)  → 0 means perfectly aligned
    divergence = round(1 - cross_sim / max(ko_intra, en_intra), 4)

    sim_rows.append({
        "place":         place,
        "ko_en_sim":     round(cross_sim, 4),
        "ko_intra_sim":  round(ko_intra,  4),
        "en_intra_sim":  round(en_intra,  4),
        "divergence":    divergence,
    })
    print(f"  {place:<14}  KO↔EN sim={cross_sim:.3f}  "
          f"KO-intra={ko_intra:.3f}  EN-intra={en_intra:.3f}  "
          f"divergence={divergence:.3f}")

sim_df = pd.DataFrame(sim_rows)
sim_df.to_csv(ANALYSIS / "crosslingual_similarity.csv", index=False, encoding="utf-8-sig")
print("  Saved: crosslingual_similarity.csv")

# ── figure: grouped bar cross sim + intra sim ────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
x     = np.arange(len(PLACES))
w     = 0.25
names = [PLACE_EN[p] for p in PLACES]

ax.bar(x - w,   sim_df["ko_intra_sim"], w, label="KO intra-group",  color="#2563EB", alpha=0.8)
ax.bar(x,       sim_df["en_intra_sim"], w, label="EN intra-group",  color="#DC2626", alpha=0.8)
ax.bar(x + w,   sim_df["ko_en_sim"],    w, label="KO ↔ EN (cross)", color="#16a34a", alpha=0.9)

for i, row in sim_df.iterrows():
    for val, offset in [(row.ko_intra_sim,-w),(row.en_intra_sim,0),(row.ko_en_sim,w)]:
        ax.text(i + offset, val + 0.003, f"{val:.3f}",
                ha="center", va="bottom", fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=10)
ax.set_ylim(0.5, 1.05)
ax.set_ylabel("Cosine Similarity", fontsize=11)
ax.set_title("Cross-lingual Semantic Similarity: Korean vs English Reviewers",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=10)
ax.spines[["top","right"]].set_visible(False)
fig.tight_layout()
fig.savefig(FIGS / "08_crosslingual_sim.png", dpi=300)
plt.close()
print("  Saved: 08_crosslingual_sim.png")

# ══════════════════════════════════════════════════════════════════════════════
# UPDATE analysis_data.json
# ══════════════════════════════════════════════════════════════════════════════
json_path = ANALYSIS / "analysis_data.json"
if json_path.exists():
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {}

# motivation summary per place × language
motiv_json = {}
for place in PLACES:
    motiv_json[place] = {}
    for lang in ["ko","en"]:
        sub = summ_df[(summ_df.place==place) & (summ_df.language==lang)]
        motiv_json[place][lang] = {
            row["motivation"]: {"count": row["count"], "pct": row["pct"]}
            for _, row in sub.iterrows()
        }

data["motivation_classification"] = {
    "method":     "zero-shot via multilingual-e5-base cosine similarity",
    "categories": label_names,
    "per_place":  motiv_json,
    "overall_pct": {
        lang: overall_pct.loc[lang].to_dict()
        for lang in overall_pct.index
    },
}
data["crosslingual_similarity"] = sim_df.to_dict(orient="records")

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("\n  Updated: analysis_data.json")

print("\n── Done ──")
for f in sorted(FIGS.iterdir()):
    print(f"  {f.name}")
