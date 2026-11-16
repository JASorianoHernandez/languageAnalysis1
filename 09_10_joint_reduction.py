"""
09_10_joint_reduction.py
Joint M1 + M2 variable-reduction exploration.

Phase 1  M1 efficiency frontier: best M1 (binary logit, Revisit) at
         each predictor count (1..7).  All 2^7 - 1 = 127 subsets tried.

Phase 2  Paired specs: for each (|M1|, |M2|) combination of sizes 4..7,
         we take the top M1 spec AND the top M2 spec of that size
         (from 09_09's M2 sweep + this script's M1 sweep).

Phase 3  Review-age sensitivity: a focused rerun of the recommended
         winning spec on reviews from the last X years only, to see
         whether the ln_review_age effect survives.

Outputs: data/analysis/naver/workshop/joint_reduction/
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd
import statsmodels.api as sm

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop" / "joint_reduction"
OUT.mkdir(parents=True, exist_ok=True)

ALL7 = ["waited", "is_tourist", "ln_user_followers", "sentiment",
        "ln_user_reviews", "comp_alone", "ln_review_age"]

LABELS = {
    "waited": "Waited", "is_tourist": "Tourist",
    "ln_user_followers": "ln(followers)",
    "ln_user_reviews": "ln(reviews)",
    "sentiment": "Sentiment", "comp_alone": "Alone",
    "ln_review_age": "ln(review_age)",
}


def derive(df):
    df = df.copy()
    df["is_tourist"] = df["purp_travel"].astype(float)
    return df


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


def fit_m1(data, cols):
    d = varying_places(data, "revisit")
    try:
        return sm.Logit(d["revisit"], design(d, cols)).fit(
            disp=False, maxiter=300,
            cov_type="cluster", cov_kwds=clusters(d))
    except Exception:
        return None


def fit_m2(data, cols):
    d = data.dropna(subset=["rating"]).reset_index(drop=True)
    d["five_star"] = (d["rating"] == 5).astype(int)
    d = varying_places(d, "five_star")
    try:
        return sm.Logit(d["five_star"], design(d, cols)).fit(
            disp=False, maxiter=300,
            cov_type="cluster", cov_kwds=clusters(d))
    except Exception:
        return None


def sig_count(res, cols):
    return int(sum((res.pvalues.get(c, 1) < 0.05) for c in cols))


# ───────────────────────────────────────────────────────────────────────────
# PHASE 1: M1 efficiency frontier (all 2^7 = 128 subsets of ALL7)
# ───────────────────────────────────────────────────────────────────────────
def phase1_m1_frontier(df_text):
    print("\n" + "=" * 90)
    print("PHASE 1: M1 (Revisit) efficiency frontier - all 127 non-empty subsets")
    print("=" * 90)

    rows = []
    for k in range(1, 8):
        for combo in combinations(ALL7, k):
            cols = list(combo)
            res = fit_m1(df_text, cols)
            if res is None:
                continue
            rows.append({
                "size":   k,
                "key":    "+".join(cols),
                "cols":   cols,
                "N":      int(res.nobs),
                "R2":     round(res.prsquared, 4),
                "AIC":    round(res.aic, 1),
                "BIC":    round(res.bic, 1),
                "n_sig":  sig_count(res, cols),
            })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "m1_all_subsets.csv", index=False, encoding="utf-8-sig")

    print(f"  Tested {len(df)} M1 specifications.")
    front = df.sort_values("R2", ascending=False).drop_duplicates("size") \
              .sort_values("size")
    print("\n  M1 FRONTIER (best R² at each size):")
    print(front[["size", "R2", "AIC", "n_sig", "key"]].to_string(index=False))

    front.to_csv(OUT / "m1_frontier.csv", index=False, encoding="utf-8-sig")
    return df, front


# ───────────────────────────────────────────────────────────────────────────
# PHASE 2: Pair M1 and M2 frontiers (joint comparison)
# ───────────────────────────────────────────────────────────────────────────
def phase2_pair(df_text, m1_front):
    print("\n" + "=" * 90)
    print("PHASE 2: Pair the M1 frontier with the M2 frontier")
    print("=" * 90)

    # Load M2 frontier from 09_09's output; fall back to re-computing here.
    m2_path = DIR / "workshop" / "m2_reduction" / "m2_reduction_summary.csv"
    if m2_path.exists():
        m2_df = pd.read_csv(m2_path)
        m2_front = (m2_df.sort_values("R2", ascending=False)
                        .drop_duplicates("n_vars")
                        .sort_values("n_vars"))
        m2_cols_lookup = {}
        for _, r in m2_front.iterrows():
            m2_cols_lookup[int(r["n_vars"])] = [v.strip()
                                                for v in r["vars"].split(";")]
    else:
        print("  m2_reduction summary not found; recomputing M2 frontier here.")
        m2_rows = []
        for k in range(1, 8):
            for combo in combinations(ALL7, k):
                cols = list(combo)
                res = fit_m2(df_text, cols)
                if res is None:
                    continue
                m2_rows.append({
                    "size": k, "cols": cols,
                    "R2": round(res.prsquared, 4),
                    "AIC": round(res.aic, 1),
                })
        m2_df = pd.DataFrame(m2_rows)
        m2_front = m2_df.sort_values("R2", ascending=False) \
                        .drop_duplicates("size").sort_values("size")
        m2_cols_lookup = {int(r["size"]): r["cols"]
                          for _, r in m2_front.iterrows()}

    # Compose paired specs for sizes 3..7 for both models
    rows = []
    for m1_size in range(3, 8):
        m1_row = m1_front[m1_front["size"] == m1_size].iloc[0]
        m1_cols = m1_row["cols"]
        m1 = fit_m1(df_text, m1_cols)
        for m2_size in range(3, 8):
            if m2_size not in m2_cols_lookup:
                continue
            m2_cols = m2_cols_lookup[m2_size]
            m2 = fit_m2(df_text, m2_cols)
            if m2 is None:
                continue
            rows.append({
                "pair":      f"M1_{m1_size}+M2_{m2_size}",
                "m1_size":   m1_size,
                "m2_size":   m2_size,
                "m1_vars":   "|".join(m1_cols),
                "m2_vars":   "|".join(m2_cols),
                "M1_R2":     round(m1.prsquared, 4),
                "M1_AIC":    round(m1.aic, 1),
                "M1_sig":    sig_count(m1, m1_cols),
                "M2_R2":     round(m2.prsquared, 4),
                "M2_AIC":    round(m2.aic, 1),
                "M2_sig":    sig_count(m2, m2_cols),
                "total_vars":m1_size + m2_size,
            })

    pairs = pd.DataFrame(rows)
    pairs.to_csv(OUT / "paired_specs.csv", index=False, encoding="utf-8-sig")

    print("  PAIRED SPECS (M1 size x M2 size) - M1 R² / M2 R²")
    pivot = pairs.pivot(index="m1_size", columns="m2_size",
                        values="M2_R2")
    print("  M2 R² (rows = M1 size, cols = M2 size):")
    print(pivot.round(4).to_string())

    pivot_aic = pairs.pivot(index="m1_size", columns="m2_size", values="M2_AIC")
    print("\n  M2 AIC:")
    print(pivot_aic.round(1).to_string())

    print("\n  Full paired table (sorted by total vars):")
    print(pairs.sort_values(["total_vars", "m1_size"])[
        ["pair", "m1_size", "m2_size", "M1_R2", "M2_R2", "M1_AIC", "M2_AIC",
         "M1_sig", "M2_sig"]].to_string(index=False))

    return pairs


# ───────────────────────────────────────────────────────────────────────────
# PHASE 3: ln_review_age sensitivity — drop old reviews, re-fit, see effect
# ───────────────────────────────────────────────────────────────────────────
def phase3_age_sensitivity(df_text, winner_m1, winner_m2):
    print("\n" + "=" * 90)
    print("PHASE 3: ln_review_age sensitivity analysis")
    print("=" * 90)

    df_text = df_text.copy()
    # Use existing ln_review_age to get age in days
    # ln_review_age = ln(1 + days); so days ≈ exp(ln_review_age) - 1
    df_text["days"] = np.exp(df_text["ln_review_age"]) - 1
    df_text["years_since_visit"] = df_text["days"] / 365.25

    yrs = df_text["years_since_visit"]
    print(f"  Review age stats (years):")
    print(f"    min:  {yrs.min():.2f}")
    print(f"    25%:  {yrs.quantile(.25):.2f}")
    print(f"    50%:  {yrs.quantile(.50):.2f}")
    print(f"    75%:  {yrs.quantile(.75):.2f}")
    print(f"    max:  {yrs.max():.2f}")

    print("\n  Fit M1 and M2 at various age cutoffs:")
    print(f"  {'cutoff':<15}{'N_M1':>8}{'N_M2':>8}"
          f"{'M1_R2':>10}{'M2_R2':>10}{'M1_age_coef':>14}{'M2_age_coef':>14}")

    rows = []
    for max_years in [None, 10, 5, 3, 2, 1]:
        d = df_text if max_years is None else df_text[
            df_text["years_since_visit"] <= max_years]
        label = "ALL" if max_years is None else f"<= {max_years}y"

        m1 = fit_m1(d, winner_m1)
        m2 = fit_m2(d, winner_m2)
        if m1 is None or m2 is None:
            continue

        n1 = int(m1.nobs)
        n2 = int(m2.nobs)
        age_m1 = (m1.params.get("ln_review_age", np.nan),
                  m1.pvalues.get("ln_review_age", np.nan))
        age_m2 = (m2.params.get("ln_review_age", np.nan),
                  m2.pvalues.get("ln_review_age", np.nan))
        print(f"  {label:<15}{n1:>8}{n2:>8}"
              f"{m1.prsquared:>10.4f}{m2.prsquared:>10.4f}"
              f"  {age_m1[0]:+.3f} (p={age_m1[1]:.3f})"
              f"  {age_m2[0]:+.3f} (p={age_m2[1]:.3f})")

        rows.append({
            "cutoff":    label,
            "N_M1":      n1,
            "N_M2":      n2,
            "M1_R2":     round(m1.prsquared, 4),
            "M2_R2":     round(m2.prsquared, 4),
            "M1_age_coef": round(age_m1[0], 4) if not np.isnan(age_m1[0]) else "",
            "M1_age_p":  round(age_m1[1], 4) if not np.isnan(age_m1[1]) else "",
            "M2_age_coef": round(age_m2[0], 4) if not np.isnan(age_m2[0]) else "",
            "M2_age_p":  round(age_m2[1], 4) if not np.isnan(age_m2[1]) else "",
        })

    pd.DataFrame(rows).to_csv(OUT / "age_sensitivity.csv", index=False,
                              encoding="utf-8-sig")


# ───────────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────────
def main():
    df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
    df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
    df_text = derive(df_text)
    print(f"Loaded: {len(df_text)} reviews with text, "
          f"{df_text.user_id.nunique()} reviewers")

    m1_all, m1_front = phase1_m1_frontier(df_text)
    pairs = phase2_pair(df_text, m1_front)

    # Phase 3: run sensitivity on the recommended winner (7+5)
    winner_m1 = ALL7                                      # all 7 for M1
    winner_m2 = ["sentiment", "waited", "is_tourist",
                 "ln_user_followers", "ln_review_age"]    # 5-var M2
    phase3_age_sensitivity(df_text, winner_m1, winner_m2)

    print(f"\nAll outputs in: {OUT}")


if __name__ == "__main__":
    main()
