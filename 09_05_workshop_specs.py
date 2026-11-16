"""
09_05_workshop_specs.py
Compare multiple reduced specifications for the workshop paper.
Each spec runs M1 (Revisit, logit) + M2 (Rating, ordered logit) with place FE
and SE clustered by reviewer. Shared predictor set per spec.

Specs:
  full      -- 18 vars (current baseline from 09_04)
  A         -- 7 vars (companion & purpose collapsed into with_group + is_tourist)
  B         -- 9 vars (only variables significant in the baseline run)
  C         -- 7 vars (theory-driven: service / social / reviewer / text)
  minimal   -- 4 vars (waited + is_tourist + ln_followers + sentiment)
  service   -- 2 vars (managerial-only: waited + reserved)

Run modes:
  python 09_05_workshop_specs.py                 # runs ALL specs (default)
  python 09_05_workshop_specs.py --spec=A        # just one spec
  python 09_05_workshop_specs.py --interactive   # menu

Outputs (data/analysis/naver/workshop/specs/):
  specs_comparison.csv                 # one row per spec, headline metrics
  spec_<name>_m1_revisit.csv           # M1 coefficients, per spec
  spec_<name>_m2_rating.csv            # M2 coefficients, per spec
"""

import argparse
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

DIR  = Path("data/analysis/naver")
OUT  = DIR / "workshop" / "specs"
OUT.mkdir(parents=True, exist_ok=True)

# ── Variable building blocks ─────────────────────────────────────────────────
VISIT_ALL = ["has_visit_info", "waited", "reserved",
             "comp_alone", "comp_partner", "comp_friend",
             "comp_child", "comp_family", "comp_colleague",
             "purp_travel", "purp_outing", "purp_daily", "purp_date", "purp_social"]
REVIEWER_ALL = ["ln_user_followers", "ln_user_reviews"]
TEXT_ALL     = ["ln_length", "sentiment"]

LABELS = {
    "has_visit_info": "Visit info provided", "waited": "Waited to enter",
    "reserved": "Reservation",
    "comp_alone": "With: alone", "comp_partner": "With: partner/spouse",
    "comp_friend": "With: friends", "comp_child": "With: children",
    "comp_family": "With: parents/relatives", "comp_colleague": "With: colleagues",
    "with_group": "With: anyone (vs alone/no-info)",
    "purp_travel": "Purpose: travel", "purp_outing": "Purpose: outing",
    "purp_daily": "Purpose: daily life", "purp_date": "Purpose: date",
    "purp_social": "Purpose: socializing",
    "is_tourist": "Visit type: tourist",
    "ln_user_followers": "ln(1 + reviewer's followers)",
    "ln_user_reviews":   "ln(1 + reviewer's reviews)",
    "ln_length":         "ln(text length)",
    "sentiment":         "Sentiment (-1 to 1)",
}


def derive_cols(df):
    """Add derived collapsed indicators used by some specs."""
    df = df.copy()
    df["with_group"] = ((df["comp_partner"] + df["comp_friend"]
                         + df["comp_child"] + df["comp_family"]
                         + df["comp_colleague"]) >= 1).astype(float)
    df["is_tourist"] = df["purp_travel"].astype(float)
    return df


SPECS = {
    "full": {
        "name": "Full baseline (current)",
        "vars": VISIT_ALL + REVIEWER_ALL + TEXT_ALL,
    },
    "A": {
        "name": "Aggressive (collapsed dummies)",
        "vars": ["waited", "reserved", "with_group", "is_tourist",
                 "ln_user_followers", "ln_length", "sentiment"],
    },
    "B": {
        "name": "Moderate (significance-driven)",
        "vars": ["waited", "reserved", "comp_alone", "comp_friend",
                 "purp_travel", "ln_user_followers", "ln_user_reviews",
                 "ln_length", "sentiment"],
    },
    "C": {
        "name": "Theory-driven (+ length)",
        "vars": ["waited", "reserved", "comp_alone", "is_tourist",
                 "ln_user_followers", "ln_length", "sentiment"],
    },
    "minimal": {
        "name": "Minimal (4 vars)",
        "vars": ["waited", "is_tourist", "ln_user_followers", "sentiment"],
    },
    "service": {
        "name": "Service-only (2 vars)",
        "vars": ["waited", "reserved"],
    },
}


# ── Modeling helpers ─────────────────────────────────────────────────────────
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


