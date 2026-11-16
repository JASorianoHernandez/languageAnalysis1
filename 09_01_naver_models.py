"""
09_01_naver_models.py
Review-level regression models on Korean reviews (data from 02_naver_build_dataset.py).

The same reviewer often writes several reviews (also of the same place), so every model
uses standard errors clustered by reviewer (pseudonymous user_id), and Model 1 is
re-estimated keeping one random review per reviewer and place.

Model 1   Revisit (visit_count >= 2), reviews with text        -> logistic regression
Model 1s  Model 1 with one random review per reviewer x place  -> sensitivity
Model 1b  Model 1 + ABSA aspect mentions (+/-)                 -> needs naver_absa.csv
          (python 06_llm_analysis.py --naver, faiss-gpu env)
Model 2   Keyword tags (0-5), ALL reviews incl. keyword-only    -> ordered logit
Model 2b  Model 2 as a bounded count                            -> binomial GLM (5 trials)
Model 2t  Model 2 on reviews with text, adding sentiment/length -> ordered logit
Model 3   Star rating (<=4 / 4.5 / 5), rated reviews only        -> ordered logit, reduced X
Model 3b  P(5 stars)                                            -> logistic (robustness)
Model 3t  Model 3 on rated reviews with text (+ sentiment, length)
Model 1x  Model 1 + season, weekend, verification, reviewer followers/photos and tag
          themes (instead of the tag count), with its own one-per-reviewer sensitivity
Model 2x  Model 2 + season, weekend, verification, reviewer followers/photos
Model 4   Reactions per review (helpfulness)                -> negative binomial,
          controlling for review age; Model 4b: P(any reaction), logistic
All models include place fixed effects (Gyeongbokgung = reference).
Associations only: the models cannot say why revisitors write differently.

Outputs (data/analysis/naver/):
  model1_revisit.csv, model1_sensitivity.csv, model1b_revisit_aspects.csv,
  model2_keywords.csv, model2b_keywords_binomial.csv, model2t_keywords_text.csv,
  vif.csv, models_summary.txt, figures/15-17_*.png

Run (base env):  python 09_01_naver_models.py
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
FIGS = DIR / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
SEED = 42

for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

LABELS = {
    "revisit": "Revisitor (2+ visits)",
    "has_text": "Wrote text (15+ chars)",
    "sentiment": "Sentiment (-1 to 1)",
    "n_tags": "Keyword tags (0-5)",
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
    "ln_length": "ln(text length)",
    "ln_photos": "ln(1 + photos)",
    "ln_user_reviews": "ln(1 + reviewer's reviews)",
}
VISIT = ["has_visit_info", "waited", "reserved",
         "comp_alone", "comp_partner", "comp_friend", "comp_child", "comp_family", "comp_colleague",
         "purp_travel", "purp_outing", "purp_daily", "purp_date", "purp_social"]
# ln_photos is not used: the scraped photo count captured reaction icons, not review photos
CONTROLS = ["ln_length", "ln_user_reviews"]
ASPECTS = ["historical_cultural", "accessibility", "crowding", "food", "visual_photo"]

df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
print(f"Reviews: {len(df_all)} (with text {len(df_text)}, keyword-only {len(df_all) - len(df_text)})"
      f"  |  reviewers: {df_all.user_id.nunique()}  |  reference place: {sorted(df_all.place.unique())[0]}")


def design(data, cols, const=True):
    places = pd.get_dummies(data["place"], prefix="place", drop_first=True, dtype=float)
    X = pd.concat([data[cols].astype(float), places], axis=1)
    return sm.add_constant(X) if const else X


LABELS.update({
    "season_summer": "Visit: summer", "season_autumn": "Visit: autumn",
    "season_winter": "Visit: winter", "visit_weekend": "Visit: weekend",
    "verif_receipt": "Verified by receipt",
    "ln_user_followers": "ln(1 + reviewer's followers)",
    "ln_user_photos": "ln(1 + reviewer's photos)",
    "ln_review_age": "ln(1 + days since visit)",
    "tag_visual": "Tags: visual", "tag_content": "Tags: things to see/learn",
    "tag_crowded": "Tags: crowded", "tag_quiet": "Tags: quiet",
    "tag_facilities": "Tags: facilities", "tag_access": "Tags: access",
    "tag_family": "Tags: family/kids", "tag_value": "Tags: price/value",
    "tag_food": "Tags: food", "tag_water": "Tags: water leisure",
})
# Extended specification: variables available for every place after the re-scrape.
# verif_reservation is left out because it duplicates `reserved` (same reservations).
NEW_COLS = ["season_summer", "season_autumn", "season_winter", "visit_weekend",
            "verif_receipt", "ln_user_followers"]   # ln_user_photos: VIF > 7 with ln_user_reviews
TAG_COLS = ["tag_visual", "tag_content", "tag_crowded", "tag_quiet", "tag_facilities",
            "tag_access", "tag_family", "tag_value", "tag_food", "tag_water"]


def varying_places(data, y, label):
    """Drop places where a binary outcome never varies: their fixed effect diverges
    (perfect separation) and, with place fixed effects, they carry no information."""
    keep = data.groupby("place")[y].transform(lambda s: s.nunique() > 1)
    dropped = sorted(data.loc[~keep, "place"].unique())
    if dropped:
        print(f"  {label}: dropped places with no variation in {y}: {', '.join(dropped)} "
              f"({int((~keep).sum())} reviews)")
    return data[keep].reset_index(drop=True)


def clusters(data):
    return {"groups": pd.factorize(data["user_id"])[0]}


def tidy(res):
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "p": res.pvalues})
    out = out[~out.index.str.startswith(("place_", "const")) & ~out.index.str.contains("/")]
    out["label"] = out.index.map(LABELS)
    out["ratio"] = np.exp(out["coef"])
    out["ci_low"] = np.exp(out["coef"] - 1.96 * out["se"])
    out["ci_high"] = np.exp(out["coef"] + 1.96 * out["se"])
    out["sig"] = pd.cut(out["p"], [-1, 0.001, 0.01, 0.05, 0.1, 1.1], labels=["***", "**", "*", ".", ""])
    return out


def show(title, table, ratio_name="OR"):
    print("\n" + "=" * 92)
    print(title)
    print("-" * 92)
    print(f"{'Variable':<32}{'coef':>8}{ratio_name:>8}{'95% CI':>18}{'p':>9}")
    print("-" * 92)
    for _, r in table.iterrows():
        print(f"{r.label:<32}{r.coef:>8.3f}{r.ratio:>8.2f}{f'[{r.ci_low:.2f}, {r.ci_high:.2f}]':>18}"
              f"{r.p:>9.4f} {r.sig}")
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


def save(table, name):
    table.round(4).to_csv(DIR / name, encoding="utf-8-sig")


summaries = []

# ── VIF ──────────────────────────────────────────────────────────────────────
vif_cols = VISIT + ["sentiment", "n_tags", "revisit"] + CONTROLS
Xv = sm.add_constant(df_text[vif_cols].astype(float))
vif = pd.DataFrame({"variable": vif_cols,
                    "VIF": [variance_inflation_factor(Xv.values, i + 1) for i in range(len(vif_cols))]})
vif.round(2).to_csv(DIR / "vif.csv", index=False, encoding="utf-8-sig")
print(f"VIF range: {vif.VIF.min():.2f} to {vif.VIF.max():.2f}")

# ── Model 1: revisit (reviews with text), SE clustered by reviewer ───────────
M1_COLS = VISIT + ["sentiment", "n_tags"] + CONTROLS
m1 = sm.Logit(df_text["revisit"], design(df_text, M1_COLS)).fit(
    disp=False, maxiter=200, cov_type="cluster", cov_kwds=clusters(df_text))
t1 = tidy(m1)
save(t1, "model1_revisit.csv")
show(f"MODEL 1  P(revisit) | logistic, place FE, SE clustered by reviewer | N = {int(m1.nobs)} "
     f"({df_text.user_id.nunique()} reviewers), revisit = {df_text.revisit.mean():.1%}, "
     f"pseudo-R2 = {m1.prsquared:.3f}", t1)
summaries.append(str(m1.summary()))
forest(t1, "Model 1: what is associated with revisiting?",
       "Odds ratio (log scale; >1 = more likely to be a revisitor)", FIGS / "15_model1_revisit.png")

# ── Model 1s: one random review per reviewer x place ─────────────────────────
one = (df_text.sample(frac=1, random_state=SEED)
              .drop_duplicates(["user_id", "place"]).sort_index())
one = varying_places(one, "revisit", "Model 1s")
m1s = sm.Logit(one["revisit"], design(one, M1_COLS)).fit(disp=False, maxiter=200, cov_type="HC1")
t1s = tidy(m1s)
comp = t1[["label", "ratio", "p"]].join(t1s[["ratio", "p"]], rsuffix="_one")
comp["same_conclusion"] = np.where((comp["p"] < 0.05) == (comp["p_one"] < 0.05), "yes", "NO")
comp.round(4).to_csv(DIR / "model1_sensitivity.csv", encoding="utf-8-sig")
print(f"\nMODEL 1s  sensitivity: one random review per reviewer x place | N = {int(m1s.nobs)}, "
      f"revisit = {one.revisit.mean():.1%}, pseudo-R2 = {m1s.prsquared:.3f}")
print(f"{'Variable':<32}{'OR all':>8}{'p':>8}{'OR one':>9}{'p':>8}   same conclusion (p<.05)")
for _, r in comp.iterrows():
    print(f"{r.label:<32}{r.ratio:>8.2f}{r.p:>8.3f}{r.ratio_one:>9.2f}{r.p_one:>8.3f}   {r.same_conclusion}")
summaries.append(str(m1s.summary()))

# ── Model 1b: revisit + ABSA aspects ─────────────────────────────────────────
absa_path = DIR / "naver_absa.csv"
if absa_path.exists():
    absa = pd.read_csv(absa_path, encoding="utf-8-sig")[["place", "text", *ASPECTS]]
    d1b = df_text.merge(absa, on=["place", "text"], how="inner").dropna(subset=ASPECTS)
    aspect_cols = []
    for a in ASPECTS:
        for sign, val in (("pos", 1), ("neg", -1)):
            col = f"{a}_{sign}"
            d1b[col] = (d1b[a] == val).astype(float)
            n = int(d1b[col].sum())
            if n >= 10:
                aspect_cols.append(col)
                short = {"historical_cultural": "history", "visual_photo": "visual"}.get(a, a)
                LABELS[col] = f"ABSA {short} {'+' if val == 1 else '-'} (n={n})"
            else:
                print(f"  Model 1b: dropped {col} (only {n} reviews)")
    m1b = sm.Logit(d1b["revisit"], design(d1b, M1_COLS + aspect_cols)).fit(
        disp=False, maxiter=200, cov_type="cluster", cov_kwds=clusters(d1b))
    t1b = tidy(m1b)
    save(t1b, "model1b_revisit_aspects.csv")
    show(f"MODEL 1b  P(revisit) + ABSA aspects | clustered SE | N = {int(m1b.nobs)}, "
         f"pseudo-R2 = {m1b.prsquared:.3f} (Model 1: {m1.prsquared:.3f})", t1b)
    summaries.append(str(m1b.summary()))
    forest(t1b[t1b.index.isin(aspect_cols)],
           "Model 1b: aspects mentioned and revisiting (controls not shown)",
           "Odds ratio (log scale; >1 = more likely to be a revisitor)",
           FIGS / "17_model1b_aspects.png")
else:
    print(f"\nModel 1b skipped: {absa_path} not found (run 06_llm_analysis.py --naver first)")

# ── Model 2: keyword tags on ALL reviews (incl. keyword-only) ────────────────
M2_COLS = ["revisit", "has_text"] + VISIT + ["ln_user_reviews"]
X2 = design(df_all, M2_COLS, const=False)
m2 = OrderedModel(df_all["n_tags"], X2, distr="logit").fit(
    method="bfgs", disp=False, maxiter=2000, cov_type="cluster", cov_kwds=clusters(df_all))
t2 = tidy(m2)
save(t2, "model2_keywords.csv")
show(f"MODEL 2  Keyword tags (0-5), all reviews | ordered logit, clustered SE | N = {int(m2.nobs)}, "
     f"mean tags = {df_all.n_tags.mean():.2f}", t2)
summaries.append(str(m2.summary()))
forest(t2, "Model 2: what is associated with more keyword tags?",
       "Odds ratio (log scale; >1 = more tags selected)", FIGS / "16_model2_keywords.png")

# ── Model 2b: same, as a bounded count (binomial with 5 trials) ──────────────
endog = np.column_stack([df_all["n_tags"], 5 - df_all["n_tags"]])
m2b = sm.GLM(endog, sm.add_constant(X2), family=sm.families.Binomial()).fit(
    cov_type="cluster", cov_kwds=clusters(df_all))
t2b = tidy(m2b)
save(t2b, "model2b_keywords_binomial.csv")
show("MODEL 2b (robustness)  Keyword tags as Binomial(5, p) | clustered SE", t2b)
summaries.append(str(m2b.summary()))
both = (np.sign(t2["coef"]) == np.sign(t2b.loc[t2.index, "coef"])) & (t2["p"] < 0.05) & \
       (t2b.loc[t2.index, "p"] < 0.05)
print(f"Significant in both ordered logit and binomial: {', '.join(t2.loc[both, 'label']) or 'none'}")

# ── Model 2t: reviews with text, adding sentiment and length ─────────────────
M2T_COLS = ["revisit"] + VISIT + ["sentiment"] + CONTROLS
m2t = OrderedModel(df_text["n_tags"], design(df_text, M2T_COLS, const=False), distr="logit").fit(
    method="bfgs", disp=False, maxiter=2000, cov_type="cluster", cov_kwds=clusters(df_text))
t2t = tidy(m2t)
save(t2t, "model2t_keywords_text.csv")
show(f"MODEL 2t  Keyword tags, reviews with text (+ sentiment, length) | ordered logit, "
     f"clustered SE | N = {int(m2t.nobs)}", t2t)
summaries.append(str(m2t.summary()))

# ── Model 3: star rating (only reviews that carry stars) ─────────────────────
# Few low ratings (108 of 354 below 5 stars), so: 3 ordered classes and a reduced set of X.
M3_COLS = ["revisit", "has_text", "reserved", "comp_alone", "comp_partner", "comp_friend",
           "comp_child", "purp_travel", "purp_outing", "n_tags", "ln_user_reviews"]
df_rated = df_all.dropna(subset=["rating"]).reset_index(drop=True)
df_rated["rating_cls"] = pd.cut(df_rated["rating"], [0, 4, 4.5, 5], labels=False).astype(int)
df_rated["five_star"] = (df_rated["rating"] == 5).astype(int)
df_rated = varying_places(df_rated, "five_star", "Model 3")


def mcfadden_ordered(res, y):
    counts = np.bincount(y)
    ll0 = np.sum(counts[counts > 0] * np.log(counts[counts > 0] / len(y)))
    return 1 - res.llf / ll0


m3 = OrderedModel(df_rated["rating_cls"], design(df_rated, M3_COLS, const=False), distr="logit").fit(
    method="bfgs", disp=False, maxiter=2000, cov_type="cluster", cov_kwds=clusters(df_rated))
t3 = tidy(m3)
save(t3, "model3_rating.csv")
show(f"MODEL 3  Star rating (<=4 / 4.5 / 5) | ordered logit, clustered SE | N = {int(m3.nobs)} "
     f"({df_rated.user_id.nunique()} reviewers), 5 stars = {df_rated.five_star.mean():.1%}, "
     f"McFadden R2 = {mcfadden_ordered(m3, df_rated['rating_cls'].to_numpy()):.3f}", t3)
summaries.append(str(m3.summary()))
forest(t3, "Model 3: what is associated with higher star ratings?",
       "Odds ratio (log scale; >1 = higher rating)", FIGS / "18_model3_rating.png")

m3b = sm.Logit(df_rated["five_star"], design(df_rated, M3_COLS)).fit(
    disp=False, maxiter=200, cov_type="cluster", cov_kwds=clusters(df_rated))
t3b = tidy(m3b)
save(t3b, "model3b_five_star.csv")
show(f"MODEL 3b (robustness)  P(5 stars) | logistic, clustered SE | N = {int(m3b.nobs)}, "
     f"events (<5 stars) = {int((1 - df_rated.five_star).sum())}, pseudo-R2 = {m3b.prsquared:.3f}", t3b)
summaries.append(str(m3b.summary()))
both3 = (np.sign(t3["coef"]) == np.sign(t3b.loc[t3.index, "coef"])) & (t3["p"] < 0.05) & \
        (t3b.loc[t3.index, "p"] < 0.05)
print(f"Significant in both ordered logit and 5-star logit: {', '.join(t3.loc[both3, 'label']) or 'none'}")

df_rated_text = df_rated[df_rated["has_text"] == 1].reset_index(drop=True)
M3T_COLS = [c for c in M3_COLS if c != "has_text"] + ["sentiment", "ln_length"]
m3t = OrderedModel(df_rated_text["rating_cls"], design(df_rated_text, M3T_COLS, const=False),
                   distr="logit").fit(method="bfgs", disp=False, maxiter=2000, cov_type="cluster",
                                      cov_kwds=clusters(df_rated_text))
t3t = tidy(m3t)
save(t3t, "model3t_rating_text.csv")
show(f"MODEL 3t  Star rating, reviews with text (+ sentiment, length) | ordered logit, clustered SE"
     f" | N = {int(m3t.nobs)}, McFadden R2 = "
     f"{mcfadden_ordered(m3t, df_rated_text['rating_cls'].to_numpy()):.3f}", t3t)
summaries.append(str(m3t.summary()))

# ══════════════════════════════════════════════════════════════════════════════
# EXTENDED MODELS: season, weekend, verification, reviewer profile, tag themes
# ══════════════════════════════════════════════════════════════════════════════
vif_x = VISIT + ["sentiment", "revisit"] + CONTROLS + NEW_COLS + TAG_COLS + ["verif_reservation"]
Xvx = sm.add_constant(df_text[vif_x].astype(float))
vif_ext = pd.DataFrame({"variable": vif_x,
                        "VIF": [variance_inflation_factor(Xvx.values, i + 1) for i in range(len(vif_x))]})
vif_ext.round(2).to_csv(DIR / "vif_extended.csv", index=False, encoding="utf-8-sig")
top = vif_ext.sort_values("VIF", ascending=False).head(3)
print("\nExtended VIF, highest: " + ", ".join(f"{v} {x:.2f}" for v, x in zip(top.variable, top.VIF)))

# ── Model 1x: revisit with the extended set (tag themes replace the tag count) ──
M1X_COLS = VISIT + ["sentiment"] + CONTROLS + NEW_COLS + TAG_COLS
m1x = sm.Logit(df_text["revisit"], design(df_text, M1X_COLS)).fit(
    disp=False, maxiter=300, cov_type="cluster", cov_kwds=clusters(df_text))
t1x = tidy(m1x)
save(t1x, "model1x_revisit_extended.csv")
show(f"MODEL 1x  P(revisit), extended | logistic, clustered SE | N = {int(m1x.nobs)}, "
     f"pseudo-R2 = {m1x.prsquared:.3f} (Model 1: {m1.prsquared:.3f}), AIC = {m1x.aic:.0f} "
     f"(Model 1: {m1.aic:.0f})", t1x)
summaries.append(str(m1x.summary()))

one_x = varying_places(df_text.sample(frac=1, random_state=SEED)
                       .drop_duplicates(["user_id", "place"]).sort_index(), "revisit", "Model 1x-s")
m1xs = sm.Logit(one_x["revisit"], design(one_x, M1X_COLS)).fit(disp=False, maxiter=300, cov_type="HC1")
t1xs = tidy(m1xs)
comp_x = t1x[["label", "ratio", "p"]].join(t1xs[["ratio", "p"]], rsuffix="_one")
comp_x["same_conclusion"] = np.where((comp_x["p"] < 0.05) == (comp_x["p_one"] < 0.05), "yes", "NO")
comp_x.round(4).to_csv(DIR / "model1x_sensitivity.csv", encoding="utf-8-sig")
robust_x = comp_x[(comp_x.p < 0.05) & (comp_x.p_one < 0.05)]
print("Model 1x effects significant in both (all reviews / one per reviewer x place): "
      + ", ".join(f"{r.label} ({r.ratio:.2f})" for _, r in robust_x.iterrows()))
forest(t1x, "Model 1x: revisiting, extended specification",
       "Odds ratio (log scale; >1 = more likely to be a revisitor)", FIGS / "15b_model1x_revisit.png")

# ── Model 2x: keyword tags with the extended set (no tag themes: they define Y) ──
M2X_COLS = M2_COLS + NEW_COLS
m2x = OrderedModel(df_all["n_tags"], design(df_all, M2X_COLS, const=False), distr="logit").fit(
    method="bfgs", disp=False, maxiter=3000, cov_type="cluster", cov_kwds=clusters(df_all))
t2x = tidy(m2x)
save(t2x, "model2x_keywords_extended.csv")
show(f"MODEL 2x  Keyword tags (0-5), extended | ordered logit, clustered SE | N = {int(m2x.nobs)}", t2x)
summaries.append(str(m2x.summary()))

# ── Model 4: reactions (how many people reacted to the review: helpfulness) ──
# Negative binomial for an over-dispersed count with many zeros; review age is
# essential because older reviews had more time to collect reactions.
M4_COLS = (VISIT + ["revisit", "sentiment", "n_tags"] + CONTROLS + NEW_COLS + ["ln_review_age"])
X4 = design(df_text, M4_COLS)


def fit_negbin(y, X, **fit_kw):
    """Negative binomial started from Poisson estimates; from default starting values
    the optimizer can stop at alpha = 0 with a log-likelihood below the null model."""
    start = np.append(sm.GLM(y, X, family=sm.families.Poisson()).fit().params.values, 1.0)
    return sm.NegativeBinomial(y, X).fit(start_params=start, method="newton", maxiter=200,
                                         disp=False, **fit_kw)


m4 = fit_negbin(df_text["reactions"], X4, cov_type="cluster", cov_kwds=clusters(df_text))
t4 = tidy(m4)
t4 = t4[t4.index != "alpha"]
save(t4, "model4_reactions.csv")
alpha = float(m4.params["alpha"])
show(f"MODEL 4  Reactions per review | negative binomial, clustered SE | N = {int(m4.nobs)}, "
     f"with reactions = {(df_text.reactions > 0).mean():.1%}, mean = {df_text.reactions.mean():.2f}, "
     f"alpha = {alpha:.2f}, pseudo-R2 = {m4.prsquared:.3f}", t4, "IRR")
summaries.append(str(m4.summary()))
forest(t4, "Model 4: what is associated with more reactions?",
       "Incidence rate ratio (log scale; >1 = more reactions)", FIGS / "19_model4_reactions.png")

df_text["any_reaction"] = (df_text["reactions"] > 0).astype(int)
m4b = sm.Logit(df_text["any_reaction"], X4).fit(
    disp=False, maxiter=300, cov_type="cluster", cov_kwds=clusters(df_text))
t4b = tidy(m4b)
save(t4b, "model4b_any_reaction.csv")
show(f"MODEL 4b (robustness)  P(at least one reaction) | logistic, clustered SE | "
     f"pseudo-R2 = {m4b.prsquared:.3f}", t4b)
summaries.append(str(m4b.summary()))
both4 = (np.sign(t4["coef"]) == np.sign(t4b.loc[t4.index, "coef"])) & (t4["p"] < 0.05) & \
        (t4b.loc[t4.index, "p"] < 0.05)
print(f"Significant in both negative binomial and logit: {', '.join(t4.loc[both4, 'label']) or 'none'}")

# ── Out-of-sample metrics: 5-fold CV grouped by reviewer (no reviewer in both train and test)
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (roc_auc_score, brier_score_loss, log_loss, accuracy_score,
                             balanced_accuracy_score, precision_score, recall_score, f1_score)

folds = GroupKFold(n_splits=5)


def fit_predict_logit(Xtr, ytr, Xte):
    """statsmodels logit; a fold where a dummy is constant can make it singular,
    in which case a (barely) regularized sklearn logit gives the predictions."""
    try:
        return sm.Logit(ytr, Xtr).fit(disp=False, maxiter=300).predict(Xte)
    except np.linalg.LinAlgError:
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression(C=1e3, max_iter=5000).fit(Xtr.drop(columns="const"), ytr)
        return model.predict_proba(Xte.drop(columns="const"))[:, 1]


def cv_revisit(data, cols, outcome="revisit"):
    X, y = design(data, cols), data[outcome].to_numpy()
    p, base = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in folds.split(X, y, groups=data["user_id"]):
        p[te] = fit_predict_logit(X.iloc[tr], y[tr], X.iloc[te])
        base[te] = y[tr].mean()
    hat = (p >= 0.5).astype(int)
    return {"AUC": roc_auc_score(y, p), "Brier": brier_score_loss(y, p),
            "Brier (base rate)": brier_score_loss(y, base), "Log-loss": log_loss(y, p),
            "Accuracy @0.5": accuracy_score(y, hat),
            "Accuracy (always 'no')": 1 - y.mean(),
            "Balanced accuracy": balanced_accuracy_score(y, hat),
            "Precision (revisit)": precision_score(y, hat, zero_division=0),
            "Recall (revisit)": recall_score(y, hat), "F1 (revisit)": f1_score(y, hat)}


def cv_tags(data, cols):
    X, y = design(data, cols, const=False), data["n_tags"].to_numpy()
    exp_ord, cls_ord, exp_bin = (np.zeros(len(y)) for _ in range(3))
    base_mean, base_mode = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in folds.split(X, y, groups=data["user_id"]):
        res = OrderedModel(y[tr], X.iloc[tr], distr="logit").fit(method="bfgs", disp=False, maxiter=2000)
        probs = np.asarray(res.model.predict(res.params, exog=X.iloc[te]))
        exp_ord[te] = probs @ np.arange(probs.shape[1])
        cls_ord[te] = probs.argmax(axis=1)
        endog = np.column_stack([y[tr], 5 - y[tr]])
        rb = sm.GLM(endog, sm.add_constant(X.iloc[tr]), family=sm.families.Binomial()).fit()
        exp_bin[te] = 5 * rb.predict(sm.add_constant(X.iloc[te], has_constant="add"))
        base_mean[te] = y[tr].mean()
        base_mode[te] = np.bincount(y[tr]).argmax()

    def rmse(a):
        return float(np.sqrt(np.mean((y - a) ** 2)))
    return {"RMSE ordered logit": rmse(exp_ord), "RMSE binomial": rmse(exp_bin),
            "RMSE (predict mean)": rmse(base_mean),
            "MAE ordered logit": float(np.mean(np.abs(y - exp_ord))),
            "MAE (predict mean)": float(np.mean(np.abs(y - base_mean))),
            "Exact accuracy (ordered)": float(np.mean(cls_ord == y)),
            "Exact accuracy (always mode)": float(np.mean(base_mode == y)),
            "Within +-1 accuracy (ordered)": float(np.mean(np.abs(cls_ord - y) <= 1))}


def cv_reactions(data, cols):
    from scipy.stats import spearmanr
    X, y = design(data, cols), data["reactions"].to_numpy()
    mu, base = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in folds.split(X, y, groups=data["user_id"]):
        mu[te] = fit_negbin(y[tr], X.iloc[tr]).predict(X.iloc[te])
        base[te] = y[tr].mean()
    rmse = lambda a: float(np.sqrt(np.mean((y - a) ** 2)))
    return {"Spearman rho (predicted vs observed)": spearmanr(mu, y)[0],
            "AUC any reaction (from predicted mean)": roc_auc_score(y > 0, mu),
            "RMSE negative binomial": rmse(mu), "RMSE (predict mean)": rmse(base),
            "MAE negative binomial": float(np.mean(np.abs(y - mu))),
            "MAE (predict mean)": float(np.mean(np.abs(y - base)))}


def cv_any_reaction(data, cols):
    return {k: v for k, v in cv_revisit(data, cols, outcome="any_reaction").items()
            if k in ("AUC", "Brier", "Brier (base rate)")}


metrics = []
for name, func, data, cols in [
    ("Model 1 revisit", cv_revisit, df_text, M1_COLS),
    ("Model 1x revisit, extended", cv_revisit, df_text, M1X_COLS),
    ("Model 2 keyword tags", cv_tags, df_all, M2_COLS),
    ("Model 2x keyword tags, extended", cv_tags, df_all, M2X_COLS),
    ("Model 4 reactions", cv_reactions, df_text, M4_COLS),
    ("Model 4b any reaction", cv_any_reaction, df_text, M4_COLS),
]:
    for metric, value in func(data, cols).items():
        metrics.append({"model": name, "metric": metric, "value": round(value, 3)})
metrics = pd.DataFrame(metrics)
metrics.to_csv(DIR / "model_metrics_cv.csv", index=False, encoding="utf-8-sig")
print("\n" + "=" * 60)
print("OUT-OF-SAMPLE METRICS (5-fold CV, grouped by reviewer)")
print("=" * 60)
for model, g in metrics.groupby("model", sort=False):
    print(model)
    for _, r in g.iterrows():
        print(f"  {r.metric:<34}{r.value:>8.3f}")

(DIR / "models_summary.txt").write_text("\n\n".join(summaries), encoding="utf-8")
print("\nOR > 1 = higher odds / more tags; < 1 = lower. Significance: *** <.001 ** <.01 * <.05 . <.1")
print(f"Saved tables, models_summary.txt and figures in {DIR}")
