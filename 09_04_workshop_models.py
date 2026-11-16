"""
09_04_workshop_models.py
Workshop paper: two parallel regression models that treat Rating and Revisit
as observable traces of a latent satisfaction construct.

Framework follows supervisor feedback (prePPT2P1, min 42-53):
  Satisfaction (latent) --> Rating (declared signal)
                        --> Revisit (behavioural trace of prior experience)

Both models use the SAME predictor set so they can be compared directly:
  - Visit context: has_visit_info, waited, reserved, companion-*, purpose-*
  - Reviewer:      ln_user_followers, ln_user_reviews
  - Text:          ln_length, sentiment
  - Place:         fixed effects (Gyeongbokgung = reference)

Sample: reviews with text only, so both models share the same observations.

Model 1  Revisit (visit_count >= 2)      -> binary logistic regression
Model 2  Rating  (<=4 / 4.5 / 5, ordered) -> ordered logistic regression
         (Model 2b robustness: P(5 stars) binary logistic)

Standard errors clustered by reviewer in all models.

Outputs (data/analysis/naver/workshop/):
  wm1_revisit.csv, wm2_rating.csv, wm2b_five_star.csv,
  wm_vif.csv, wm_summary.txt, figures/wm1_*.png, wm2_*.png

Run:  python 09_04_workshop_models.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.stats.outliers_influence import variance_inflation_factor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop"
FIGS = OUT / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

LABELS = {
    "has_visit_info": "Visit info provided",
    "waited": "Waited to enter",
    "reserved": "Reservation",
    "comp_alone": "With: alone",
    "comp_partner": "With: partner/spouse",
    "comp_friend": "With: friends",
    "comp_child": "With: children",
    "comp_family": "With: parents/relatives",
    "comp_colleague": "With: colleagues",
    "purp_travel": "Purpose: travel",
    "purp_outing": "Purpose: outing",
    "purp_daily": "Purpose: daily life",
    "purp_date": "Purpose: date",
    "purp_social": "Purpose: socializing",
    "ln_user_followers": "ln(1 + reviewer's followers)",
    "ln_user_reviews":   "ln(1 + reviewer's reviews)",
    "ln_length":         "ln(text length)",
    "sentiment":         "Sentiment (-1 to 1)",
}

VISIT    = ["has_visit_info", "waited", "reserved",
            "comp_alone", "comp_partner", "comp_friend",
            "comp_child", "comp_family", "comp_colleague",
            "purp_travel", "purp_outing", "purp_daily", "purp_date", "purp_social"]
REVIEWER = ["ln_user_followers", "ln_user_reviews"]
TEXT     = ["ln_length", "sentiment"]
SHARED   = VISIT + REVIEWER + TEXT


# ───────── helpers ──────────────────────────────────────────────────────────
def design(data, cols, const=True):
    places = pd.get_dummies(data["place"], prefix="place", drop_first=True, dtype=float)
    X = pd.concat([data[cols].astype(float), places], axis=1)
    return sm.add_constant(X) if const else X


def clusters(data):
    return {"groups": pd.factorize(data["user_id"])[0]}


def varying_places(data, y, label):
    """Drop places where the binary outcome never varies (perfect separation under place FE)."""
    keep = data.groupby("place")[y].transform(lambda s: s.nunique() > 1)
    dropped = sorted(data.loc[~keep, "place"].unique())
    if dropped:
        print(f"  {label}: dropped places with no variation in {y}: "
              f"{', '.join(dropped)} ({int((~keep).sum())} reviews)")
    return data[keep].reset_index(drop=True)


def tidy(res):
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "p": res.pvalues})
    out = out[~out.index.str.startswith(("place_", "const")) & ~out.index.str.contains("/")]
    out["label"]   = out.index.map(LABELS)
    out["ratio"]   = np.exp(out["coef"])
    out["ci_low"]  = np.exp(out["coef"] - 1.96 * out["se"])
    out["ci_high"] = np.exp(out["coef"] + 1.96 * out["se"])
    out["sig"] = pd.cut(out["p"], [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                        labels=["***", "**", "*", ".", ""])
    return out


def show(title, table, ratio_name="OR"):
    print("\n" + "=" * 92)
    print(title)
    print("-" * 92)
    print(f"{'Variable':<32}{'coef':>8}{ratio_name:>8}{'95% CI':>18}{'p':>9}")
    print("-" * 92)
    for _, r in table.iterrows():
        print(f"{r.label:<32}{r.coef:>8.3f}{r.ratio:>8.2f}"
              f"{f'[{r.ci_low:.2f}, {r.ci_high:.2f}]':>18}{r.p:>9.4f} {r.sig}")
    print("=" * 92)


def forest(table, title, xlabel, path):
    t = table.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.38 * len(t) + 1.5))
    colors = ["#2563EB" if p < 0.05 else "#9CA3AF" for p in t["p"]]
    ax.hlines(range(len(t)), t["ci_low"], t["ci_high"], colors=colors, linewidth=1.4)
    ax.scatter(t["ratio"], range(len(t)), c=colors, zorder=3, s=28)
    ax.axvline(1, color="#111827", lw=0.8, ls="--")
    ax.set_xscale("log")
    ticks = [x for x in (0.125, 0.25, 0.5, 1, 2, 4, 8)
             if t["ci_low"].min() / 1.5 <= x <= t["ci_high"].max() * 1.5]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{x:g}" for x in ticks])
    ax.minorticks_off()
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels(t["label"], fontsize=9)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontweight="bold", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def mcfadden_ordered(res, y):
    counts = np.bincount(y)
    ll0 = np.sum(counts[counts > 0] * np.log(counts[counts > 0] / len(y)))
    return 1 - res.llf / ll0


def save(table, name):
    table.round(4).to_csv(OUT / name, encoding="utf-8-sig")


# ───────── load data ────────────────────────────────────────────────────────
df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
print(f"Reviews with text: {len(df_text)} | reviewers: {df_text.user_id.nunique()} | "
      f"places: {df_text.place.nunique()}")
print(f"Shared predictor set: {len(SHARED)} vars (+ {df_text.place.nunique() - 1} place dummies)")

# ───────── VIF on the shared predictor set ──────────────────────────────────
Xv = sm.add_constant(df_text[SHARED].astype(float))
vif = pd.DataFrame({"variable": SHARED,
                    "VIF": [variance_inflation_factor(Xv.values, i + 1)
                            for i in range(len(SHARED))]})
vif.round(2).to_csv(OUT / "wm_vif.csv", index=False, encoding="utf-8-sig")
print(f"VIF range on shared predictor set: {vif.VIF.min():.2f} to {vif.VIF.max():.2f}")
if vif.VIF.max() > 5:
    print("  Highest VIF:")
    print(vif.sort_values("VIF", ascending=False).head(3).to_string(index=False))

summaries = []

# ───────── Model 1: Revisit (binary logit) ──────────────────────────────────
d1 = varying_places(df_text, "revisit", "Model 1")
m1 = sm.Logit(d1["revisit"], design(d1, SHARED)).fit(
    disp=False, maxiter=200, cov_type="cluster", cov_kwds=clusters(d1))
t1 = tidy(m1)
save(t1, "wm1_revisit.csv")
show(f"MODEL 1  P(Revisit) | binary logistic, place FE, SE clustered by reviewer | "
     f"N = {int(m1.nobs)} ({d1.user_id.nunique()} reviewers), "
     f"revisit = {d1.revisit.mean():.1%}, pseudo-R2 = {m1.prsquared:.3f}", t1)
summaries.append("MODEL 1  P(Revisit) | binary logistic\n" + str(m1.summary()))
forest(t1,
       "Model 1: Visit context and the probability of being a revisitor",
       "Odds ratio (log scale; >1 = more likely to be a revisitor)",
       FIGS / "wm1_revisit.png")

# ───────── Model 2: Rating (ordered logit, 3 classes) ───────────────────────
d2 = df_text.dropna(subset=["rating"]).reset_index(drop=True)
d2["rating_cls"] = pd.cut(d2["rating"], [0, 4, 4.5, 5], labels=False).astype(int)
d2["five_star"]  = (d2["rating"] == 5).astype(int)
d2 = varying_places(d2, "five_star", "Model 2")

print(f"\nRating distribution in the Model 2 sample (N = {len(d2)}):")
print(d2["rating"].value_counts().sort_index().to_string())

m2 = OrderedModel(d2["rating_cls"],
                  design(d2, SHARED, const=False), distr="logit").fit(
    method="bfgs", disp=False, maxiter=2000,
    cov_type="cluster", cov_kwds=clusters(d2))
t2 = tidy(m2)
save(t2, "wm2_rating.csv")
show(f"MODEL 2  Rating (<=4 / 4.5 / 5) | ordered logit, place FE, SE clustered | "
     f"N = {int(m2.nobs)} ({d2.user_id.nunique()} reviewers), "
     f"5 stars = {d2.five_star.mean():.1%}, "
     f"McFadden R2 = {mcfadden_ordered(m2, d2['rating_cls'].to_numpy()):.3f}", t2)
summaries.append("MODEL 2  Rating | ordered logit\n" + str(m2.summary()))
forest(t2,
       "Model 2: Visit context and higher star ratings",
       "Odds ratio (log scale; >1 = higher rating category)",
       FIGS / "wm2_rating.png")

# ───────── Model 2b (robustness): P(5 stars) ────────────────────────────────
m2b = sm.Logit(d2["five_star"], design(d2, SHARED)).fit(
    disp=False, maxiter=200, cov_type="cluster", cov_kwds=clusters(d2))
t2b = tidy(m2b)
save(t2b, "wm2b_five_star.csv")
show(f"MODEL 2b (robustness)  P(5 stars) | binary logistic, clustered SE | "
     f"N = {int(m2b.nobs)}, pseudo-R2 = {m2b.prsquared:.3f}", t2b)
summaries.append("MODEL 2b  P(5 stars)\n" + str(m2b.summary()))

both2 = (np.sign(t2["coef"]) == np.sign(t2b.loc[t2.index, "coef"])) \
        & (t2["p"] < 0.05) & (t2b.loc[t2.index, "p"] < 0.05)
print(f"Significant in both ordered logit (M2) and 5-star logit (M2b): "
      f"{', '.join(t2.loc[both2, 'label']) or 'none'}")

# ───────── Side-by-side summary: M1 (Revisit) vs M2 (Rating) ────────────────
comp = t1[["label", "ratio", "p"]].join(
    t2[["ratio", "p"]], rsuffix="_m2", how="outer")
comp.columns = ["label", "OR_revisit", "p_revisit", "OR_rating", "p_rating"]
comp["sig_revisit"] = pd.cut(comp["p_revisit"],
                              [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                              labels=["***", "**", "*", ".", ""])
comp["sig_rating"]  = pd.cut(comp["p_rating"],
                              [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                              labels=["***", "**", "*", ".", ""])
comp.round(4).to_csv(OUT / "wm_comparison.csv", encoding="utf-8-sig")

print("\n" + "=" * 92)
print("SIDE-BY-SIDE: predictors in Model 1 (Revisit) vs Model 2 (Rating)")
print("-" * 92)
print(f"{'Predictor':<32}{'OR (Revisit)':>14}{'p':>8}{'OR (Rating)':>14}{'p':>8}  pattern")
print("-" * 92)
for _, r in comp.iterrows():
    pattern = []
    if r.p_revisit < 0.05:
        pattern.append("rev")
    if r.p_rating < 0.05:
        pattern.append("rat")
    tag = ("both" if len(pattern) == 2
           else "/".join(pattern) if pattern
           else "—")
    print(f"{str(r.label):<32}{r.OR_revisit:>14.2f}{r.p_revisit:>8.3f}"
          f"{r.OR_rating:>14.2f}{r.p_rating:>8.3f}  {tag}")
print("=" * 92)

# ───────── Save summaries ──────────────────────────────────────────────────
(OUT / "wm_summary.txt").write_text("\n\n".join(summaries), encoding="utf-8")

print("\n" + "=" * 60)
print("DONE — workshop models (2 models, shared predictors)")
print("=" * 60)
print(f"CSVs:     {OUT}/wm1_revisit.csv, wm2_rating.csv, wm2b_five_star.csv")
print(f"Compare:  {OUT}/wm_comparison.csv")
print(f"VIF:      {OUT}/wm_vif.csv")
print(f"Summary:  {OUT}/wm_summary.txt")
print(f"Figures:  {FIGS}/wm1_revisit.png, wm2_rating.png")
