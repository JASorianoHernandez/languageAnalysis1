"""
09_06_workshop_exploration.py
Comprehensive exploratory sweep: runs ~30 reduced specifications of M1 (Revisit,
binary logit) and M2 (Rating, ordered logit), then ranks them by fit so you can
see which direction to go to push pseudo-R2 above 0.20 without sacrificing
parsimony.

Families of specs (each spec is run against BOTH M1 and M2):

  BASE               full, A, B, C, minimal, service
  MINIMAL+1          minimal plus one additional predictor
  MINIMAL+2          minimal plus two additional predictors
  EXTENDED           minimal plus "new" vars (weekend, season, verification, age)
  INTERACTION        minimal plus one interaction term
  NON-LINEAR         minimal plus one squared term

All runs share:
  - Place fixed effects (28 dummies, Gyeongbokgung = reference)
  - SE clustered by user_id (reviewer)
  - M1 uses N = 11,165 (reviews with text); M2 uses N = 4,044 (text + rating)

Outputs (data/analysis/naver/workshop/exploration/):
  exploration_summary.csv       # all specs, headline metrics, sortable
  spec_<key>_m1_revisit.csv     # M1 coefs per spec
  spec_<key>_m2_rating.csv      # M2 coefs per spec
  top_by_fit.txt                # printable top-10 report

Run:  python 09_06_workshop_exploration.py
      python 09_06_workshop_exploration.py --spec=minimal+reviews   (single)
"""

import argparse
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.miscmodels.ordinal_model import OrderedModel

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)

MINIMAL = ["waited", "is_tourist", "ln_user_followers", "sentiment"]

LABELS = {
    "has_visit_info": "Visit info", "waited": "Waited", "reserved": "Reservation",
    "comp_alone": "Alone", "comp_partner": "Partner", "comp_friend": "Friends",
    "comp_child": "Children", "comp_family": "Family", "comp_colleague": "Colleagues",
    "with_group": "With anyone (vs alone)",
    "purp_travel": "Travel", "purp_outing": "Outing", "purp_daily": "Daily",
    "purp_date": "Date", "purp_social": "Social",
    "is_tourist": "Tourist", "ln_user_followers": "ln(followers)",
    "ln_user_reviews": "ln(reviews)", "ln_length": "ln(length)",
    "sentiment": "Sentiment",
    "visit_weekend": "Weekend",
    "season_summer": "Summer", "season_autumn": "Autumn", "season_winter": "Winter",
    "verif_receipt": "Verified receipt",
    "ln_review_age": "ln(review age)",
    "waited_x_tourist": "Waited x Tourist",
    "waited_x_followers": "Waited x ln(followers)",
    "waited_x_sentiment": "Waited x Sentiment",
    "tourist_x_sentiment": "Tourist x Sentiment",
    "sentiment_x_length": "Sentiment x ln(length)",
    "sentiment_sq": "Sentiment^2",
    "followers_sq": "ln(followers)^2",
}


def derive(df):
    """Pre-compute all derived columns needed across specs."""
    df = df.copy()
    # Collapsed indicators
    df["with_group"] = ((df["comp_partner"] + df["comp_friend"]
                         + df["comp_child"] + df["comp_family"]
                         + df["comp_colleague"]) >= 1).astype(float)
    df["is_tourist"] = df["purp_travel"].astype(float)
    # Interactions
    df["waited_x_tourist"]    = df["waited"] * df["is_tourist"]
    df["waited_x_followers"]  = df["waited"] * df["ln_user_followers"]
    df["waited_x_sentiment"]  = df["waited"] * df["sentiment"]
    df["tourist_x_sentiment"] = df["is_tourist"] * df["sentiment"]
    df["sentiment_x_length"]  = df["sentiment"] * df["ln_length"]
    # Non-linear
    df["sentiment_sq"] = df["sentiment"] ** 2
    df["followers_sq"] = df["ln_user_followers"] ** 2
    return df


