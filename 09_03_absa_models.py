"""
09_03_absa_models.py
ABSA x visit-context regressions and ABSA-augmented engagement model.

Two blocks:
  Block A -- Who mentions what?
    For each of 5 aspects (historical_cultural, accessibility, crowding, food,
    visual_photo), a logistic regression:
        mentions_aspect ~ visit context (companion, purpose, waited, reserved)
                        + reviewer controls + place FE
    "mentions" = 1 if the LLM detected the aspect (positive OR negative), 0 otherwise.

  Block B -- Does what people mention predict engagement?
    M4-augmented: reactions ~ x_main (M4 covariates) + 5 aspect-mention dummies
                             + place FE + ln_review_age offset
    Negative binomial, same spec as 09_01 Model 4 but on the 1,173-review ABSA subsample.

Outputs (data/analysis/naver/):
  absa_mention_historical.csv
  absa_mention_accessibility.csv
  absa_mention_crowding.csv
  absa_mention_food.csv
  absa_mention_visual.csv
  absa_reactions_extended.csv
  absa_models_summary.txt

Run (base env):  python 09_03_absa_models.py
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

DIR = Path("data/analysis/naver")
SEED = 42

ASPECTS = ["historical_cultural", "accessibility", "crowding", "food", "visual_photo", "service_experience"]
ASPECT_LABELS = {
    "historical_cultural": "Historical/Cultural",
    "accessibility":       "Accessibility",
    "crowding":            "Crowding",
    "food":                "Food",
    "visual_photo":        "Visual/Photo",
    "service_experience":  "Service/Experience",
}

# --- Load & merge ------------------------------------------------------------
print("Loading data...")
ds = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8")
ab = pd.read_csv(DIR / "naver_absa.csv", encoding="utf-8")

keep_ab = ["place", "text"] + ASPECTS
df = ds.merge(ab[keep_ab], on=["place", "text"], how="inner")
print(f"  merged rows: {len(df)} (ABSA has {len(ab)}, dataset {len(ds)})")

# Mention dummies: 1 if LLM marked +1 or -1 (not 0)
for a in ASPECTS:
    df[f"m_{a}"] = (df[a] != 0).astype(int)

# Place dummies (reference = Gyeongbokgung)
place_dum = pd.get_dummies(df["place"], prefix="place", drop_first=True).astype(int)
df = pd.concat([df, place_dum], axis=1)
place_cols = list(place_dum.columns)

# Visit-context predictors (same as M1 in 09_01)
COMP = ["comp_alone", "comp_partner", "comp_friend", "comp_child",
        "comp_family", "comp_colleague"]
PURP = ["purp_travel", "purp_outing", "purp_daily", "purp_date", "purp_social"]
CTX  = COMP + PURP + ["waited", "reserved"]
CTRL = ["ln_user_reviews", "ln_length"]

# --- Block A: Who mentions what? --------------------------------------------
print("\n== Block A: aspect-mention logistic regressions ==")

def fmt(res, label_map):
    """Standard output row: coef, se, p, OR, CI, sig."""
    rows = []
    for v in res.params.index:
        if v == "const" or v.startswith("place_"):
            continue
        c = res.params[v]
        se = res.bse[v]
        p  = res.pvalues[v]
        or_ = np.exp(c)
        lo, hi = np.exp(c - 1.96*se), np.exp(c + 1.96*se)
        stars = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "." if p < .1 else ""
        rows.append({
            "variable": v, "coef": c, "se": se, "p": p,
            "label": label_map.get(v, v),
            "ratio": or_, "ci_low": lo, "ci_high": hi, "sig": stars,
        })
    return pd.DataFrame(rows).round(4)

LABEL_MAP = {
    "comp_alone": "With: alone", "comp_partner": "With: partner/spouse",
    "comp_friend": "With: friends", "comp_child": "With: children",
    "comp_family": "With: parents/relatives", "comp_colleague": "With: colleagues",
    "purp_travel": "Purpose: travel", "purp_outing": "Purpose: outing",
    "purp_daily":  "Purpose: daily life", "purp_date": "Purpose: date",
    "purp_social": "Purpose: socializing",
    "waited": "Waited to enter", "reserved": "Reservation",
    "ln_user_reviews": "ln(1 + reviewer's reviews)",
    "ln_length": "ln(text length)",
}

summaries = []
for a in ASPECTS:
    y = df[f"m_{a}"]
    X = df[CTX + CTRL + place_cols].copy()
    X = sm.add_constant(X)
    try:
        res = sm.Logit(y, X).fit(disp=0, maxiter=200,
                                   cov_type="cluster",
                                   cov_kwds={"groups": df["user_id"]})
    except Exception as e:
        print(f"  {a}: FAILED ({e})")
        continue
    out = fmt(res, LABEL_MAP)
    out.to_csv(DIR / f"absa_mention_{a.replace('_cultural','').replace('_photo','')}.csv",
               index=False, encoding="utf-8")
    rate = y.mean()
    print(f"  {a}: N={len(y)}, mention rate={rate:.1%}, LLR p={res.llr_pvalue:.3e}, pseudo-R2={res.prsquared:.3f}")
    top = out[out["p"] < .05].sort_values("p").head(5)
    print(top[["variable","label","ratio","p","sig"]].to_string(index=False))
    summaries.append({"aspect": a, "N": len(y), "mention_rate": rate,
                      "pseudo_r2": res.prsquared, "llr_p": res.llr_pvalue})

summary_a = pd.DataFrame(summaries)
summary_a.to_csv(DIR / "absa_mention_summary.csv", index=False, encoding="utf-8")

# --- Block B: Aspect mentions as predictors of reactions --------------------
print("\n== Block B: reactions ~ ... + aspect mentions ==")

# Reduced spec for the ABSA subsample (N=1,173): drop sparse covariates to allow NB to converge.
M4_COVARS = ["has_visit_info", "waited", "revisit", "sentiment", "n_tags",
             "ln_length", "ln_user_reviews", "ln_user_followers"]
ASPECT_DUMS = [f"m_{a}" for a in ASPECTS]

sub = df.dropna(subset=M4_COVARS + ["reactions", "ln_review_age"]).copy()
sub = sub[sub["reactions"] >= 0]

print(f"  subsample for Model 4+ABSA: N={len(sub)}")

X = sub[M4_COVARS + ASPECT_DUMS + place_cols].copy().astype(float)
X = sm.add_constant(X)
y = sub["reactions"].astype(int)
offset = sub["ln_review_age"].astype(float)

try:
    res_nb = sm.NegativeBinomial(y, X, offset=offset).fit(
        disp=0, maxiter=300, method="bfgs",
        cov_type="cluster", cov_kwds={"groups": sub["user_id"]},
    )
except Exception as e:
    print(f"  NB failed, trying Poisson. ({e})")
    res_nb = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit(
        cov_type="cluster", cov_kwds={"groups": sub["user_id"]},
    )

MAP_ASPECT = {f"m_{a}": f"Mentions: {ASPECT_LABELS[a]}" for a in ASPECTS}
LABEL_M4 = {**LABEL_MAP, **MAP_ASPECT,
            "has_visit_info": "Visit info provided",
            "revisit": "Revisitor (2+ visits)",
            "sentiment": "Sentiment (-1 to 1)",
            "n_tags": "Keyword tags (0-5)",
            "ln_user_followers": "ln(1 + reviewer's followers)",
            "season_summer": "Visit: summer",
            "season_autumn": "Visit: autumn",
            "season_winter": "Visit: winter",
            "visit_weekend": "Visit: weekend",
            "verif_receipt": "Verified by receipt"}

out_m4 = fmt(res_nb, LABEL_M4)
out_m4.to_csv(DIR / "absa_reactions_extended.csv", index=False, encoding="utf-8")

print("  Aspect-mention effects on reactions (significant only):")
sig = out_m4[(out_m4["variable"].isin(ASPECT_DUMS)) & (out_m4["p"] < .1)]
print(sig[["label", "ratio", "ci_low", "ci_high", "p", "sig"]].to_string(index=False))

# --- Narrative summary -------------------------------------------------------
with open(DIR / "absa_models_summary.txt", "w", encoding="utf-8") as f:
    f.write("ABSA regressions summary (09_03_absa_models.py)\n")
    f.write("=" * 60 + "\n\n")
    f.write("Block A: Who mentions each aspect?\n")
    for _, r in summary_a.iterrows():
        f.write(f"  {r['aspect']:22s}  N={int(r['N'])}  rate={r['mention_rate']:.1%}  "
                f"pseudo-R2={r['pseudo_r2']:.3f}  LLR p={r['llr_p']:.3e}\n")
    f.write(f"\nBlock B: reactions ~ ... + 5 aspect mentions\n")
    f.write(f"  Subsample N={len(sub)}  (ABSA merged with M4 covariates)\n")
    f.write("  Significant aspect-mention effects:\n")
    for _, r in sig.iterrows():
        f.write(f"    {r['label']:30s}  IRR={r['ratio']:.3f}  [{r['ci_low']:.3f}, {r['ci_high']:.3f}]  p={r['p']:.4f} {r['sig']}\n")

print(f"\nDone. Outputs in {DIR}")
