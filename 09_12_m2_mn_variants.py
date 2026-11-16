"""
09_12_m2_mn_variants.py
Variants of M2 (multinomial logit, Y = {LOW, MID, TOP}) to find the best
reduced specification AND explore including variables that are NOT in M1
(so that M2 is not a strict subset of M1 — gives each model its own flavor).

M1 (binary logit, Revisit) is held fixed at the 7-var winner spec throughout.
Only M2 varies.

Specs tested:
  A. CORE_5          Shared core only (5 vars). Baseline for reduction.
  B. FULL_7          Current full 7-var multinomial (reference).

  Reductions:
  C. CORE_4_no_tour  Core 5 minus is_tourist
  D. CORE_4_no_foll  Core 5 minus ln_followers

  Replace core var with a NEW M2-only var:
  E. SWAP_tour_verif  Replace is_tourist with verif_receipt (verification)
  F. SWAP_foll_season Replace ln_followers with season_autumn

  Add a NEW M2-only var to core:
  G. CORE+verif       Core 5 + verif_receipt (6 vars)
  H. CORE+autumn      Core 5 + season_autumn (6 vars)
  I. CORE+reserved    Core 5 + reserved (6 vars)
  J. CORE+weekend     Core 5 + visit_weekend (6 vars)
  K. CORE+photos      Core 5 + ln(1+n_photos) (6 vars)

  Mix: shared core + M1-exclusive + M2-exclusive:
  L. CORE+verif+autumn  Core 5 + verif_receipt + season_autumn (7 vars)
  M. CORE+full_season   Core 5 + 3 season dummies (8 vars)

For each spec: pseudo-R², AIC, # significant vars.
We use the SAME 3-class rating grouping:
  LOW (<=3.5★), MID (4-4.5★), TOP (5★)

Outputs: data/analysis/naver/workshop/m2_mn_variants/
  mn_variants_summary.csv       side-by-side comparison
  mn_<spec>_coefs.csv           coefficients per spec
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
OUT = DIR / "workshop" / "m2_mn_variants"
OUT.mkdir(parents=True, exist_ok=True)

# Shared core (vars in BOTH M1 and M2)
CORE_5 = ["waited", "is_tourist", "ln_user_followers",
          "sentiment", "ln_review_age"]

# Specs to test for M2
SPECS = {
    # --- Baselines ---
    "CORE_5": {
        "name": "Shared core only (5 vars)",
        "vars": CORE_5,
    },
    "FULL_7": {
        "name": "Full 7 vars (current)",
        "vars": CORE_5 + ["ln_user_reviews", "comp_alone"],
    },

    # --- Pure reductions ---
    "CORE_4_no_tour": {
        "name": "Core minus is_tourist (4 vars)",
        "vars": [v for v in CORE_5 if v != "is_tourist"],
    },
    "CORE_4_no_foll": {
        "name": "Core minus ln(followers) (4 vars)",
        "vars": [v for v in CORE_5 if v != "ln_user_followers"],
    },

    # --- Swap a core var for a M2-UNIQUE var ---
    "SWAP_tour_verif": {
        "name": "Core minus is_tourist + verif_receipt",
        "vars": [v for v in CORE_5 if v != "is_tourist"] + ["verif_receipt"],
    },
    "SWAP_foll_season": {
        "name": "Core minus ln(followers) + season_autumn",
        "vars": [v for v in CORE_5 if v != "ln_user_followers"]
                + ["season_autumn"],
    },

    # --- Add a M2-unique var to core ---
    "CORE_plus_verif": {
        "name": "Core 5 + verif_receipt (verification; 6 vars)",
        "vars": CORE_5 + ["verif_receipt"],
    },
    "CORE_plus_autumn": {
        "name": "Core 5 + season_autumn (6 vars)",
        "vars": CORE_5 + ["season_autumn"],
    },
    "CORE_plus_reserved": {
        "name": "Core 5 + reserved (6 vars)",
        "vars": CORE_5 + ["reserved"],
    },
    "CORE_plus_weekend": {
        "name": "Core 5 + visit_weekend (6 vars)",
        "vars": CORE_5 + ["visit_weekend"],
    },
    "CORE_plus_photos": {
        "name": "Core 5 + ln(1+n_photos) (6 vars)",
        "vars": CORE_5 + ["ln_photos"],
    },

    # --- Combinations: core + M2-unique vars ---
    "CORE_plus_verif_autumn": {
        "name": "Core 5 + verif_receipt + season_autumn (7 vars)",
        "vars": CORE_5 + ["verif_receipt", "season_autumn"],
    },
    "CORE_plus_all_seasons": {
        "name": "Core 5 + 3 season dummies (8 vars)",
        "vars": CORE_5 + ["season_summer", "season_autumn", "season_winter"],
    },
}

LABELS = {
    "waited": "Waited", "is_tourist": "Tourist",
    "ln_user_followers": "ln(1+followers)",
    "ln_user_reviews": "ln(1+reviews)",
    "sentiment": "Sentiment", "comp_alone": "Alone",
    "ln_review_age": "ln(1+review_age)",
    "verif_receipt": "Verified by receipt",
    "season_summer": "Season: summer",
    "season_autumn": "Season: autumn",
    "season_winter": "Season: winter",
    "visit_weekend": "Weekend",
    "reserved": "Reservation",
    "ln_photos": "ln(1+photos)",
}


# ─── Helpers ────────────────────────────────────────────────────────────────
def derive(df):
    df = df.copy()
    df["is_tourist"] = df["purp_travel"].astype(float)
    return df


def group_rating(df):
    df = df.copy()
    df["rating_3cat"] = np.select(
        [df["rating"] <= 3.5,
         (df["rating"] >= 4.0) & (df["rating"] <= 4.5),
         df["rating"] == 5.0],
        [0, 1, 2], default=np.nan,
    )
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


def fit_mn(d, cols):
    """Multinomial logit with TOP = baseline. Progressive fallback on
    non-convergence."""
    d = d.copy()
    d["mn_y"] = 2 - d["rating_3cat"].astype(int)      # TOP=0, MID=1, LOW=2
    X = design(d, cols)
    try:
        m = sm.MNLogit(d["mn_y"], X).fit(
            method="bfgs", disp=False, maxiter=2000,
            cov_type="cluster", cov_kwds=clusters(d))
        if m.params.isna().any().any() or not np.isfinite(m.aic):
            raise RuntimeError("NaN params")
        return m, "FE + cluster"
    except Exception:
        try:
            m = sm.MNLogit(d["mn_y"], X).fit(method="bfgs", disp=False,
                                              maxiter=2000)
            return m, "FE no-cluster"
        except Exception:
            X_simple = sm.add_constant(d[cols].astype(float))
            m = sm.MNLogit(d["mn_y"], X_simple).fit(method="bfgs",
                                                     disp=False, maxiter=2000)
            return m, "No-FE"


# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
    df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
    df_text = derive(df_text)
    df = df_text.dropna(subset=["rating"]).reset_index(drop=True)
    df = group_rating(df)
    df = df.dropna(subset=["rating_3cat"]).reset_index(drop=True)
    df["five_star"] = (df["rating"] == 5.0).astype(int)
    df = varying_places(df, "five_star")
    print(f"Loaded M2 sample: {len(df)} reviews\n")

    results = []
    for key, spec in SPECS.items():
        print(f"[{key:<24s}] n={len(spec['vars']):>2}  {spec['name']}")
        try:
            m, mode = fit_mn(df, spec["vars"])
            # Count predictor sig: a predictor is sig if sig in AT LEAST ONE
            # of the two comparisons (MID vs TOP, LOW vs TOP)
            params = m.params
            pvals  = m.pvalues
            n_sig_either = 0
            n_sig_both   = 0
            per_var = []
            for v in spec["vars"]:
                if v not in params.index:
                    continue
                p_mid = pvals.loc[v, params.columns[0]]
                p_low = pvals.loc[v, params.columns[1]]
                b_mid = params.loc[v, params.columns[0]]
                b_low = params.loc[v, params.columns[1]]
                is_sig_either = (p_mid < 0.05) or (p_low < 0.05)
                is_sig_both   = (p_mid < 0.05) and (p_low < 0.05)
                n_sig_either += int(is_sig_either)
                n_sig_both   += int(is_sig_both)
                per_var.append({
                    "variable": v, "label": LABELS.get(v, v),
                    "OR_MID": round(np.exp(b_mid), 3),
                    "p_MID":  round(p_mid, 4),
                    "OR_LOW": round(np.exp(b_low), 3),
                    "p_LOW":  round(p_low, 4),
                })
            pd.DataFrame(per_var).to_csv(OUT / f"mn_{key}_coefs.csv",
                                          index=False, encoding="utf-8-sig")
            r2 = m.prsquared
            aic = m.aic
            bic = m.bic
            print(f"  -> {mode}   R²={r2:.4f}  AIC={aic:.1f}  "
                  f"BIC={bic:.1f}  sig(either)={n_sig_either}/{len(spec['vars'])}")
            results.append({
                "spec":           key,
                "name":           spec["name"],
                "n_vars":         len(spec["vars"]),
                "fit_mode":       mode,
                "N":              int(m.nobs),
                "pseudo_R2":      round(r2, 4),
                "AIC":            round(aic, 1),
                "BIC":            round(bic, 1),
                "sig_either":     n_sig_either,
                "sig_both":       n_sig_both,
                "vars":           " | ".join(spec["vars"]),
            })
        except Exception as e:
            print(f"  -> FAILED: {str(e)[:80]}")
            results.append({
                "spec":   key,  "name": spec["name"],
                "n_vars": len(spec["vars"]), "fit_mode": "FAILED",
                "N": "", "pseudo_R2": "", "AIC": "", "BIC": "",
                "sig_either": "", "sig_both": "",
                "vars": " | ".join(spec["vars"]),
            })

    summary = pd.DataFrame(results)
    summary.to_csv(OUT / "mn_variants_summary.csv", index=False,
                   encoding="utf-8-sig")

    print("\n" + "=" * 100)
    print("SUMMARY — M2 MULTINOMIAL VARIANTS (sorted by AIC, lower = better)")
    print("=" * 100)
    good = summary[summary["pseudo_R2"] != ""].copy()
    good = good.sort_values("AIC")
    print(good[["spec", "n_vars", "pseudo_R2", "AIC", "BIC",
                "sig_either", "sig_both"]].to_string(index=False))

    print("\n" + "=" * 100)
    print("SORTED BY pseudo-R² (higher = better)")
    print("=" * 100)
    print(good.sort_values("pseudo_R2", ascending=False)[
        ["spec", "n_vars", "pseudo_R2", "AIC", "sig_either",
         "sig_both"]].to_string(index=False))

    print(f"\nSaved: {OUT}/mn_variants_summary.csv")
    print(f"       and {len(SPECS)} coefficient files")


if __name__ == "__main__":
    main()