# ─── SPECS registry ─────────────────────────────────────────────────────────
BASE_SPECS = {
    "full": {
        "family": "base",
        "name": "Full baseline (18)",
        "vars": ["has_visit_info", "waited", "reserved",
                 "comp_alone", "comp_partner", "comp_friend",
                 "comp_child", "comp_family", "comp_colleague",
                 "purp_travel", "purp_outing", "purp_daily",
                 "purp_date", "purp_social",
                 "ln_user_followers", "ln_user_reviews",
                 "ln_length", "sentiment"],
    },
    "A_aggressive": {
        "family": "base",
        "name": "A: collapsed dummies (7)",
        "vars": ["waited", "reserved", "with_group", "is_tourist",
                 "ln_user_followers", "ln_length", "sentiment"],
    },
    "B_moderate": {
        "family": "base",
        "name": "B: sig-only (9)",
        "vars": ["waited", "reserved", "comp_alone", "comp_friend",
                 "purp_travel", "ln_user_followers", "ln_user_reviews",
                 "ln_length", "sentiment"],
    },
    "C_theory": {
        "family": "base",
        "name": "C: theory-driven (7)",
        "vars": ["waited", "reserved", "comp_alone", "is_tourist",
                 "ln_user_followers", "ln_length", "sentiment"],
    },
    "minimal": {
        "family": "base",
        "name": "Minimal (4)",
        "vars": list(MINIMAL),
    },
    "service": {
        "family": "base",
        "name": "Service only (2)",
        "vars": ["waited", "reserved"],
    },
}


def plus_specs(extras, family, prefix="min+"):
    """Build minimal + each extra variable individually."""
    out = {}
    for v in extras:
        key = f"{prefix}{v}"
        out[key] = {
            "family": family,
            "name":   f"minimal + {LABELS.get(v, v)}",
            "vars":   MINIMAL + [v],
        }
    return out


MIN_PLUS_1 = plus_specs(
    ["ln_user_reviews", "comp_alone", "comp_friend", "ln_length",
     "reserved", "has_visit_info", "visit_weekend", "verif_receipt",
     "ln_review_age", "season_summer", "season_autumn", "season_winter"],
    family="min+1",
)

MIN_PLUS_2 = {
    "min+rev+alone":    {"family": "min+2",
                         "name": "minimal + ln(reviews) + alone",
                         "vars": MINIMAL + ["ln_user_reviews", "comp_alone"]},
    "min+rev+length":   {"family": "min+2",
                         "name": "minimal + ln(reviews) + ln(length)",
                         "vars": MINIMAL + ["ln_user_reviews", "ln_length"]},
    "min+rev+friend":   {"family": "min+2",
                         "name": "minimal + ln(reviews) + friend",
                         "vars": MINIMAL + ["ln_user_reviews", "comp_friend"]},
    "min+alone+friend": {"family": "min+2",
                         "name": "minimal + alone + friend",
                         "vars": MINIMAL + ["comp_alone", "comp_friend"]},
    "min+length+reserved": {"family": "min+2",
                            "name": "minimal + ln(length) + reserved",
                            "vars": MINIMAL + ["ln_length", "reserved"]},
    "min+weekend+verif":   {"family": "min+2",
                            "name": "minimal + weekend + verified",
                            "vars": MINIMAL + ["visit_weekend", "verif_receipt"]},
    "min+age+weekend":     {"family": "min+2",
                            "name": "minimal + ln(age) + weekend",
                            "vars": MINIMAL + ["ln_review_age", "visit_weekend"]},
}

MIN_EXTENDED = {
    "min+all_seasons": {
        "family": "extended",
        "name": "minimal + 3 season dummies",
        "vars": MINIMAL + ["season_summer", "season_autumn", "season_winter"],
    },
    "min+new_all": {
        "family": "extended",
        "name": "minimal + weekend + season + verified + age",
        "vars": MINIMAL + ["visit_weekend", "season_summer", "season_autumn",
                           "season_winter", "verif_receipt", "ln_review_age"],
    },
    "min+rev+alone+length": {
        "family": "extended",
        "name": "minimal + ln(reviews) + alone + ln(length)  [=~C]",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone", "ln_length"],
    },
    "min+all_sig": {
        "family": "extended",
        "name": "minimal + 4 sig vars from full (approx = full-core)",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone",
                           "comp_friend", "ln_length"],
    },
}

