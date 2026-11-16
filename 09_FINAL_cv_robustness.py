"""
09_FINAL_cv_robustness.py
Generate the two remaining assets for the paper:

  1. Cross-validation detailed table (per-fold AUC/Brier/Accuracy for M1,
     per-fold exact and within-+-1 accuracy for M2).
  2. Robustness checks: M1 and M2 with alternative predictor sets.
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
from sklearn.metrics import (roc_auc_score, brier_score_loss, accuracy_score,
                             balanced_accuracy_score, f1_score)

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop" / "FINAL"
OUT.mkdir(parents=True, exist_ok=True)

M1_COLS = ["waited", "is_tourist", "sentiment", "comp_alone",
           "ln_user_reviews", "ln_user_followers"]
M2_COLS = ["sentiment", "waited", "ln_user_followers",
           "ln_photos", "season_autumn"]


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


# Load data
df = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
df_text = df[df["has_text"] == 1].reset_index(drop=True).copy()
df_text = derive(df_text)
d1 = varying_places(df_text, "revisit")

d2 = df_text.dropna(subset=["rating"]).reset_index(drop=True)
d2["rating_3cat"] = np.select(
    [d2["rating"] <= 3.5,
     (d2["rating"] >= 4.0) & (d2["rating"] <= 4.5),
     d2["rating"] == 5.0], [0, 1, 2], default=np.nan)
d2 = d2.dropna(subset=["rating_3cat"]).reset_index(drop=True)
d2["five_star"] = (d2["rating"] == 5.0).astype(int)
d2 = varying_places(d2, "five_star")
d2["mn_y"] = (2 - d2["rating_3cat"].astype(int)).astype(int)

# ─── 1. Cross-validation fold-by-fold ──────────────────────────────────────
print("=== CROSS-VALIDATION (5-fold grouped by reviewer) ===")
folds = GroupKFold(n_splits=5)

# M1 CV
X1 = design(d1, M1_COLS)
y1 = d1["revisit"].to_numpy()
cv_m1 = []
for fold_idx, (tr, te) in enumerate(folds.split(X1, y1, groups=d1["user_id"]), 1):
    try:
        res = sm.Logit(y1[tr], X1.iloc[tr]).fit(disp=False, maxiter=300)
        p_te = res.predict(X1.iloc[te])
    except np.linalg.LinAlgError:
        from sklearn.linear_model import LogisticRegression
        mdl = LogisticRegression(C=1e3, max_iter=5000).fit(
            X1.iloc[tr].drop(columns="const"), y1[tr])
        p_te = mdl.predict_proba(X1.iloc[te].drop(columns="const"))[:, 1]
    hat = (p_te >= 0.5).astype(int)
    cv_m1.append({
        "Fold":          fold_idx,
        "N_test":        len(te),
        "AUC":           round(roc_auc_score(y1[te], p_te), 3),
        "Brier":         round(brier_score_loss(y1[te], p_te), 3),
        "Accuracy":      round(accuracy_score(y1[te], hat), 3),
        "Bal. accuracy": round(balanced_accuracy_score(y1[te], hat), 3),
        "F1":            round(f1_score(y1[te], hat), 3),
    })
cv_m1_df = pd.DataFrame(cv_m1)
# Add average row
avg = cv_m1_df.drop(columns="Fold").mean(numeric_only=True).round(3)
cv_m1_df.loc[len(cv_m1_df)] = ["AVG", int(avg["N_test"]) * 5,
                                avg["AUC"], avg["Brier"], avg["Accuracy"],
                                avg["Bal. accuracy"], avg["F1"]]
cv_m1_df.to_csv(OUT / "cv_m1_detailed.csv", index=False, encoding="utf-8-sig")
print("\nM1 Revisit (binary logit):")
print(cv_m1_df.to_string(index=False))

# M2 CV
X2 = design(d2, M2_COLS)
y2 = d2["mn_y"].to_numpy()
cv_m2 = []
for fold_idx, (tr, te) in enumerate(folds.split(X2, y2, groups=d2["user_id"]), 1):
    try:
        res = sm.MNLogit(y2[tr], X2.iloc[tr]).fit(
            method="bfgs", disp=False, maxiter=2000)
        probs = np.asarray(res.predict(X2.iloc[te]))
        yhat_te = probs.argmax(axis=1)
    except Exception:
        yhat_te = np.full(len(te), int(np.bincount(y2[tr]).argmax()))
    cv_m2.append({
        "Fold":                fold_idx,
        "N_test":              len(te),
        "Exact accuracy":      round((yhat_te == y2[te]).mean(), 3),
        "Within +-1 accuracy": round((np.abs(yhat_te - y2[te]) <= 1).mean(), 3),
    })
cv_m2_df = pd.DataFrame(cv_m2)
avg2 = cv_m2_df.drop(columns="Fold").mean(numeric_only=True).round(3)
cv_m2_df.loc[len(cv_m2_df)] = ["AVG", int(avg2["N_test"]) * 5,
                                avg2["Exact accuracy"],
                                avg2["Within +-1 accuracy"]]
cv_m2_df.to_csv(OUT / "cv_m2_detailed.csv", index=False, encoding="utf-8-sig")
print("\nM2 Rating (multinomial logit):")
print(cv_m2_df.to_string(index=False))


# ─── 2. Robustness checks ─────────────────────────────────────────────────
print("\n\n=== ROBUSTNESS CHECKS ===")


def fit_m1(cols):
    m = sm.Logit(d1["revisit"], design(d1, cols)).fit(
        disp=False, maxiter=300, cov_type="cluster",
        cov_kwds=clusters(d1))
    return m


def fit_m2(cols):
    m = sm.MNLogit(d2["mn_y"], design(d2, cols)).fit(
        method="bfgs", disp=False, maxiter=2000,
        cov_type="cluster", cov_kwds=clusters(d2))
    return m


# M1 robustness: add ln_review_age (dropped in main spec); also try without comp_alone
m1_alts = {
    "Main (6 vars)":                     M1_COLS,
    "+ ln(review_age) (7)":              M1_COLS + ["ln_review_age"],
    "- comp_alone (5)":                  [v for v in M1_COLS if v != "comp_alone"],
    "- sentiment (5)":                   [v for v in M1_COLS if v != "sentiment"],
    "+ season_autumn (7)":               M1_COLS + ["season_autumn"],
}
m1_rows = []
for name, cols in m1_alts.items():
    m = fit_m1(cols)
    m1_rows.append({
        "Specification": name,
        "N predictors":  len(cols),
        "pseudo-R2":     round(m.prsquared, 4),
        "AIC":           round(m.aic, 1),
        "BIC":           round(m.bic, 1),
    })
m1_rob = pd.DataFrame(m1_rows)
m1_rob.to_csv(OUT / "robustness_m1.csv", index=False, encoding="utf-8-sig")
print("\nM1 Revisit robustness alternatives:")
print(m1_rob.to_string(index=False))


# M2 robustness: without autumn, with ln_review_age, etc.
m2_alts = {
    "Main (5 vars)":                     M2_COLS,
    "- season_autumn (4)":               [v for v in M2_COLS if v != "season_autumn"],
    "+ ln(review_age) (6)":              M2_COLS + ["ln_review_age"],
    "+ is_tourist (6)":                  M2_COLS + ["is_tourist"],
    "+ comp_alone (6)":                  M2_COLS + ["comp_alone"],
    "- ln_photos (4)":                   [v for v in M2_COLS if v != "ln_photos"],
}
m2_rows = []
for name, cols in m2_alts.items():
    m = fit_m2(cols)
    m2_rows.append({
        "Specification": name,
        "N predictors":  len(cols),
        "pseudo-R2":     round(m.prsquared, 4),
        "AIC":           round(m.aic, 1),
        "BIC":           round(m.bic, 1),
    })
m2_rob = pd.DataFrame(m2_rows)
m2_rob.to_csv(OUT / "robustness_m2.csv", index=False, encoding="utf-8-sig")
print("\nM2 Rating robustness alternatives:")
print(m2_rob.to_string(index=False))

print(f"\nAll CV + robustness outputs saved under: {OUT}")
