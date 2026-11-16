"""
09_11_m2_multinomial.py
Compare three M2 (rating) specifications on the SAME 3-class grouping:

    LOW  (<=3.5★)  :   276 reviews  (6.8%)
    MID  (4-4.5★)  :   728 reviews  (18.0%)
    TOP  (5★)      : 3,040 reviews  (75.2%)

Three model types estimated with the SAME 7-var predictor set:
    1. ORDERED LOGIT    (respects ordering, requires proportional odds)
    2. MULTINOMIAL LOGIT (ignores ordering, no PO assumption)
    3. BINARY LOGIT     (P(5★) vs anything else) — current D baseline

All runs:
  - 7 predictors: waited, is_tourist, ln(followers), sentiment,
                  ln(reviews), comp_alone, ln(review_age)
  - 28 place fixed effects
  - SE clustered by reviewer (user_id)

Outputs: data/analysis/naver/workshop/m2_multinomial/
  ordered_logit_coefs.csv
  multinomial_coefs.csv       # 2 sets of coefficients (low vs top, mid vs top)
  binary_coefs.csv
  brant_test_ordered.csv
  comparison_summary.csv
  report.txt
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
from scipy.stats import chi2, norm

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop" / "m2_multinomial"
OUT.mkdir(parents=True, exist_ok=True)

PREDICTORS = ["waited", "is_tourist", "ln_user_followers", "sentiment",
              "ln_user_reviews", "comp_alone", "ln_review_age"]

LABELS = {
    "waited": "Waited", "is_tourist": "Tourist",
    "ln_user_followers": "ln(1+followers)",
    "ln_user_reviews": "ln(1+reviews)",
    "sentiment": "Sentiment", "comp_alone": "Alone",
    "ln_review_age": "ln(1+review_age)",
}


# ─── Helpers ────────────────────────────────────────────────────────────────
def derive(df):
    df = df.copy()
    df["is_tourist"] = df["purp_travel"].astype(float)
    return df


def group_rating(df):
    """Assign 3-class grouping as specified by the user:
       0 = LOW  (<=3.5), 1 = MID (4-4.5), 2 = TOP (5)."""
    df = df.copy()
    df["rating_3cat"] = np.select(
        [df["rating"] <= 3.5,
         (df["rating"] >= 4.0) & (df["rating"] <= 4.5),
         df["rating"] == 5.0],
        [0, 1, 2],
        default=np.nan,
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


def mcfadden_ordered(res, y):
    counts = np.bincount(y)
    ll0 = np.sum(counts[counts > 0] * np.log(counts[counts > 0] / len(y)))
    return 1 - res.llf / ll0


def tidy_binary(res):
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "p": res.pvalues})
    out = out[~out.index.str.startswith(("place_", "const"))]
    out["label"] = [LABELS.get(idx, idx) for idx in out.index]
    out["OR"]    = np.exp(out["coef"])
    out["ci_low"]  = np.exp(out["coef"] - 1.96 * out["se"])
    out["ci_high"] = np.exp(out["coef"] + 1.96 * out["se"])
    out["sig"] = pd.cut(out["p"], [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                        labels=["***", "**", "*", ".", ""])
    return out[["label", "coef", "OR", "ci_low", "ci_high", "se", "p", "sig"]]


# ─── Models ────────────────────────────────────────────────────────────────
def fit_ordered(d, cols):
    """Ordered logit on 3-class rating."""
    m = OrderedModel(d["rating_3cat"].astype(int),
                     design(d, cols, const=False),
                     distr="logit").fit(method="bfgs", disp=False,
                                        maxiter=2000, cov_type="cluster",
                                        cov_kwds=clusters(d))
    return m


def fit_multinomial(d, cols, use_place_fe=True, use_cluster=True):
    """Multinomial logit (base = TOP = category 2).
    With 7 predictors + 56 place dummies * 2 non-base cats = many parameters,
    and LOW having only 276 obs, convergence can fail.  We try progressively
    simpler specs if the first fails.
    """
    # MNLogit treats the LOWEST integer as the baseline by default — invert
    # the coding so that TOP (currently 2) becomes the baseline (0).
    d = d.copy()
    d["mn_y"] = 2 - d["rating_3cat"].astype(int)   # TOP->0, MID->1, LOW->2
    X = design(d, cols) if use_place_fe else sm.add_constant(
        d[cols].astype(float))

    fit_kw = dict(disp=False, maxiter=2000, method="bfgs")
    if use_cluster:
        fit_kw.update(cov_type="cluster", cov_kwds=clusters(d))

    m = sm.MNLogit(d["mn_y"], X).fit(**fit_kw)
    return m


def fit_multinomial_robust(d, cols):
    """Try several fallbacks until one converges with real params."""
    attempts = [
        {"use_place_fe": True,  "use_cluster": True,  "label": "FE + cluster SE"},
        {"use_place_fe": True,  "use_cluster": False, "label": "FE, non-cluster SE"},
        {"use_place_fe": False, "use_cluster": True,  "label": "No FE + cluster SE"},
        {"use_place_fe": False, "use_cluster": False, "label": "No FE, non-cluster"},
    ]
    for a in attempts:
        try:
            m = fit_multinomial(d, cols, use_place_fe=a["use_place_fe"],
                                use_cluster=a["use_cluster"])
            # Check for NaN in params or AIC
            if (not m.params.isna().any().any()) and np.isfinite(m.aic):
                print(f"  -> Multinomial converged with: {a['label']}")
                return m, a["label"]
        except Exception as e:
            print(f"  -> Attempt '{a['label']}' failed: {str(e)[:80]}")
            continue
    return None, "ALL ATTEMPTS FAILED"


def fit_binary(d, cols):
    """Binary logit on P(rating == 5)."""
    d = d.copy()
    d["five_star"] = (d["rating"] == 5.0).astype(int)
    d = varying_places(d, "five_star")
    m = sm.Logit(d["five_star"], design(d, cols)).fit(
        disp=False, maxiter=300,
        cov_type="cluster", cov_kwds=clusters(d))
    return m, d


# ─── Brant test (ordered logit on 3-class) ─────────────────────────────────
def brant_ordered_3cat(d, cols):
    """H0: proportional odds in a 3-class ordered logit.
    Fit two cumulative binary logits:
       Logit1: P(Y >= 1)  (MID or TOP)
       Logit2: P(Y >= 2)  (TOP only)
    Compare coefficients across the two."""
    d = d.copy()
    d["y1"] = (d["rating_3cat"] >= 1).astype(int)
    d["y2"] = (d["rating_3cat"] >= 2).astype(int)

    def fit_dichot(y_name):
        d_use = varying_places(d, y_name)
        X_use = design(d_use, cols)
        const_cols = [c for c in X_use.columns
                      if c != "const" and X_use[c].nunique() == 1]
        X_use = X_use.drop(columns=const_cols)
        try:
            return sm.Logit(d_use[y_name], X_use).fit(
                disp=False, maxiter=500,
                cov_type="cluster", cov_kwds=clusters(d_use))
        except Exception:
            return sm.Logit(d_use[y_name], X_use).fit(
                disp=False, maxiter=500, cov_type="HC1")

    m1 = fit_dichot("y1")
    m2 = fit_dichot("y2")

    keep = [c for c in cols if c in m1.params.index and c in m2.params.index]
    b1 = m1.params[keep]; s1 = m1.bse[keep]
    b2 = m2.params[keep]; s2 = m2.bse[keep]
    diff = b1 - b2
    se_diff = np.sqrt(s1**2 + s2**2)
    z = diff / se_diff
    p = 2 * (1 - norm.cdf(np.abs(z)))

    out = pd.DataFrame({
        "beta_P(Y>=1_MID|TOP)": b1.round(4),
        "beta_P(Y>=2_TOP)":     b2.round(4),
        "diff":    diff.round(4),
        "SE_diff": se_diff.round(4),
        "z":       z.round(3),
        "p":       p.round(4),
    })
    out["violation (p<.05)"] = np.where(out["p"] < 0.05, "YES", "no")
    out["label"] = [LABELS.get(i, i) for i in out.index]
    chi2_stat = float((z ** 2).sum())
    return out, {
        "chi2": round(chi2_stat, 3),
        "df":   len(keep),
        "p":    round(1 - chi2.cdf(chi2_stat, len(keep)), 4),
        "violations": int((out["p"] < 0.05).sum()),
        "total": len(keep),
    }


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

    print(f"\nLoaded M2 sample: {len(df)} reviews with rating")
    print("3-class distribution:")
    print(df["rating_3cat"].value_counts().sort_index()
          .rename(index={0: "LOW (<=3.5)", 1: "MID (4-4.5)",
                          2: "TOP (5)"}).to_string())

    # ── 1. Ordered logit ────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("1. ORDERED LOGIT (3 classes: LOW < MID < TOP)")
    print("=" * 90)
    ord_m = fit_ordered(df, PREDICTORS)
    ord_t = tidy_binary(ord_m)
    ord_t = ord_t[~ord_t.index.str.contains("/")]
    ord_t.round(4).to_csv(OUT / "ordered_logit_coefs.csv",
                          encoding="utf-8-sig")
    ord_r2 = mcfadden_ordered(ord_m, df["rating_3cat"].astype(int).to_numpy())
    print(f"N = {int(ord_m.nobs)}, McFadden R² = {ord_r2:.4f}, "
          f"AIC = {ord_m.aic:.1f}, BIC = {ord_m.bic:.1f}")
    print("\nCoefficients (one per predictor; assumes proportional odds):")
    print(ord_t[["label", "coef", "OR", "ci_low", "ci_high",
                 "p", "sig"]].to_string())

    # Brant
    brant_df, brant_overall = brant_ordered_3cat(df, PREDICTORS)
    brant_df.to_csv(OUT / "brant_test_ordered.csv", encoding="utf-8-sig")
    print(f"\nBRANT TEST (proportional odds):")
    print(f"  chi² = {brant_overall['chi2']:.3f}, df = {brant_overall['df']}, "
          f"p = {brant_overall['p']:.4f}")
    print(f"  violations: {brant_overall['violations']}/{brant_overall['total']} "
          f"{'⚠️ PO violated' if brant_overall['p'] < 0.05 else '✓ PO holds'}")
    print(brant_df[["label", "beta_P(Y>=1_MID|TOP)",
                    "beta_P(Y>=2_TOP)", "diff", "p",
                    "violation (p<.05)"]].to_string(index=False))

    # ── 2. Multinomial logit ────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("2. MULTINOMIAL LOGIT (base = TOP; coefs are vs TOP)")
    print("=" * 90)
    mn_m, mn_label = fit_multinomial_robust(df, PREDICTORS)
    if mn_m is None:
        print("Multinomial failed with all attempted specs. Skipping.")
        mn_r2 = np.nan
        mn_aic = np.nan
        mn_bic = np.nan
        mn_df = pd.DataFrame()
    else:
        params = mn_m.params
        pvals  = mn_m.pvalues
        ses    = mn_m.bse
        print(f"  (converged with: {mn_label})")
        rows = []
        for cat_idx, cat_name in enumerate(["MID vs TOP", "LOW vs TOP"]):
            col = params.columns[cat_idx]
            for v in PREDICTORS:
                if v not in params.index:
                    continue
                b = params.loc[v, col]
                p = pvals.loc[v, col]
                s = ses.loc[v, col]
                rows.append({
                    "comparison": cat_name,
                    "variable": v,
                    "label":    LABELS.get(v, v),
                    "coef":     round(b, 4),
                    "OR":       round(np.exp(b), 2),
                    "ci_low":   round(np.exp(b - 1.96 * s), 2),
                    "ci_high":  round(np.exp(b + 1.96 * s), 2),
                    "se":       round(s, 4),
                    "p":        round(p, 4),
                    "sig":      ("***" if p < 0.001 else "**" if p < 0.01
                                 else "*" if p < 0.05 else "." if p < 0.1 else ""),
                })
        mn_df = pd.DataFrame(rows)
        mn_df.to_csv(OUT / "multinomial_coefs.csv", index=False,
                     encoding="utf-8-sig")
        mn_r2 = mn_m.prsquared
        mn_aic = mn_m.aic
        mn_bic = mn_m.bic
        print(f"N = {int(mn_m.nobs)}, McFadden pseudo-R² = {mn_r2:.4f}, "
              f"AIC = {mn_aic:.1f}, BIC = {mn_bic:.1f}")
        print(f"Spec used: {mn_label}")
        print("\nCoefficients by comparison:\n")
        for cat in ["MID vs TOP", "LOW vs TOP"]:
            sub = mn_df[mn_df["comparison"] == cat]
            print(f"  >>> {cat} <<<")
            print(sub[["label", "coef", "OR", "ci_low", "ci_high",
                       "p", "sig"]].to_string(index=False))
            print()

    # ── 3. Binary logit (current D baseline) ────────────────────────────
    print("=" * 90)
    print("3. BINARY LOGIT  P(5★ vs not-5★)   [current D baseline]")
    print("=" * 90)
    bin_m, bin_d = fit_binary(df, PREDICTORS)
    bin_t = tidy_binary(bin_m)
    bin_t.round(4).to_csv(OUT / "binary_coefs.csv", encoding="utf-8-sig")
    bin_r2 = bin_m.prsquared
    print(f"N = {int(bin_m.nobs)}, pseudo-R² = {bin_r2:.4f}, "
          f"AIC = {bin_m.aic:.1f}, BIC = {bin_m.bic:.1f}")
    print(bin_t[["label", "coef", "OR", "ci_low", "ci_high",
                 "p", "sig"]].to_string())

    # ── 4. Summary comparison ───────────────────────────────────────────
    print("\n" + "=" * 90)
    print("SUMMARY  —  three M2 approaches on the SAME 7 predictors")
    print("=" * 90)
    summary = pd.DataFrame([
        {"model": "Ordered logit (3 cats)",
         "N": int(ord_m.nobs),
         "pseudo_R2": round(ord_r2, 4),
         "AIC": round(ord_m.aic, 1),
         "BIC": round(ord_m.bic, 1),
         "n_param_predictors": 7,
         "n_cols_in_table": 1,
         "PO_assumption":
             f"REQUIRED (Brant p={brant_overall['p']}, "
             f"{brant_overall['violations']}/{brant_overall['total']} violate)"},
        {"model": f"Multinomial (3 cats, vs TOP) [{mn_label}]",
         "N": int(mn_m.nobs) if mn_m is not None else "",
         "pseudo_R2": round(mn_r2, 4) if np.isfinite(mn_r2) else "",
         "AIC": round(mn_aic, 1) if np.isfinite(mn_aic) else "",
         "BIC": round(mn_bic, 1) if np.isfinite(mn_bic) else "",
         "n_param_predictors": 14,
         "n_cols_in_table": 2,
         "PO_assumption": "NOT required"},
        {"model": "Binary P(5★)",
         "N": int(bin_m.nobs),
         "pseudo_R2": round(bin_r2, 4),
         "AIC": round(bin_m.aic, 1),
         "BIC": round(bin_m.bic, 1),
         "n_param_predictors": 7,
         "n_cols_in_table": 1,
         "PO_assumption": "NOT required"},
    ])
    summary.to_csv(OUT / "comparison_summary.csv", index=False,
                   encoding="utf-8-sig")
    print(summary.to_string(index=False))

    # Save text report
    mn_txt = (mn_df.to_string(index=False) if not mn_df.empty
              else "Multinomial failed to converge")
    (OUT / "report.txt").write_text("\n".join([
        "M2 THREE-APPROACH COMPARISON", "=" * 60, "",
        f"Sample: {len(df)} reviews with rating",
        f"Grouping: LOW (<=3.5★)={int((df.rating_3cat==0).sum())}, "
        f"MID (4-4.5★)={int((df.rating_3cat==1).sum())}, "
        f"TOP (5★)={int((df.rating_3cat==2).sum())}",
        "", summary.to_string(index=False), "",
        "ORDERED LOGIT:", ord_t.to_string(), "",
        "BRANT TEST:", brant_df.to_string(), "",
        f"  overall chi²={brant_overall['chi2']}, "
        f"p={brant_overall['p']}", "",
        "MULTINOMIAL (vs TOP):", mn_txt, "",
        "BINARY P(5★):", bin_t.to_string(),
    ]), encoding="utf-8")

    print(f"\nAll outputs saved in: {OUT}")


if __name__ == "__main__":
    main()
