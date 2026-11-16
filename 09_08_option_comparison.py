"""
09_08_option_comparison.py
Compare three design options for the workshop paper:

  A (current)  SAME 7 predictors in M1 and M2
               M1 = M2 = {waited, is_tourist, ln(followers), sentiment,
                          ln(reviews), comp_alone, ln(review_age)}

  B            DIFFERENT predictors per model, theory-driven
               M1 = {waited, is_tourist, ln(followers), ln(reviews),
                     comp_alone, ln(review_age)}   (no sentiment)
               M2 = {waited, is_tourist, ln(followers), sentiment}

  C            SAME 7 in M1, M2 drops only the Brant-violating pair
               M1 = 7 vars (same as A)
               M2 = {waited, is_tourist, ln(followers), ln(reviews),
                     comp_alone}  (dropped sentiment + ln_review_age)

For each option, reports:
  - M1 fit: pseudo-R², AIC, BIC, N
  - M2 fit: McFadden R², AIC, BIC, N
  - Brant test for M2 (overall + per variable)
  - Significant var counts

Outputs (data/analysis/naver/workshop/option_comparison/):
  option_comparison_summary.csv
  option_<X>_m1.csv, option_<X>_m2.csv, option_<X>_brant.csv

Run:  python 09_08_option_comparison.py
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
OUT = DIR / "workshop" / "option_comparison"
OUT.mkdir(parents=True, exist_ok=True)

# ─── Variable definitions per option ────────────────────────────────────────
OPTIONS = {
    "A_same_7":  {
        "name": "A: SAME 7 predictors (current winner)",
        "m1":   ["waited", "is_tourist", "ln_user_followers", "sentiment",
                 "ln_user_reviews", "comp_alone", "ln_review_age"],
        "m2":   ["waited", "is_tourist", "ln_user_followers", "sentiment",
                 "ln_user_reviews", "comp_alone", "ln_review_age"],
        "m2_type": "ordered",
    },
    "B_different": {
        "name": "B: DIFFERENT theory-driven predictors",
        "m1":   ["waited", "is_tourist", "ln_user_followers",
                 "ln_user_reviews", "comp_alone", "ln_review_age"],
        "m2":   ["waited", "is_tourist", "ln_user_followers", "sentiment"],
        "m2_type": "ordered",
    },
    "C_drop_brant": {
        "name": "C: SAME 7 in M1, M2 drops Brant-violating vars",
        "m1":   ["waited", "is_tourist", "ln_user_followers", "sentiment",
                 "ln_user_reviews", "comp_alone", "ln_review_age"],
        "m2":   ["waited", "is_tourist", "ln_user_followers",
                 "ln_user_reviews", "comp_alone"],
        "m2_type": "ordered",
    },
    "D_binary_5star": {
        "name": "D: SAME 7 in M1, M2 as BINARY logit P(5 stars)",
        "m1":   ["waited", "is_tourist", "ln_user_followers", "sentiment",
                 "ln_user_reviews", "comp_alone", "ln_review_age"],
        "m2":   ["waited", "is_tourist", "ln_user_followers", "sentiment",
                 "ln_user_reviews", "comp_alone", "ln_review_age"],
        "m2_type": "binary",   # P(rating == 5)
    },
    "E_binary_B": {
        "name": "E: M1 like B (6 vars) + M2 BINARY P(5) with B's 4 vars",
        "m1":   ["waited", "is_tourist", "ln_user_followers",
                 "ln_user_reviews", "comp_alone", "ln_review_age"],
        "m2":   ["waited", "is_tourist", "ln_user_followers", "sentiment"],
        "m2_type": "binary",
    },
}

LABELS = {
    "waited": "Waited", "is_tourist": "Tourist",
    "ln_user_followers": "ln(followers)",
    "ln_user_reviews": "ln(reviews)",
    "sentiment": "Sentiment", "comp_alone": "Alone",
    "ln_review_age": "ln(review_age)",
}


# ─── Helpers ────────────────────────────────────────────────────────────────
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


def mcfadden_ordered(res, y):
    counts = np.bincount(y)
    ll0 = np.sum(counts[counts > 0] * np.log(counts[counts > 0] / len(y)))
    return 1 - res.llf / ll0


def tidy(res):
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "p": res.pvalues})
    out = out[~out.index.str.startswith(("place_", "const"))
              & ~out.index.str.contains("/")]
    out["label"]   = [LABELS.get(idx, idx) for idx in out.index]
    out["OR"]      = np.exp(out["coef"])
    out["sig"] = pd.cut(out["p"], [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                        labels=["***", "**", "*", ".", ""])
    return out[["label", "coef", "OR", "se", "p", "sig"]]


# ─── Fit models ─────────────────────────────────────────────────────────────
def fit_m1(data, cols):
    d = varying_places(data, "revisit")
    m = sm.Logit(d["revisit"], design(d, cols)).fit(
        disp=False, maxiter=300,
        cov_type="cluster", cov_kwds=clusters(d))
    return m, d


def fit_m2(data, cols, m2_type="ordered"):
    d = data.dropna(subset=["rating"]).reset_index(drop=True)
    d["rating_cls"] = pd.cut(d["rating"], [0, 4, 4.5, 5], labels=False).astype(int)
    d["five_star"]  = (d["rating"] == 5).astype(int)
    d = varying_places(d, "five_star")
    if m2_type == "binary":
        m = sm.Logit(d["five_star"], design(d, cols)).fit(
            disp=False, maxiter=300,
            cov_type="cluster", cov_kwds=clusters(d))
    else:
        m = OrderedModel(d["rating_cls"], design(d, cols, const=False),
                         distr="logit").fit(method="bfgs", disp=False,
                                            maxiter=2000, cov_type="cluster",
                                            cov_kwds=clusters(d))
    return m, d


# ─── Brant test (manual, cluster-robust) ───────────────────────────────────
def brant_test(data, cols):
    d = data.dropna(subset=["rating"]).reset_index(drop=True)
    d["rating_cls"] = pd.cut(d["rating"], [0, 4, 4.5, 5], labels=False).astype(int)
    d["y1"] = (d["rating_cls"] >= 1).astype(int)   # rating > 4
    d["y2"] = (d["rating_cls"] >= 2).astype(int)   # rating == 5

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

    m_y1 = fit_dichot("y1")
    m_y2 = fit_dichot("y2")

    keep = [c for c in cols if c in m_y1.params.index and c in m_y2.params.index]
    b1 = m_y1.params[keep]; s1 = m_y1.bse[keep]
    b2 = m_y2.params[keep]; s2 = m_y2.bse[keep]
    diff = b1 - b2
    se_diff = np.sqrt(s1**2 + s2**2)
    z = diff / se_diff
    p = 2 * (1 - norm.cdf(np.abs(z)))

    df_b = pd.DataFrame({
        "beta_P(Y>=1)": b1.round(4), "beta_P(Y>=2)": b2.round(4),
        "diff": diff.round(4), "SE_diff": se_diff.round(4),
        "z": z.round(3), "p": p.round(4),
    })
    df_b["violation"] = np.where(df_b["p"] < 0.05, "YES", "no")
    df_b["label"] = [LABELS.get(i, i) for i in df_b.index]

    chi2_stat = float((z ** 2).sum())
    p_overall = float(1 - chi2.cdf(chi2_stat, len(keep)))
    return df_b, {"chi2": round(chi2_stat, 3), "df": len(keep),
                  "p": round(p_overall, 4),
                  "violations": int((df_b["p"] < 0.05).sum()),
                  "total": len(keep)}


# ─── Run one option ─────────────────────────────────────────────────────────
def run_option(key, opt, df_text):
    print(f"\n{'=' * 72}")
    print(f"OPTION {key}:  {opt['name']}")
    print(f"{'=' * 72}")
    print(f"  M1 vars ({len(opt['m1'])}): {', '.join(opt['m1'])}")
    print(f"  M2 vars ({len(opt['m2'])}): {', '.join(opt['m2'])}")

    # Model 1
    m1, d1 = fit_m1(df_text, opt["m1"])
    t1 = tidy(m1)
    t1.round(4).to_csv(OUT / f"option_{key}_m1.csv", encoding="utf-8-sig")
    sig1 = int((t1["p"] < 0.05).sum())
    print(f"\n  M1 Revisit:  N={int(m1.nobs)}, pseudo-R²={m1.prsquared:.4f}, "
          f"AIC={m1.aic:.1f}, BIC={m1.bic:.1f}, sig={sig1}/{len(opt['m1'])}")

    # Model 2
    m2_type = opt.get("m2_type", "ordered")
    m2, d2 = fit_m2(df_text, opt["m2"], m2_type=m2_type)
    t2 = tidy(m2)
    t2.round(4).to_csv(OUT / f"option_{key}_m2.csv", encoding="utf-8-sig")
    if m2_type == "binary":
        r2 = m2.prsquared
        model_label = "M2 P(5★) BINARY"
    else:
        y2 = d2["rating_cls"].to_numpy()
        r2 = mcfadden_ordered(m2, y2)
        model_label = "M2 Rating ORDERED"
    sig2 = int((t2["p"] < 0.05).sum())
    print(f"  {model_label}: N={int(m2.nobs)}, "
          f"{'pseudo' if m2_type == 'binary' else 'McFadden'}-R²={r2:.4f}, "
          f"AIC={m2.aic:.1f}, BIC={m2.bic:.1f}, sig={sig2}/{len(opt['m2'])}")

    # Brant test: only applies to ordered logit
    if m2_type == "ordered":
        print(f"\n  Brant test on M2 ({len(opt['m2'])} predictors):")
        df_brant, overall = brant_test(df_text, opt["m2"])
        df_brant.to_csv(OUT / f"option_{key}_brant.csv", encoding="utf-8-sig")
        print(f"    overall chi²={overall['chi2']:.2f}, df={overall['df']}, "
              f"p={overall['p']:.4f}")
        print(f"    violations: {overall['violations']}/{overall['total']} "
              f"{'(⚠️ PO violated)' if overall['p'] < 0.05 else '(✓ PO holds)'}")
        if overall['violations'] > 0:
            bad = df_brant[df_brant['p'] < 0.05]
            print(f"    offending vars: "
                  f"{', '.join(bad['label'] + ' (p=' + bad['p'].astype(str) + ')')}")
    else:
        overall = {"chi2": np.nan, "df": np.nan, "p": np.nan,
                   "violations": np.nan, "total": np.nan}
        print(f"\n  Brant test: N/A (binary logit does not assume proportional odds)")

    po_holds = ("N/A" if m2_type == "binary"
                else ("YES" if overall["p"] >= 0.05 else "NO"))
    return {
        "option":           key,
        "name":             opt["name"],
        "M2_type":          m2_type,
        "n_vars_M1":        len(opt["m1"]),
        "n_vars_M2":        len(opt["m2"]),
        "N_M1":             int(m1.nobs),
        "pseudo_R2_M1":     round(m1.prsquared, 4),
        "AIC_M1":           round(m1.aic, 1),
        "BIC_M1":           round(m1.bic, 1),
        "LLF_M1":           round(m1.llf, 2),
        "sig_M1":           sig1,
        "N_M2":             int(m2.nobs),
        "R2_M2":            round(r2, 4),
        "AIC_M2":           round(m2.aic, 1),
        "BIC_M2":           round(m2.bic, 1),
        "LLF_M2":           round(m2.llf, 2),
        "sig_M2":           sig2,
        "brant_chi2":       overall["chi2"],
        "brant_df":         overall["df"],
        "brant_p":          overall["p"],
        "brant_violations": overall["violations"],
        "brant_total":      overall["total"],
        "PO_holds":         po_holds,
    }


# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
    df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
    df_text = derive(df_text)
    print(f"Loaded: {len(df_text)} reviews with text, "
          f"{df_text.user_id.nunique()} reviewers\n")

    results = [run_option(k, opt, df_text) for k, opt in OPTIONS.items()]
    summary = pd.DataFrame(results)
    summary.to_csv(OUT / "option_comparison_summary.csv", index=False,
                   encoding="utf-8-sig")

    print("\n" + "=" * 100)
    print("SUMMARY — comparison of design options")
    print("=" * 100)
    cols_show = ["option", "M2_type", "n_vars_M1", "n_vars_M2",
                 "pseudo_R2_M1", "AIC_M1",
                 "R2_M2", "AIC_M2",
                 "brant_p", "brant_violations", "PO_holds"]
    print(summary[cols_show].to_string(index=False))
    print("=" * 100)

    print(f"\nAll files saved under: {OUT}")


if __name__ == "__main__":
    main()