INTERACTIONS = {
    "min+int_waited_tourist":   {"family": "interaction",
                                 "name": "minimal + waited x tourist",
                                 "vars": MINIMAL + ["waited_x_tourist"]},
    "min+int_waited_followers": {"family": "interaction",
                                 "name": "minimal + waited x ln(followers)",
                                 "vars": MINIMAL + ["waited_x_followers"]},
    "min+int_waited_sentiment": {"family": "interaction",
                                 "name": "minimal + waited x sentiment",
                                 "vars": MINIMAL + ["waited_x_sentiment"]},
    "min+int_tourist_sentiment":{"family": "interaction",
                                 "name": "minimal + tourist x sentiment",
                                 "vars": MINIMAL + ["tourist_x_sentiment"]},
    "min+int_sentiment_length": {"family": "interaction",
                                 "name": "minimal + sentiment x ln(length)",
                                 "vars": MINIMAL + ["sentiment_x_length",
                                                    "ln_length"]},
}

NONLINEAR = {
    "min+sent_sq":    {"family": "nonlinear",
                       "name": "minimal + sentiment^2",
                       "vars": MINIMAL + ["sentiment_sq"]},
    "min+foll_sq":    {"family": "nonlinear",
                       "name": "minimal + ln(followers)^2",
                       "vars": MINIMAL + ["followers_sq"]},
    "min+both_sq":    {"family": "nonlinear",
                       "name": "minimal + sentiment^2 + followers^2",
                       "vars": MINIMAL + ["sentiment_sq", "followers_sq"]},
}

# ─── PROPOSED combos (based on exploration round 1 findings) ────────────────
# Top single-variable boosters:
#   M1: ln_user_reviews (+0.014), ln_review_age (+0.010),
#       comp_alone (+0.010), verif_receipt (+0.010)
#   M2: season_autumn (+0.013), ln_review_age (+0.011)
# These combos probe what happens when we mix the top boosters.
PROPOSED = {
    # ── 6-var pairs (new ones not covered in min+2) ─────────────────────
    "min+rev+age": {
        "family": "proposed",
        "name": "min + ln(reviews) + ln(age)  [M1 boost + M2 boost]",
        "vars": MINIMAL + ["ln_user_reviews", "ln_review_age"],
    },
    "min+alone+age": {
        "family": "proposed",
        "name": "min + alone + ln(age)",
        "vars": MINIMAL + ["comp_alone", "ln_review_age"],
    },
    "min+rev+autumn": {
        "family": "proposed",
        "name": "min + ln(reviews) + autumn",
        "vars": MINIMAL + ["ln_user_reviews", "season_autumn"],
    },
    "min+rev+verif": {
        "family": "proposed",
        "name": "min + ln(reviews) + verif_receipt",
        "vars": MINIMAL + ["ln_user_reviews", "verif_receipt"],
    },

    # ── 7-var triplets (the FLAGSHIP candidates) ────────────────────────
    "min+rev+alone+age": {
        "family": "proposed",
        "name": "⭐ min + ln(reviews) + alone + ln(age)",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone", "ln_review_age"],
    },
    "min+rev+alone+autumn": {
        "family": "proposed",
        "name": "min + ln(reviews) + alone + autumn",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone", "season_autumn"],
    },
    "min+rev+alone+verif": {
        "family": "proposed",
        "name": "min + ln(reviews) + alone + verif_receipt",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone", "verif_receipt"],
    },
    "min+rev+age+autumn": {
        "family": "proposed",
        "name": "min + ln(reviews) + ln(age) + autumn",
        "vars": MINIMAL + ["ln_user_reviews", "ln_review_age", "season_autumn"],
    },

    # ── 8-var quadruplets (push both R² higher) ─────────────────────────
    "min+rev+alone+age+length": {
        "family": "proposed",
        "name": "min + ln(reviews) + alone + ln(age) + ln(length)",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone",
                           "ln_review_age", "ln_length"],
    },
    "min+rev+alone+age+autumn": {
        "family": "proposed",
        "name": "min + ln(reviews) + alone + ln(age) + autumn",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone",
                           "ln_review_age", "season_autumn"],
    },
    "min+rev+alone+age+verif": {
        "family": "proposed",
        "name": "min + ln(reviews) + alone + ln(age) + verif",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone",
                           "ln_review_age", "verif_receipt"],
    },

    # ── Theory-driven alternatives ──────────────────────────────────────
    "theory_tight": {
        "family": "proposed",
        "name": "Theory-tight: service+social+reviewer+text+time (6)",
        "vars": ["waited", "is_tourist", "ln_user_followers",
                 "ln_user_reviews", "sentiment", "ln_review_age"],
    },
    "social": {
        "family": "proposed",
        "name": "Social-focused: waited + alone + friend + followers + sent (5)",
        "vars": ["waited", "comp_alone", "comp_friend",
                 "ln_user_followers", "sentiment"],
    },

    # ── Interaction added to a strong base ──────────────────────────────
    "min+rev+alone+int_wait_tour": {
        "family": "proposed",
        "name": "min+rev+alone + waited x tourist interaction (7)",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone",
                           "waited_x_tourist"],
    },

    # ── 9-var "all seasons + rev + alone" ───────────────────────────────
    "min+rev+alone+all_seasons": {
        "family": "proposed",
        "name": "min + rev + alone + 3 season dummies (9)",
        "vars": MINIMAL + ["ln_user_reviews", "comp_alone",
                           "season_summer", "season_autumn", "season_winter"],
    },
}

