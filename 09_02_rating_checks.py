"""
09_02_rating_checks.py
Uses the star ratings (1-5) that some reviews carry.

1. Sentiment validation: Spearman correlation between the text sentiment score and the
   star rating, and how well sentiment separates low (<= 3) from high ratings (AUC).
   Cross-cultural corpus (KO and EN) and Korean-only dataset.
2. H5 with real ratings: are Korean reviewers more favourable than English-language ones?
   One-sided Mann-Whitney U on ratings, chi-square on the share of 5-star reviews.
   Missingness check: Korean reviews with vs without a rating (sentiment compared).
3. Korean-only dataset: ratings of revisitors vs first-time visitors.

Ratings are missing for many Korean reviews (the platform shows stars only on some),
so all rating results refer to the rated subset.

Outputs: data/analysis/rating_checks.csv
Run (base env, after 04 and 09):  python 09_02_rating_checks.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, mannwhitneyu, chi2_contingency
from sklearn.metrics import roc_auc_score

ANALYSIS = Path("data/analysis")
KEY = ["place", "language", "text"]
rows = []


def add(section, item, n, stat, p=np.nan, note=""):
    rows.append({"section": section, "item": item, "n": n, "statistic": round(stat, 4),
                 "p": round(p, 4) if not np.isnan(p) else np.nan, "note": note})
    p_txt = f"p = {p:.4f}" if not np.isnan(p) else ""
    print(f"  {item:<44} n = {n:<5} {stat:>8.3f}   {p_txt}  {note}")


corpus = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
sent = pd.read_csv(ANALYSIS / "sentiment_results.csv").drop_duplicates(KEY)
corpus = corpus.merge(sent[KEY + ["sentiment"]], on=KEY, how="left")
naver = pd.read_csv(ANALYSIS / "naver" / "naver_dataset.csv", encoding="utf-8-sig")

# ── 1. sentiment validation ──────────────────────────────────────────────────
print("1. SENTIMENT vs STAR RATING (Spearman rho; AUC = sentiment separating <=3 from 4-5 stars)")
datasets = [("corpus EN", corpus[corpus.language == "en"]),
            ("corpus KO", corpus[corpus.language == "ko"]),
            ("Korean-only dataset", naver[naver.has_text == 1])]
for name, d in datasets:
    d = d.dropna(subset=["rating", "sentiment"])
    rho, p = spearmanr(d["sentiment"], d["rating"])
    add("sentiment_validation", f"{name}: Spearman rho", len(d), rho, p)
    low = (d["rating"] <= 3).astype(int)
    if 0 < low.sum() < len(d):
        add("sentiment_validation", f"{name}: AUC low rating (n low = {low.sum()})", len(d),
            roc_auc_score(low, -d["sentiment"]))

# ── 2. H5 with real ratings ──────────────────────────────────────────────────
print("\n2. H5 WITH STAR RATINGS (cross-cultural corpus, rated reviews only)")
rated = corpus.dropna(subset=["rating"])
ko, en = rated.loc[rated.language == "ko", "rating"], rated.loc[rated.language == "en", "rating"]
add("H5_ratings", "mean rating KO", len(ko), ko.mean())
add("H5_ratings", "mean rating EN", len(en), en.mean())
u, p = mannwhitneyu(ko, en, alternative="greater")
add("H5_ratings", "Mann-Whitney U (H1: KO > EN, one-sided)", len(rated), u, p)
table = np.array([[(ko == 5).sum(), (ko < 5).sum()], [(en == 5).sum(), (en < 5).sum()]])
chi2, p2, _, _ = chi2_contingency(table, correction=False)
p_one = p2 / 2 if (ko == 5).mean() > (en == 5).mean() else 1 - p2 / 2
add("H5_ratings", f"5-star share KO {(ko == 5).mean():.1%} vs EN {(en == 5).mean():.1%} (chi2)",
    len(rated), chi2, p_one, "one-sided")
add("H5_ratings", f"low ratings (<=3) KO {(ko <= 3).mean():.1%} vs EN {(en <= 3).mean():.1%}",
    len(rated), (ko <= 3).mean() - (en <= 3).mean())

import statsmodels.api as sm


def adjusted(data, x, cluster=None):
    """Rating ~ x + place FE (OLS) and P(5 stars) ~ x + place FE (logit)."""
    X = sm.add_constant(pd.concat(
        [data[[x]].astype(float),
         pd.get_dummies(data["place"], prefix="p", drop_first=True, dtype=float)], axis=1))
    cov = ({"cov_type": "cluster", "cov_kwds": {"groups": pd.factorize(data[cluster])[0]}}
           if cluster else {"cov_type": "HC1"})
    ols = sm.OLS(data["rating"].astype(float), X).fit(**cov)
    logit = sm.Logit((data["rating"] == 5).astype(int), X).fit(disp=False, **cov)
    return ols, logit


rated = rated.assign(is_ko=(rated.language == "ko").astype(int))
ols, logit = adjusted(rated, "is_ko")
print("   Adjusted for place (rated reviews; place fixed effects, robust SE):")
add("H5_ratings", "KO - EN rating difference, place-adjusted (OLS)", len(rated),
    ols.params["is_ko"], ols.pvalues["is_ko"] / 2 if ols.params["is_ko"] > 0 else 1 - ols.pvalues["is_ko"] / 2,
    "one-sided")
add("H5_ratings", "OR 5 stars KO vs EN, place-adjusted (logit)", len(rated),
    np.exp(logit.params["is_ko"]),
    logit.pvalues["is_ko"] / 2 if logit.params["is_ko"] > 0 else 1 - logit.pvalues["is_ko"] / 2,
    "one-sided")

print("\n   Missingness: Korean corpus reviews with vs without a rating")
ko_all = corpus[corpus.language == "ko"]
with_r, without_r = ko_all[ko_all.rating.notna()], ko_all[ko_all.rating.isna()]
add("H5_ratings", f"KO rated: {len(with_r)} / {len(ko_all)}", len(ko_all), len(with_r) / len(ko_all))
u, p = mannwhitneyu(with_r["sentiment"], without_r["sentiment"], alternative="two-sided")
add("H5_ratings", f"sentiment rated {with_r.sentiment.mean():.3f} vs unrated "
    f"{without_r.sentiment.mean():.3f}", len(ko_all), u, p, "two-sided")
print("   rated share by place (KO):",
      ko_all.groupby("place")["rating"].apply(lambda s: f"{s.notna().mean():.0%}").to_dict())

# ── 3. Korean-only: revisitors vs first-time visitors ────────────────────────
print("\n3. KOREAN-ONLY DATASET: RATINGS OF REVISITORS vs FIRST-TIME VISITORS")
nr = naver.dropna(subset=["rating"])
rev, first = nr.loc[nr.revisit == 1, "rating"], nr.loc[nr.revisit == 0, "rating"]
add("revisit_ratings", "mean rating revisitors", len(rev), rev.mean())
add("revisit_ratings", "mean rating first-time", len(first), first.mean())
u, p = mannwhitneyu(rev, first, alternative="two-sided")
add("revisit_ratings", "Mann-Whitney U (two-sided)", len(nr), u, p)
ols, logit = adjusted(nr, "revisit", cluster="user_id")
print("   Adjusted for place, SE clustered by reviewer:")
add("revisit_ratings", "rating difference revisit - first (OLS)", len(nr),
    ols.params["revisit"], ols.pvalues["revisit"])
add("revisit_ratings", "OR 5 stars revisit vs first (logit)", len(nr),
    np.exp(logit.params["revisit"]), logit.pvalues["revisit"])
print(f"   rated share: {naver.rating.notna().mean():.1%} of {len(naver)} reviews "
      f"(revisitors {naver.loc[naver.revisit == 1, 'rating'].notna().mean():.1%}, "
      f"first-time {naver.loc[naver.revisit == 0, 'rating'].notna().mean():.1%})")

out = ANALYSIS / "rating_checks.csv"
pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
print(f"\nSaved: {out}")
