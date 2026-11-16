"""
09_07_workshop_diagnostics.py
Full diagnostic suite for the winning workshop specification:

    WINNER:  min+rev+alone+age (7 vars)
    X = [waited, is_tourist, ln(1+followers), sentiment,
         ln(1+reviews), comp_alone, ln(1+review_age)]

Reports:
  1. Baseline fit of M1 (binary logit, Revisit) and M2 (ordered logit, Rating)
  2. 5-fold cross-validation GROUPED by reviewer -> AUC, Brier, log-loss,
     accuracy, balanced accuracy, F1 (M1); classification accuracy, RMSE (M2)
  3. Brant-style test for M2 proportional-odds assumption
  4. Likelihood-ratio test: minimal (4 vars) vs. winner (7 vars)
  5. BIC alongside AIC for both models

Outputs (data/analysis/naver/workshop/diagnostics/):
  wd_m1_cv.csv            # cross-validation metrics for M1
  wd_m2_cv.csv            # cross-validation metrics for M2
  wd_brant.csv            # per-variable proportional-odds test
  wd_lr_test.csv          # likelihood-ratio tests
  wd_fit_summary.csv      # headline fit (AIC/BIC/LLF/pseudo-R2) side by side
  wd_diagnostics_report.txt   # printable report

Run:  python 09_07_workshop_diagnostics.py
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
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (roc_auc_score, brier_score_loss, log_loss,
                             accuracy_score, balanced_accuracy_score,
                             precision_score, recall_score, f1_score)

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop" / "diagnostics"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 42

MINIMAL = ["waited", "is_tourist", "ln_user_followers", "sentiment"]
WINNER  = MINIMAL + ["ln_user_reviews", "comp_alone", "ln_review_age"]

LABELS = {
    "waited": "Waited", "is_tourist": "Tourist (purp_travel)",
    "ln_user_followers": "ln(1+followers)", "ln_user_reviews": "ln(1+reviews)",
    "sentiment": "Sentiment", "comp_alone": "Alone",
    "ln_review_age": "ln(1+review_age)",
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


# ─── 1. Baseline fits ───────────────────────────────────────────────────────
def fit_m1(data, cols):
    d = varying_places(data, "revisit")
    return (sm.Logit(d["revisit"], design(d, cols))
            .fit(disp=False, maxiter=300, cov_type="cluster",
                 cov_kwds=clusters(d))), d


def fit_m2(data, cols):
    d = data.dropna(subset=["rating"]).reset_index(drop=True)
    d["rating_cls"] = pd.cut(d["rating"], [0, 4, 4.5, 5], labels=False).astype(int)
    d["five_star"]  = (d["rating"] == 5).astype(int)
    d = varying_places(d, "five_star")
    return (OrderedModel(d["rating_cls"], design(d, cols, const=False),
                         distr="logit").fit(method="bfgs", disp=False,
                                            maxiter=2000, cov_type="cluster",
                                            cov_kwds=clusters(d))), d


def fit_summary(m1, m1d, m2, m2d, name):
    y2 = m2d["rating_cls"].to_numpy()
    return {
        "spec":          name,
        "n_predictors":  int((~m1.params.index.str.startswith(
                            ("place_", "const"))).sum()),
        "N_M1":          int(m1.nobs),
        "LLF_M1":        round(m1.llf, 2),
        "pseudo_R2_M1":  round(m1.prsquared, 4),
        "AIC_M1":        round(m1.aic, 1),
        "BIC_M1":        round(m1.bic, 1),
        "N_M2":          int(m2.nobs),
        "LLF_M2":        round(m2.llf, 2),
        "McFadden_R2_M2": round(mcfadden_ordered(m2, y2), 4),
        "AIC_M2":        round(m2.aic, 1),
        "BIC_M2":        round(m2.bic, 1),
    }


# ─── 2. Cross-validation (5-fold grouped by reviewer) ──────────────────────
def cv_m1(data, cols):
    d = varying_places(data, "revisit")
    X = design(d, cols)
    y = d["revisit"].to_numpy()
    folds = GroupKFold(n_splits=5)
    p, base = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in folds.split(X, y, groups=d["user_id"]):
        try:
            res = sm.Logit(y[tr], X.iloc[tr]).fit(disp=False, maxiter=300)
            p[te] = res.predict(X.iloc[te])
        except np.linalg.LinAlgError:
            from sklearn.linear_model import LogisticRegression
            model = LogisticRegression(C=1e3, max_iter=5000).fit(
                X.iloc[tr].drop(columns="const"), y[tr])
            p[te] = model.predict_proba(X.iloc[te].drop(columns="const"))[:, 1]
        base[te] = y[tr].mean()
    hat = (p >= 0.5).astype(int)
    return {
        "AUC":                roc_auc_score(y, p),
        "Brier":              brier_score_loss(y, p),
        "Brier (base rate)":  brier_score_loss(y, base),
        "Log-loss":           log_loss(y, p),
        "Accuracy @0.5":      accuracy_score(y, hat),
        "Accuracy (always 'no')": 1 - y.mean(),
        "Balanced accuracy":  balanced_accuracy_score(y, hat),
        "Precision (revisit)": precision_score(y, hat, zero_division=0),
        "Recall (revisit)":   recall_score(y, hat),
        "F1 (revisit)":       f1_score(y, hat),
        "N":                  len(y),
        "folds":              5,
    }


def cv_m2(data, cols):
    d = data.dropna(subset=["rating"]).reset_index(drop=True)
    d["rating_cls"] = pd.cut(d["rating"], [0, 4, 4.5, 5], labels=False).astype(int)
    d["five_star"]  = (d["rating"] == 5).astype(int)
    d = varying_places(d, "five_star")
    X = design(d, cols, const=False)
    y = d["rating_cls"].to_numpy()
    folds = GroupKFold(n_splits=5)
    exp_ord, cls_ord = np.zeros(len(y)), np.zeros(len(y))
    base_mean, base_mode = np.zeros(len(y)), np.zeros(len(y))
    for tr, te in folds.split(X, y, groups=d["user_id"]):
        res = OrderedModel(y[tr], X.iloc[tr], distr="logit").fit(
            method="bfgs", disp=False, maxiter=2000)
        probs = np.asarray(res.model.predict(res.params, exog=X.iloc[te]))
        exp_ord[te] = probs @ np.arange(probs.shape[1])
        cls_ord[te] = probs.argmax(axis=1)
        base_mean[te] = y[tr].mean()
        base_mode[te] = np.bincount(y[tr]).argmax()

    def rmse(a): return float(np.sqrt(np.mean((y - a) ** 2)))
    return {
        "RMSE ordered logit":            rmse(exp_ord),
        "RMSE (predict mean)":           rmse(base_mean),
        "MAE ordered logit":             float(np.mean(np.abs(y - exp_ord))),
        "MAE (predict mean)":            float(np.mean(np.abs(y - base_mean))),
        "Exact accuracy (ordered)":      float(np.mean(cls_ord == y)),
        "Exact accuracy (always mode)":  float(np.mean(base_mode == y)),
        "Within +-1 accuracy (ordered)": float(np.mean(np.abs(cls_ord - y) <= 1)),
        "N":                             len(y),
        "folds":                         5,
    }


# ─── 3. Brant-style test (manual) ──────────────────────────────────────────
def brant_test(data, cols):
    """
    For the K=3 ordered outcome (rating_cls in {0,1,2}), fit two binary logits:
      Logit1: P(Y >= 1)   (rating > 4)
      Logit2: P(Y >= 2)   (rating == 5)
    Under proportional odds H0, beta coefficients should be equal across the
    two logits.  For each predictor we report:
      beta_1, beta_2, diff, SE(diff)*, z, p
      *approximation: assumes independence between the two logits (conservative)
    Overall test: sum of z^2 ~ chi^2(k)
    """
    d = data.dropna(subset=["rating"]).reset_index(drop=True)
    d["rating_cls"] = pd.cut(d["rating"], [0, 4, 4.5, 5], labels=False).astype(int)
    d["y1"] = (d["rating_cls"] >= 1).astype(int)   # rating > 4
    d["y2"] = (d["rating_cls"] >= 2).astype(int)   # rating == 5

    def fit_dichot(y_name):
        """Fit binary logit on dichotomized y, dropping places with no variation."""
        d_use = varying_places(d, y_name)
        X_use = design(d_use, cols)
        # Drop place columns that collapsed to constant after filtering
        const_cols = [c for c in X_use.columns
                      if c != "const" and X_use[c].nunique() == 1]
        X_use = X_use.drop(columns=const_cols)
        try:
            return sm.Logit(d_use[y_name], X_use).fit(
                disp=False, maxiter=500,
                cov_type="cluster", cov_kwds=clusters(d_use))
        except (np.linalg.LinAlgError, Exception):
            # Fallback: HC1 instead of clustered SE
            return sm.Logit(d_use[y_name], X_use).fit(
                disp=False, maxiter=500, cov_type="HC1")

    m_y1 = fit_dichot("y1")
    m_y2 = fit_dichot("y2")

    # Keep only predictors present in BOTH models
    keep = [c for c in cols if c in m_y1.params.index and c in m_y2.params.index]
    b1 = m_y1.params[keep]
    b2 = m_y2.params[keep]
    s1 = m_y1.bse[keep]
    s2 = m_y2.bse[keep]
    diff = b1 - b2
    se_diff = np.sqrt(s1**2 + s2**2)           # independence approx (conservative)
    z = diff / se_diff
    p_z = 2 * (1 - norm.cdf(np.abs(z)))

    df_brant = pd.DataFrame({
        "beta_P(Y>=1)":  b1.round(4),
        "beta_P(Y>=2)":  b2.round(4),
        "diff":          diff.round(4),
        "SE_diff":       se_diff.round(4),
        "z":             z.round(3),
        "p":             p_z.round(4),
    })
    df_brant["violation (p<.05)"] = np.where(df_brant["p"] < 0.05, "YES", "no")
    df_brant["label"] = [LABELS.get(i, i) for i in df_brant.index]

    chi2_stat = float((z ** 2).sum())
    df_free   = len(keep)
    p_overall = float(1 - chi2.cdf(chi2_stat, df_free))

    return df_brant, {
        "chi2": round(chi2_stat, 3),
        "df":   df_free,
        "p":    round(p_overall, 4),
        "violations": int((df_brant["p"] < 0.05).sum()),
        "total":      df_free,
    }


# ─── 4. Likelihood-ratio test (nested) ─────────────────────────────────────
def lr_test(data, cols_restricted, cols_full, fit_func):
    """
    LR = 2 * (LL_full - LL_restricted) ~ chi^2 ( df_full - df_restricted )
    IMPORTANT: both models must be fit on exactly the same sample.
    """
    m_r, d_r = fit_func(data, cols_restricted)
    m_f, d_f = fit_func(data, cols_full)
    if int(m_r.nobs) != int(m_f.nobs):
        return {"warning": f"N differs: restricted {int(m_r.nobs)} vs "
                           f"full {int(m_f.nobs)} - LR test invalid"}
    lr   = 2 * (m_f.llf - m_r.llf)
    df_d = len(cols_full) - len(cols_restricted)
    p    = 1 - chi2.cdf(lr, df_d)
    return {
        "N":           int(m_f.nobs),
        "LLF_restricted": round(m_r.llf, 2),
        "LLF_full":    round(m_f.llf, 2),
        "LR_stat":     round(lr, 3),
        "df":          df_d,
        "p":           round(p, 6),
        "reject H0":   "YES - full model is better" if p < 0.05 else "no",
    }


# ─── Main ──────────────────────────────────────────────────────────────────
def main():
    print(f"{'=' * 72}")
    print(f"DIAGNOSTICS for winning spec: min+rev+alone+age (7 vars)")
    print(f"{'=' * 72}\n")

    df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
    df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
    df_text = derive(df_text)
    print(f"Loaded: {len(df_text)} reviews with text, "
          f"{df_text.user_id.nunique()} reviewers\n")

    # 1. Baseline fits ───────────────────────────────────────────────────
    print("[1/5] Fitting winning spec and minimal baseline ...")
    m1_w, d1_w = fit_m1(df_text, WINNER)
    m2_w, d2_w = fit_m2(df_text, WINNER)
    m1_m, _    = fit_m1(df_text, MINIMAL)
    m2_m, _    = fit_m2(df_text, MINIMAL)

    fit_df = pd.DataFrame([
        fit_summary(m1_m, None, m2_m, d2_w, "minimal (4)"),
        fit_summary(m1_w, d1_w, m2_w, d2_w, "winner (7)"),
    ])
    fit_df.to_csv(OUT / "wd_fit_summary.csv", index=False, encoding="utf-8-sig")
    print("\n   FIT SUMMARY")
    print("   " + fit_df.to_string(index=False).replace("\n", "\n   "))

    # 2. Cross-validation ────────────────────────────────────────────────
    print("\n[2/5] Running 5-fold cross-validation grouped by reviewer ...")
    cv1 = cv_m1(df_text, WINNER)
    cv2 = cv_m2(df_text, WINNER)
    pd.DataFrame([cv1]).to_csv(OUT / "wd_m1_cv.csv", index=False,
                               encoding="utf-8-sig")
    pd.DataFrame([cv2]).to_csv(OUT / "wd_m2_cv.csv", index=False,
                               encoding="utf-8-sig")
    print("\n   M1 (Revisit) CV metrics:")
    for k, v in cv1.items():
        if isinstance(v, float):
            print(f"     {k:<32}  {v:>8.4f}")
        else:
            print(f"     {k:<32}  {v}")
    print("\n   M2 (Rating) CV metrics:")
    for k, v in cv2.items():
        if isinstance(v, float):
            print(f"     {k:<32}  {v:>8.4f}")
        else:
            print(f"     {k:<32}  {v}")

    # 3. Brant test (proportional-odds for M2) ───────────────────────────
    print("\n[3/5] Brant-style proportional-odds test for M2 ...")
    brant_df, brant_overall = brant_test(df_text, WINNER)
    brant_df.to_csv(OUT / "wd_brant.csv", encoding="utf-8-sig")
    print(f"\n   Per-variable proportional odds test:")
    print("   " + brant_df.to_string().replace("\n", "\n   "))
    print(f"\n   OVERALL Brant test (sum z^2):")
    print(f"     chi^2 = {brant_overall['chi2']:.3f}  df = {brant_overall['df']}  "
          f"p = {brant_overall['p']:.4f}")
    print(f"     violations: {brant_overall['violations']}/{brant_overall['total']} "
          f"variables with p < 0.05")
    verdict = ("PROPORTIONAL ODDS LIKELY VIOLATED - consider "
               "generalized-ordered logit or report as limitation"
               if brant_overall["p"] < 0.05
               else "PROPORTIONAL ODDS ASSUMPTION NOT REJECTED  (ok to use ordered logit)")
    print(f"     verdict: {verdict}")

    # 4. LR tests ────────────────────────────────────────────────────────
    print("\n[4/5] Likelihood-ratio test: minimal (4) vs winner (7) ...")
    lr_m1 = lr_test(df_text, MINIMAL, WINNER, fit_m1)
    lr_m2 = lr_test(df_text, MINIMAL, WINNER, fit_m2)
    lr_df = pd.DataFrame([{"model": "M1 Revisit", **lr_m1},
                          {"model": "M2 Rating",  **lr_m2}])
    lr_df.to_csv(OUT / "wd_lr_test.csv", index=False, encoding="utf-8-sig")
    print("\n   " + lr_df.to_string(index=False).replace("\n", "\n   "))

    # 5. Final written report ────────────────────────────────────────────
    print("\n[5/5] Writing printable report ...")
    lines = [
        "WORKSHOP MODEL DIAGNOSTICS",
        "=" * 72,
        f"Winning spec: min+rev+alone+age  ({len(WINNER)} vars)",
        f"Variables: {', '.join(WINNER)}",
        "",
        "1. FIT SUMMARY",
        "-" * 72,
        fit_df.to_string(index=False),
        "",
        "2. CROSS-VALIDATION (5-fold grouped by reviewer)",
        "-" * 72,
        "M1 Revisit:",
        *[f"  {k:<32}{v:>10.4f}" if isinstance(v, float) else f"  {k:<32}{v}"
          for k, v in cv1.items()],
        "",
        "M2 Rating:",
        *[f"  {k:<32}{v:>10.4f}" if isinstance(v, float) else f"  {k:<32}{v}"
          for k, v in cv2.items()],
        "",
        "3. BRANT-STYLE PROPORTIONAL-ODDS TEST (M2)",
        "-" * 72,
        brant_df.to_string(),
        "",
        f"Overall chi^2 = {brant_overall['chi2']:.3f}, "
        f"df = {brant_overall['df']}, p = {brant_overall['p']:.4f}",
        f"Variables violating PO (p<0.05): "
        f"{brant_overall['violations']}/{brant_overall['total']}",
        f"Verdict: {verdict}",
        "",
        "4. LIKELIHOOD-RATIO TEST (minimal vs winner)",
        "-" * 72,
        lr_df.to_string(index=False),
        "",
    ]
    (OUT / "wd_diagnostics_report.txt").write_text("\n".join(lines),
                                                   encoding="utf-8")

    print(f"\n{'=' * 72}")
    print(f"ALL diagnostics saved under: {OUT}")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()