# ── Run one spec ─────────────────────────────────────────────────────────────
def run_spec(key, spec, df_text):
    cols = spec["vars"]
    print(f"\n[{key}]  {spec['name']}  —  {len(cols)} predictors")

    # ---- Model 1: Revisit ----
    d1 = varying_places(df_text, "revisit")
    m1 = sm.Logit(d1["revisit"], design(d1, cols)).fit(
        disp=False, maxiter=200, cov_type="cluster", cov_kwds=clusters(d1))
    t1 = tidy(m1)
    t1.round(4).to_csv(OUT / f"spec_{key}_m1_revisit.csv",
                       encoding="utf-8-sig")
    sig1 = int((t1["p"] < 0.05).sum())
    print(f"  M1 Revisit: N={int(m1.nobs)}, pseudo-R²={m1.prsquared:.4f}, "
          f"AIC={m1.aic:.1f}, sig vars={sig1}/{len(cols)}")

    # ---- Model 2: Rating (ordered logit) ----
    d2 = df_text.dropna(subset=["rating"]).reset_index(drop=True)
    d2["rating_cls"] = pd.cut(d2["rating"], [0, 4, 4.5, 5],
                              labels=False).astype(int)
    d2["five_star"] = (d2["rating"] == 5).astype(int)
    d2 = varying_places(d2, "five_star")
    m2 = OrderedModel(d2["rating_cls"],
                      design(d2, cols, const=False),
                      distr="logit").fit(method="bfgs", disp=False, maxiter=2000,
                                         cov_type="cluster", cov_kwds=clusters(d2))
    t2 = tidy(m2)
    t2.round(4).to_csv(OUT / f"spec_{key}_m2_rating.csv",
                       encoding="utf-8-sig")
    r2 = mcfadden_ordered(m2, d2["rating_cls"].to_numpy())
    sig2 = int((t2["p"] < 0.05).sum())
    print(f"  M2 Rating:  N={int(m2.nobs)}, McFadden R²={r2:.4f}, "
          f"AIC={m2.aic:.1f}, sig vars={sig2}/{len(cols)}")

    # Headline findings: which vars sig in BOTH, in only one, in neither
    merged = t1[["label", "p", "ratio"]].join(
        t2[["p", "ratio"]], rsuffix="_m2", how="outer")
    merged.columns = ["label", "p_m1", "or_m1", "p_m2", "or_m2"]
    both  = ((merged["p_m1"] < 0.05) & (merged["p_m2"] < 0.05)).sum()
    only1 = ((merged["p_m1"] < 0.05) & (merged["p_m2"] >= 0.05)).sum()
    only2 = ((merged["p_m1"] >= 0.05) & (merged["p_m2"] < 0.05)).sum()
    print(f"  Pattern:    sig in BOTH={both},  only M1={only1},  only M2={only2}")

    return {
        "spec":           key,
        "name":           spec["name"],
        "n_predictors":   len(cols),
        "N_M1":           int(m1.nobs),
        "pseudo_R2_M1":   round(m1.prsquared, 4),
        "AIC_M1":         round(m1.aic, 1),
        "sig_vars_M1":    sig1,
        "N_M2":           int(m2.nobs),
        "McFadden_R2_M2": round(r2, 4),
        "AIC_M2":         round(m2.aic, 1),
        "sig_vars_M2":    sig2,
        "sig_both":       int(both),
        "sig_only_M1":    int(only1),
        "sig_only_M2":    int(only2),
    }


# ── Interactive menu ────────────────────────────────────────────────────────
def menu():
    print("\nAvailable specifications:")
    keys = list(SPECS.keys())
    for i, k in enumerate(keys, 1):
        s = SPECS[k]
        print(f"  {i}) {k:<10}  {s['name']:<40}  ({len(s['vars'])} vars)")
    print(f"  {len(keys)+1}) all        Run all specs")
    choice = input("\nSelect spec (number): ").strip()
    try:
        idx = int(choice) - 1
        if idx == len(keys):
            return SPECS
        return {keys[idx]: SPECS[keys[idx]]}
    except (ValueError, IndexError):
        print(f"Invalid choice, running all specs.")
        return SPECS


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", help=f"one of: {', '.join(SPECS.keys())}")
    parser.add_argument("--interactive", action="store_true",
                        help="pick a spec from a menu")
    args = parser.parse_args()

    df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
    df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
    df_text = derive_cols(df_text)
    print(f"Loaded: {len(df_text)} reviews with text, "
          f"{df_text.user_id.nunique()} reviewers, "
          f"{df_text.place.nunique()} places")

    if args.interactive:
        specs_to_run = menu()
    elif args.spec:
        if args.spec not in SPECS:
            print(f"Unknown spec '{args.spec}'. Valid: {', '.join(SPECS.keys())}")
            sys.exit(1)
        specs_to_run = {args.spec: SPECS[args.spec]}
    else:
        specs_to_run = SPECS  # default: run all

    results = [run_spec(k, s, df_text) for k, s in specs_to_run.items()]

    # ── Summary table ─────────────────────────────────────────────────────
    summary = pd.DataFrame(results)
    summary.to_csv(OUT / "specs_comparison.csv", index=False,
                   encoding="utf-8-sig")

    print("\n" + "=" * 110)
    print("SPECS COMPARISON SUMMARY")
    print("=" * 110)
    cols_show = ["spec", "n_predictors",
                 "pseudo_R2_M1", "AIC_M1", "sig_vars_M1",
                 "McFadden_R2_M2", "AIC_M2", "sig_vars_M2",
                 "sig_both"]
    print(summary[cols_show].to_string(index=False))
    print("=" * 110)
    print(f"\nDetailed coefficients and summary saved under: {OUT}")

    # Simple winner heuristic
    if len(summary) > 1:
        print("\nQuick heuristics (higher is better unless noted):")
        print(f"  Best M1 pseudo-R²:    {summary.loc[summary['pseudo_R2_M1'].idxmax(), 'spec']} "
              f"({summary['pseudo_R2_M1'].max():.4f})")
        print(f"  Best M2 McFadden R²:  {summary.loc[summary['McFadden_R2_M2'].idxmax(), 'spec']} "
              f"({summary['McFadden_R2_M2'].max():.4f})")
        print(f"  Lowest M1 AIC:        {summary.loc[summary['AIC_M1'].idxmin(), 'spec']} "
              f"({summary['AIC_M1'].min():.1f})")
        print(f"  Lowest M2 AIC:        {summary.loc[summary['AIC_M2'].idxmin(), 'spec']} "
              f"({summary['AIC_M2'].min():.1f})")
        print(f"  Most parsimonious:    {summary.loc[summary['n_predictors'].idxmin(), 'spec']} "
              f"({summary['n_predictors'].min()} vars)")


if __name__ == "__main__":
    main()