SPECS = {**BASE_SPECS, **MIN_PLUS_1, **MIN_PLUS_2,
         **MIN_EXTENDED, **INTERACTIONS, **NONLINEAR, **PROPOSED}


# ─── Modeling helpers ───────────────────────────────────────────────────────
def design(data, cols, const=True):
    places = pd.get_dummies(data["place"], prefix="place",
                            drop_first=True, dtype=float)
    X = pd.concat([data[cols].astype(float), places], axis=1)
    return sm.add_constant(X) if const else X


def clusters(data):
    return {"groups": pd.factorize(data["user_id"])[0]}


def varying_places(data, y):
    keep = data.groupby("place")[y].transform(lambda s: s.nunique() > 1)
    return data[keep].reset_index(drop=True)


def mcfadden_ordered(res, y):
    counts = np.bincount(y)
    ll0 = np.sum(counts[counts > 0] * np.log(counts[counts > 0] / len(y)))
    return 1 - res.llf / ll0


def tidy(res):
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "p": res.pvalues})
    out = out[~out.index.str.startswith(("place_", "const"))
              & ~out.index.str.contains("/")]
    out["label"]   = [LABELS.get(idx, idx) for idx in out.index]
    out["ratio"]   = np.exp(out["coef"])
    out["ci_low"]  = np.exp(out["coef"] - 1.96 * out["se"])
    out["ci_high"] = np.exp(out["coef"] + 1.96 * out["se"])
    out["sig"] = pd.cut(out["p"], [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                        labels=["***", "**", "*", ".", ""])
    return out


# ─── Run one spec ──────────────────────────────────────────────────────────
def run_spec(key, spec, df_text):
    cols = spec["vars"]
    t_start = perf_counter()

    # M1 Revisit (binary logit)
    d1 = varying_places(df_text, "revisit")
    try:
        m1 = sm.Logit(d1["revisit"], design(d1, cols)).fit(
            disp=False, maxiter=300,
            cov_type="cluster", cov_kwds=clusters(d1))
        t1 = tidy(m1)
        t1.round(4).to_csv(OUT / f"spec_{key}_m1_revisit.csv",
                           encoding="utf-8-sig")
        m1_pr2 = m1.prsquared
        m1_aic = m1.aic
        m1_n   = int(m1.nobs)
        m1_sig = int((t1["p"] < 0.05).sum())
        m1_llf = m1.llf
    except Exception as e:
        print(f"  [{key}] M1 failed: {e}")
        m1_pr2 = m1_aic = m1_n = m1_sig = m1_llf = np.nan
        t1 = pd.DataFrame()

    # M2 Rating (ordered logit)
    d2 = df_text.dropna(subset=["rating"]).reset_index(drop=True)
    d2["rating_cls"] = pd.cut(d2["rating"], [0, 4, 4.5, 5],
                              labels=False).astype(int)
    d2["five_star"]  = (d2["rating"] == 5).astype(int)
    d2 = varying_places(d2, "five_star")
    try:
        m2 = OrderedModel(d2["rating_cls"],
                          design(d2, cols, const=False),
                          distr="logit").fit(method="bfgs", disp=False,
                                             maxiter=2000, cov_type="cluster",
                                             cov_kwds=clusters(d2))
        t2 = tidy(m2)
        t2.round(4).to_csv(OUT / f"spec_{key}_m2_rating.csv",
                           encoding="utf-8-sig")
        m2_r2  = mcfadden_ordered(m2, d2["rating_cls"].to_numpy())
        m2_aic = m2.aic
        m2_n   = int(m2.nobs)
        m2_sig = int((t2["p"] < 0.05).sum())
        m2_llf = m2.llf
    except Exception as e:
        print(f"  [{key}] M2 failed: {e}")
        m2_r2 = m2_aic = m2_n = m2_sig = m2_llf = np.nan
        t2 = pd.DataFrame()

    # Overlap: how many predictors sig in BOTH?
    if not t1.empty and not t2.empty:
        shared_idx = t1.index.intersection(t2.index)
        both = int(((t1.loc[shared_idx, "p"] < 0.05)
                    & (t2.loc[shared_idx, "p"] < 0.05)).sum())
    else:
        both = np.nan

    elapsed = perf_counter() - t_start
    print(f"[{key:>26s}] n_vars={len(cols):>2}  "
          f"M1 pR²={m1_pr2:.4f} AIC={m1_aic:>7.1f} sig={m1_sig:>2}/{len(cols)}  "
          f"M2 pR²={m2_r2:.4f} AIC={m2_aic:>7.1f} sig={m2_sig:>2}/{len(cols)}  "
          f"both={both}  ({elapsed:.1f}s)")

    return {
        "key":            key,
        "family":         spec["family"],
        "name":           spec["name"],
        "n_predictors":   len(cols),
        "N_M1":           m1_n,
        "pseudo_R2_M1":   round(m1_pr2, 4) if not np.isnan(m1_pr2) else np.nan,
        "AIC_M1":         round(m1_aic, 1) if not np.isnan(m1_aic) else np.nan,
        "LLF_M1":         round(m1_llf, 2) if not np.isnan(m1_llf) else np.nan,
        "sig_vars_M1":    m1_sig,
        "N_M2":           m2_n,
        "McFadden_R2_M2": round(m2_r2, 4) if not np.isnan(m2_r2) else np.nan,
        "AIC_M2":         round(m2_aic, 1) if not np.isnan(m2_aic) else np.nan,
        "LLF_M2":         round(m2_llf, 2) if not np.isnan(m2_llf) else np.nan,
        "sig_vars_M2":    m2_sig,
        "sig_both":       both,
    }


# ─── Report helpers ────────────────────────────────────────────────────────
def print_top(summary, metric, k=10, ascending=False, extra_cols=None):
    extra = extra_cols or []
    cols = ["key", "family", "n_predictors",
            "pseudo_R2_M1", "McFadden_R2_M2", "AIC_M1", "AIC_M2",
            "sig_vars_M1", "sig_vars_M2", "sig_both"] + extra
    cols = [c for c in cols if c in summary.columns]
    top = summary.sort_values(metric, ascending=ascending).head(k)
    print(top[cols].to_string(index=False))


# ─── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", help="run only one spec (key)")
    parser.add_argument("--family", help="run only one family: "
                        "base|min+1|min+2|extended|interaction|nonlinear")
    args = parser.parse_args()

    df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
    df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
    df_text = derive(df_text)
    print(f"Loaded: {len(df_text)} reviews with text, "
          f"{df_text.user_id.nunique()} reviewers, "
          f"{df_text.place.nunique()} places\n")

    if args.spec:
        if args.spec not in SPECS:
            print(f"Unknown spec '{args.spec}'. Available: {list(SPECS.keys())}")
            sys.exit(1)
        specs_to_run = {args.spec: SPECS[args.spec]}
    elif args.family:
        specs_to_run = {k: v for k, v in SPECS.items() if v["family"] == args.family}
    else:
        specs_to_run = SPECS

    print(f"Running {len(specs_to_run)} specifications ...\n")
    results = [run_spec(k, s, df_text) for k, s in specs_to_run.items()]
    summary = pd.DataFrame(results)
    summary.to_csv(OUT / "exploration_summary.csv", index=False,
                   encoding="utf-8-sig")

    print("\n" + "=" * 120)
    print(f"SUMMARY — {len(summary)} specs")
    print("=" * 120)

    print("\n>>> TOP 10 by M1 pseudo-R² (Revisit) <<<")
    print_top(summary, "pseudo_R2_M1", k=10)

    print("\n>>> TOP 10 by M2 McFadden R² (Rating) <<<")
    print_top(summary, "McFadden_R2_M2", k=10)

    print("\n>>> TOP 10 by LOWEST M1 AIC <<<")
    print_top(summary, "AIC_M1", k=10, ascending=True)

    print("\n>>> TOP 10 by LOWEST M2 AIC <<<")
    print_top(summary, "AIC_M2", k=10, ascending=True)

    # Efficiency: R² per predictor
    summary["eff_M1"] = summary["pseudo_R2_M1"] / summary["n_predictors"]
    summary["eff_M2"] = summary["McFadden_R2_M2"] / summary["n_predictors"]
    print("\n>>> TOP 10 by R²-per-variable efficiency (M1) <<<")
    print_top(summary, "eff_M1", k=10, extra_cols=["eff_M1"])

    # Specs that cross the 0.20 threshold on M1
    above = summary[summary["pseudo_R2_M1"] >= 0.20].sort_values(
        "n_predictors").head(10)
    print(f"\n>>> SPECS WITH M1 pseudo-R² >= 0.20 (smallest first) <<<")
    if above.empty:
        print("  (none)")
    else:
        print(above[["key", "n_predictors", "pseudo_R2_M1",
                     "McFadden_R2_M2", "AIC_M1", "sig_vars_M1"]].to_string(index=False))

    # Save a text report
    report_lines = ["EXPLORATION REPORT — all specs ranked",
                    "=" * 72, ""]
    for col in ["pseudo_R2_M1", "McFadden_R2_M2"]:
        report_lines.append(f"Top 10 by {col}:")
        report_lines.append(summary.sort_values(col, ascending=False)
                            .head(10)[["key", "n_predictors", col]]
                            .to_string(index=False))
        report_lines.append("")
    (OUT / "top_by_fit.txt").write_text("\n".join(report_lines),
                                        encoding="utf-8")

    # Resave summary with efficiency columns
    summary.to_csv(OUT / "exploration_summary.csv", index=False,
                   encoding="utf-8-sig")
    print(f"\nSaved: {OUT / 'exploration_summary.csv'}")
    print(f"       {OUT / 'top_by_fit.txt'}")
    print(f"       and {len(summary)} per-spec coefficient files")


if __name__ == "__main__":
    main()
