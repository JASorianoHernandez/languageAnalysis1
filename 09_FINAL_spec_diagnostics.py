"""
09_FINAL_spec_diagnostics.py
Final-spec runner for the workshop paper:

  M1 Revisit (binary logit, 6 vars):
      waited, is_tourist, sentiment, comp_alone, ln(reviews), ln(followers)

  M2 Rating (multinomial logit, 5 vars, Y = {LOW, MID, TOP} base = TOP):
      sentiment, waited, ln(followers), ln(photos), season_autumn

Both with place fixed effects (28 dummies) and SE clustered by reviewer.

Produces:
  - Full coefficient tables (M1 + M2)
  - Pseudo-R2, AIC, BIC
  - Confusion matrices (M1: 2x2, M2: 3x3)
  - M1: AUC + Brier + accuracy metrics
  - M2: exact accuracy + within-category accuracy
  - 5-fold cross-validation grouped by reviewer

Outputs: data/analysis/naver/workshop/FINAL/
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (confusion_matrix, roc_auc_score, brier_score_loss,
                             log_loss, accuracy_score, balanced_accuracy_score,
                             precision_score, recall_score, f1_score)

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop" / "FINAL"
OUT.mkdir(parents=True, exist_ok=True)

M1_COLS = ["waited", "is_tourist", "sentiment", "comp_alone",
           "ln_user_reviews", "ln_user_followers"]
M2_COLS = ["sentiment", "waited", "ln_user_followers",
           "ln_photos", "season_autumn"]

LABELS = {
    "waited": "Waited", "is_tourist": "Tourist",
    "sentiment": "Sentiment", "comp_alone": "Alone",
    "ln_user_reviews": "ln(1+reviews)",
    "ln_user_followers": "ln(1+followers)",
    "ln_photos": "ln(1+photos)",
    "season_autumn": "Season: autumn",
}


# ─── Helpers ───────────────────────────────────────────────────────────────
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


def tidy_binary(res, cols):
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "p": res.pvalues})
    out = out.loc[cols]
    out["label"] = [LABELS.get(idx, idx) for idx in out.index]
    out["OR"] = np.exp(out["coef"])
    out["ci_low"] = np.exp(out["coef"] - 1.96 * out["se"])
    out["ci_high"] = np.exp(out["coef"] + 1.96 * out["se"])
    out["sig"] = pd.cut(out["p"], [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                        labels=["***", "**", "*", ".", ""])
    return out[["label", "coef", "OR", "ci_low", "ci_high",
                "se", "p", "sig"]]


# ─── Load data ─────────────────────────────────────────────────────────────
df = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
df_text = df[df["has_text"] == 1].reset_index(drop=True).copy()
df_text["is_tourist"] = df_text["purp_travel"].astype(float)

# M1 data (all text reviews)
d1 = varying_places(df_text, "revisit")

# M2 data (text + rating + varying)
d2 = df_text.dropna(subset=["rating"]).reset_index(drop=True)
d2["rating_3cat"] = np.select(
    [d2["rating"] <= 3.5,
     (d2["rating"] >= 4.0) & (d2["rating"] <= 4.5),
     d2["rating"] == 5.0],
    [0, 1, 2], default=np.nan,
)
d2 = d2.dropna(subset=["rating_3cat"]).reset_index(drop=True)
d2["five_star"] = (d2["rating"] == 5.0).astype(int)
d2 = varying_places(d2, "five_star")
# Multinomial: TOP=0, MID=1, LOW=2
d2["mn_y"] = (2 - d2["rating_3cat"].astype(int)).astype(int)

print("=" * 85)
print("FINAL SPEC — DIAGNOSTICS")
print("=" * 85)
print(f"M1 sample: {len(d1)} reviews with text, "
      f"{d1['user_id'].nunique()} reviewers")
print(f"M2 sample: {len(d2)} reviews with rating, "
      f"{d2['user_id'].nunique()} reviewers")
print(f"M2 rating distribution: "
      f"LOW={int((d2['rating_3cat']==0).sum())}, "
      f"MID={int((d2['rating_3cat']==1).sum())}, "
      f"TOP={int((d2['rating_3cat']==2).sum())}")

# ───────────────────────────────────────────────────────────────────────────
# M1 Revisit — binary logit
# ───────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 85)
print("M1 REVISIT (binary logit, 6 vars)")
print("=" * 85)
m1 = sm.Logit(d1["revisit"], design(d1, M1_COLS)).fit(
    disp=False, maxiter=300, cov_type="cluster", cov_kwds=clusters(d1))

t1 = tidy_binary(m1, M1_COLS)
t1.round(4).to_csv(OUT / "M1_coefficients.csv", encoding="utf-8-sig")
print(f"\nN = {int(m1.nobs)}  |  pseudo-R² = {m1.prsquared:.4f}  |  "
      f"AIC = {m1.aic:.1f}  |  BIC = {m1.bic:.1f}")
print(t1.to_string())

# M1 Confusion matrix (at 0.5 threshold)
y_true1 = d1["revisit"].to_numpy()
p1 = m1.predict(design(d1, M1_COLS))
yhat1 = (p1 >= 0.5).astype(int)
cm1 = confusion_matrix(y_true1, yhat1)
cm1_df = pd.DataFrame(cm1, index=["Actual_0", "Actual_1"],
                      columns=["Pred_0", "Pred_1"])
cm1_df.to_csv(OUT / "M1_confusion_matrix.csv", encoding="utf-8-sig")
print(f"\nM1 CONFUSION MATRIX (threshold = 0.5):")
print(cm1_df.to_string())
print(f"  Accuracy:          {accuracy_score(y_true1, yhat1):.4f}")
print(f"  Baseline (all 0):  {1 - y_true1.mean():.4f}")
print(f"  Balanced accuracy: {balanced_accuracy_score(y_true1, yhat1):.4f}")
print(f"  Precision:         {precision_score(y_true1, yhat1, zero_division=0):.4f}")
print(f"  Recall:            {recall_score(y_true1, yhat1):.4f}")
print(f"  F1:                {f1_score(y_true1, yhat1):.4f}")
print(f"  AUC:               {roc_auc_score(y_true1, p1):.4f}")
print(f"  Brier score:       {brier_score_loss(y_true1, p1):.4f}")
print(f"  Log-loss:          {log_loss(y_true1, p1):.4f}")

# ───────────────────────────────────────────────────────────────────────────
# M2 Rating — multinomial logit
# ───────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 85)
print("M2 RATING (multinomial logit, 5 vars, base = TOP)")
print("=" * 85)
X2 = design(d2, M2_COLS)
m2 = sm.MNLogit(d2["mn_y"], X2).fit(
    method="bfgs", disp=False, maxiter=2000,
    cov_type="cluster", cov_kwds=clusters(d2))

print(f"\nN = {int(m2.nobs)}  |  pseudo-R² = {m2.prsquared:.4f}  |  "
      f"AIC = {m2.aic:.1f}  |  BIC = {m2.bic:.1f}")

# M2 coefficients: 2 columns (MID vs TOP, LOW vs TOP)
rows = []
for cat_idx, cat_name in enumerate(["MID vs TOP", "LOW vs TOP"]):
    col = m2.params.columns[cat_idx]
    for v in M2_COLS:
        b = m2.params.loc[v, col]
        p = m2.pvalues.loc[v, col]
        s = m2.bse.loc[v, col]
        rows.append({
            "comparison": cat_name,
            "variable":   v,
            "label":      LABELS.get(v, v),
            "coef":       round(b, 4),
            "OR":         round(np.exp(b), 2),
            "ci_low":     round(np.exp(b - 1.96 * s), 2),
            "ci_high":    round(np.exp(b + 1.96 * s), 2),
            "se":         round(s, 4),
            "p":          round(p, 4),
            "sig": ("***" if p < 0.001 else "**" if p < 0.01 else
                    "*" if p < 0.05 else "." if p < 0.1 else ""),
        })
m2_df = pd.DataFrame(rows)
m2_df.to_csv(OUT / "M2_coefficients.csv", index=False, encoding="utf-8-sig")

for cat in ["MID vs TOP", "LOW vs TOP"]:
    print(f"\n  >>> {cat} <<<")
    sub = m2_df[m2_df["comparison"] == cat]
    print(sub[["label", "coef", "OR", "ci_low", "ci_high",
               "p", "sig"]].to_string(index=False))

# M2 Confusion matrix (3x3)
probs2 = np.asarray(m2.predict(X2))              # (N, 3) probs for TOP/MID/LOW (base is 0 = TOP)
yhat2 = probs2.argmax(axis=1)
y_true2 = d2["mn_y"].to_numpy()
cm2 = confusion_matrix(y_true2, yhat2)
cm2_df = pd.DataFrame(cm2,
                      index=["Actual_TOP(5★)", "Actual_MID(4-4.5)", "Actual_LOW(≤3.5)"],
                      columns=["Pred_TOP", "Pred_MID", "Pred_LOW"])
cm2_df.to_csv(OUT / "M2_confusion_matrix.csv", encoding="utf-8-sig")
print(f"\nM2 CONFUSION MATRIX:")
print(cm2_df.to_string())
exact_acc2 = (yhat2 == y_true2).mean()
within1_acc = (np.abs(yhat2 - y_true2) <= 1).mean()
# Baseline: always predict TOP (modal class)
baseline_mode = int(np.bincount(y_true2).argmax())
print(f"  Exact accuracy:            {exact_acc2:.4f}")
print(f"  Baseline (always predict mode): {(y_true2 == baseline_mode).mean():.4f}")
print(f"  Within ±1 accuracy:        {within1_acc:.4f}")

# Per-class recall
print(f"\n  Per-class recall:")
for cls, name in enumerate(["TOP (5★)", "MID (4-4.5)", "LOW (≤3.5)"]):
    mask = (y_true2 == cls)
    rec = (yhat2[mask] == cls).mean() if mask.sum() > 0 else 0
    print(f"    {name:<16}  recall = {rec:.4f}  (n = {int(mask.sum())})")

# ───────────────────────────────────────────────────────────────────────────
# Brant test note
# ───────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 85)
print("BRANT TEST — NOTE")
print("=" * 85)
print("""
The Brant test assesses the proportional-odds assumption of ORDERED LOGIT
models. Our M2 is a MULTINOMIAL LOGIT (categories treated as unordered),
which does NOT assume proportional odds. Therefore the Brant test does not
apply to this specification.

