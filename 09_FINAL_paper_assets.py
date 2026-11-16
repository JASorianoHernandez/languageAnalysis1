"""
09_FINAL_paper_assets.py
Generate all remaining assets for the workshop paper (English):

  1. Descriptive statistics table (8 variables, M1 + M2 samples)
  2. Correlation matrix + VIF
  3. Model-fit summary table
  4. Forest plot — M1 (binary logit)
  5. Forest plot — M2 (multinomial, 2 panels: MID vs TOP, LOW vs TOP)

All outputs saved to: data/analysis/naver/workshop/FINAL/
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

DIR = Path("data/analysis/naver")
OUT = DIR / "workshop" / "FINAL"
FIGS = OUT / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

M1_COLS = ["waited", "is_tourist", "sentiment", "comp_alone",
           "ln_user_reviews", "ln_user_followers"]
M2_COLS = ["sentiment", "waited", "ln_user_followers",
           "ln_photos", "season_autumn"]
ALL_COLS = ["waited", "is_tourist", "sentiment", "comp_alone",
            "ln_user_reviews", "ln_user_followers",
            "ln_photos", "season_autumn"]

LABELS = {
    "waited":              "Waited",
    "is_tourist":          "Tourist",
    "sentiment":           "Sentiment",
    "comp_alone":          "Alone",
    "ln_user_reviews":     "ln(1+reviews)",
    "ln_user_followers":   "ln(1+followers)",
    "ln_photos":           "ln(1+photos)",
    "season_autumn":       "Season: autumn",
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


# ─── Load data ─────────────────────────────────────────────────────────────
df = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
df_text = df[df["has_text"] == 1].reset_index(drop=True).copy()
df_text = derive(df_text)
d1 = varying_places(df_text, "revisit")

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
d2["mn_y"] = (2 - d2["rating_3cat"].astype(int)).astype(int)


# ─── 1. Descriptive statistics table ───────────────────────────────────────
rows = []
# Outcomes
rows.append({"Variable": "Revisit (0/1)", "N (M1)": len(d1),
             "Mean": d1["revisit"].mean(), "SD": d1["revisit"].std(),
             "Min": 0, "Max": 1, "N (M2)": "—"})
rows.append({"Variable": "Five-star (0/1)", "N (M1)": "—",
             "Mean": d2["five_star"].mean(), "SD": d2["five_star"].std(),
             "Min": 0, "Max": 1, "N (M2)": len(d2)})
# Rating 3-cat distribution
for cls, name in [(0, "Rating cat: LOW"), (1, "Rating cat: MID"), (2, "Rating cat: TOP")]:
    pct = (d2["rating_3cat"] == cls).mean()
    rows.append({"Variable": name, "N (M1)": "—",
                 "Mean": pct, "SD": "—", "Min": 0, "Max": 1,
                 "N (M2)": int((d2["rating_3cat"] == cls).sum())})
# Predictors
for v in ALL_COLS:
    row = {"Variable": LABELS[v]}
    row["N (M1)"] = int(d1[v].notna().sum()) if v in d1.columns else "—"
    row["Mean"] = d1[v].mean() if v in d1.columns else d2[v].mean()
    row["SD"] = d1[v].std() if v in d1.columns else d2[v].std()
    row["Min"] = d1[v].min() if v in d1.columns else d2[v].min()
    row["Max"] = d1[v].max() if v in d1.columns else d2[v].max()
    row["N (M2)"] = int(d2[v].notna().sum()) if v in d2.columns else "—"
    rows.append(row)

desc = pd.DataFrame(rows)
# Round numeric columns
for col in ["Mean", "SD", "Min", "Max"]:
    desc[col] = desc[col].apply(lambda x: round(x, 3) if isinstance(x, (int, float)) else x)
desc.to_csv(OUT / "descriptive_stats.csv", index=False, encoding="utf-8-sig")
print("=== DESCRIPTIVE STATISTICS ===")
print(desc.to_string(index=False))


# ─── 2. Correlation matrix (M2 shared sample) + VIFs ──────────────────────
corr = d2[ALL_COLS].corr().round(3)
corr.to_csv(OUT / "correlation_matrix.csv", encoding="utf-8-sig")
print("\n=== CORRELATION MATRIX (M2 sample, N=4044) ===")
print(corr.to_string())

# VIFs on all 8 vars together
X_vif = sm.add_constant(d2[ALL_COLS].astype(float))
vif_rows = []
for i, v in enumerate(ALL_COLS):
    v_val = variance_inflation_factor(X_vif.values, i + 1)
    vif_rows.append({"Variable": LABELS[v], "VIF": round(v_val, 2)})
vif = pd.DataFrame(vif_rows)
vif.to_csv(OUT / "vif.csv", index=False, encoding="utf-8-sig")
print("\n=== VARIANCE INFLATION FACTORS ===")
print(vif.to_string(index=False))


# ─── 3. Model-fit summary ─────────────────────────────────────────────────
m1 = sm.Logit(d1["revisit"], design(d1, M1_COLS)).fit(
    disp=False, maxiter=300, cov_type="cluster", cov_kwds=clusters(d1))
m2 = sm.MNLogit(d2["mn_y"], design(d2, M2_COLS)).fit(
    method="bfgs", disp=False, maxiter=2000,
    cov_type="cluster", cov_kwds=clusters(d2))

# McFadden R² is prsquared for both; AIC/BIC directly
fit_summary = pd.DataFrame([
    {"Statistic": "Model", "M1 Revisit": "Binary logit",
     "M2 Rating": "Multinomial logit"},
    {"Statistic": "Outcome", "M1 Revisit": "Revisit (0/1)",
     "M2 Rating": "Rating category (LOW / MID / TOP)"},
    {"Statistic": "Reference category",
     "M1 Revisit": "no revisit (0)", "M2 Rating": "TOP (5★)"},
    {"Statistic": "N observations", "M1 Revisit": f"{int(m1.nobs):,}",
     "M2 Rating": f"{int(m2.nobs):,}"},
    {"Statistic": "Predictors", "M1 Revisit": 6, "M2 Rating": 5},
    {"Statistic": "Place fixed effects", "M1 Revisit": 28, "M2 Rating": 28},
    {"Statistic": "pseudo-R²", "M1 Revisit": round(m1.prsquared, 4),
     "M2 Rating": round(m2.prsquared, 4)},
    {"Statistic": "AIC", "M1 Revisit": round(m1.aic, 1),
     "M2 Rating": round(m2.aic, 1)},
    {"Statistic": "BIC", "M1 Revisit": round(m1.bic, 1),
     "M2 Rating": round(m2.bic, 1)},
    {"Statistic": "Log-likelihood", "M1 Revisit": round(m1.llf, 2),
     "M2 Rating": round(m2.llf, 2)},
    {"Statistic": "AUC (M1) / Exact acc. (M2)",
     "M1 Revisit": "0.80 (CV)", "M2 Rating": "0.77 (CV)"},
    {"Statistic": "Within-±1 accuracy (M2)",
     "M1 Revisit": "—", "M2 Rating": "0.95"},
])
fit_summary.to_csv(OUT / "fit_summary.csv", index=False, encoding="utf-8-sig")
print("\n=== MODEL FIT SUMMARY ===")
print(fit_summary.to_string(index=False))


# ─── 4. Forest plot — M1 Revisit ──────────────────────────────────────────
def forest(ax, labels, ors, cis_low, cis_high, p_values, title, xlabel):
    y = np.arange(len(labels))[::-1]
    colors = ["#2563EB" if p < 0.05 else "#9CA3AF" for p in p_values]
    ax.hlines(y, cis_low[::-1], cis_high[::-1], colors=colors, linewidth=1.4)
    ax.scatter(ors[::-1], y, c=colors, zorder=3, s=28)
    ax.axvline(1, color="#111827", lw=0.8, ls="--")
    ax.set_xscale("log")
    all_vals = list(cis_low) + list(cis_high) + list(ors)
    xlo = max(0.02, min(all_vals) / 1.3)
    xhi = max(all_vals) * 1.3
    ticks = [x for x in (0.03, 0.1, 0.25, 0.5, 1, 2, 4, 8, 16) if xlo <= x <= xhi]
    ax.set_xticks(ticks); ax.set_xticklabels([f"{t:g}" for t in ticks])
    ax.minorticks_off()
    ax.set_yticks(y); ax.set_yticklabels(labels[::-1], fontsize=9)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
    ax.spines[["top", "right"]].set_visible(False)


# M1 forest
m1_data = []
for v in M1_COLS:
    b = m1.params[v]; se = m1.bse[v]; p = m1.pvalues[v]
    m1_data.append((LABELS[v], np.exp(b), np.exp(b - 1.96 * se),
                    np.exp(b + 1.96 * se), p))
m1_data = list(zip(*m1_data))
fig, ax = plt.subplots(figsize=(7, 2.6))
forest(ax, list(m1_data[0]), np.array(m1_data[1]),
       np.array(m1_data[2]), np.array(m1_data[3]), m1_data[4],
       "Model 1: Revisit (binary logit, 6 predictors)",
       "Odds ratio (log scale; >1 = higher odds of revisit)")
plt.tight_layout()
plt.savefig(FIGS / "forest_m1.png", dpi=300, bbox_inches="tight")
plt.close()
print(f"\nSaved: {FIGS / 'forest_m1.png'}")


# M2 forest — 2 panels (MID vs TOP, LOW vs TOP)
fig, axes = plt.subplots(1, 2, figsize=(12, 2.6), sharey=True)
for ax, cat_idx, cat_name in [(axes[0], 0, "MID vs TOP"),
                               (axes[1], 1, "LOW vs TOP")]:
    col = m2.params.columns[cat_idx]
    rows_mn = []
    for v in M2_COLS:
        b = m2.params.loc[v, col]
        se = m2.bse.loc[v, col]
        p = m2.pvalues.loc[v, col]
        rows_mn.append((LABELS[v], np.exp(b),
                        np.exp(b - 1.96 * se), np.exp(b + 1.96 * se), p))
    rows_mn = list(zip(*rows_mn))
    forest(ax, list(rows_mn[0]), np.array(rows_mn[1]),
           np.array(rows_mn[2]), np.array(rows_mn[3]), rows_mn[4],
           f"Model 2: {cat_name}",
           "Odds ratio (log scale; vs TOP)")
plt.tight_layout()
plt.savefig(FIGS / "forest_m2.png", dpi=300, bbox_inches="tight")
plt.close()
print(f"Saved: {FIGS / 'forest_m2.png'}")

print(f"\nAll paper assets saved under: {OUT}")