Earlier we had an ordered-logit M2 whose Brant test failed (p < 0.01) for
sentiment and ln(review_age). Switching to multinomial resolves this issue
by design — each comparison (MID vs TOP, LOW vs TOP) estimates its own
coefficient for each predictor, no equality constraint imposed.
""")

# ───────────────────────────────────────────────────────────────────────────
# Cross-validation
# ───────────────────────────────────────────────────────────────────────────
print("=" * 85)
print("5-FOLD CROSS-VALIDATION (grouped by reviewer)")
print("=" * 85)
folds = GroupKFold(n_splits=5)

# M1 CV
X1_full = design(d1, M1_COLS)
y1_full = d1["revisit"].to_numpy()
p1_cv = np.zeros(len(y1_full))
for tr, te in folds.split(X1_full, y1_full, groups=d1["user_id"]):
    try:
        res = sm.Logit(y1_full[tr], X1_full.iloc[tr]).fit(
            disp=False, maxiter=300)
        p1_cv[te] = res.predict(X1_full.iloc[te])
    except np.linalg.LinAlgError:
        from sklearn.linear_model import LogisticRegression
        mdl = LogisticRegression(C=1e3, max_iter=5000).fit(
            X1_full.iloc[tr].drop(columns="const"), y1_full[tr])
        p1_cv[te] = mdl.predict_proba(
            X1_full.iloc[te].drop(columns="const"))[:, 1]
yhat1_cv = (p1_cv >= 0.5).astype(int)
m1_cv = {
    "AUC":                      roc_auc_score(y1_full, p1_cv),
    "Brier":                    brier_score_loss(y1_full, p1_cv),
    "Log-loss":                 log_loss(y1_full, p1_cv),
    "Accuracy @0.5":            accuracy_score(y1_full, yhat1_cv),
    "Baseline (always 0)":      1 - y1_full.mean(),
    "Balanced accuracy":        balanced_accuracy_score(y1_full, yhat1_cv),
    "Precision (revisit=1)":    precision_score(y1_full, yhat1_cv, zero_division=0),
    "Recall (revisit=1)":       recall_score(y1_full, yhat1_cv),
    "F1 (revisit=1)":           f1_score(y1_full, yhat1_cv),
}
pd.DataFrame([m1_cv]).to_csv(OUT / "M1_cv_metrics.csv",
                              index=False, encoding="utf-8-sig")
print("\nM1 Revisit CV metrics:")
for k, v in m1_cv.items():
    print(f"  {k:<28s}  {v:.4f}")

# M2 CV
X2_full = design(d2, M2_COLS)
y2_full = d2["mn_y"].to_numpy()
yhat2_cv = np.zeros(len(y2_full), dtype=int)
for tr, te in folds.split(X2_full, y2_full, groups=d2["user_id"]):
    try:
        res = sm.MNLogit(y2_full[tr], X2_full.iloc[tr]).fit(
            method="bfgs", disp=False, maxiter=2000)
        probs = np.asarray(res.predict(X2_full.iloc[te]))
        yhat2_cv[te] = probs.argmax(axis=1)
    except Exception:
        yhat2_cv[te] = int(np.bincount(y2_full[tr]).argmax())
m2_cv = {
    "Exact accuracy":           (yhat2_cv == y2_full).mean(),
    "Baseline (always mode)":   (y2_full == int(np.bincount(y2_full).argmax())).mean(),
    "Within ±1 accuracy":       (np.abs(yhat2_cv - y2_full) <= 1).mean(),
}
pd.DataFrame([m2_cv]).to_csv(OUT / "M2_cv_metrics.csv",
                              index=False, encoding="utf-8-sig")
print("\nM2 Rating CV metrics:")
for k, v in m2_cv.items():
    print(f"  {k:<28s}  {v:.4f}")

print(f"\nAll outputs saved under: {OUT}")
