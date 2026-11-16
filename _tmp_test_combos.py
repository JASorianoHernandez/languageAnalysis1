import sys
sys.stdout.reconfigure(encoding="utf-8")
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import statsmodels.api as sm

df = pd.read_csv("data/analysis/naver/naver_dataset.csv", encoding="utf-8-sig")
df_text = df[df["has_text"] == 1].reset_index(drop=True).copy()
df_text["is_tourist"] = df_text["purp_travel"].astype(float)

d2 = df_text.dropna(subset=["rating"]).reset_index(drop=True)
d2["rating_3cat"] = np.select(
    [d2["rating"] <= 3.5,
     (d2["rating"] >= 4.0) & (d2["rating"] <= 4.5),
     d2["rating"] == 5.0],
    [0, 1, 2], default=np.nan)
d2 = d2.dropna(subset=["rating_3cat"]).reset_index(drop=True)
d2["mn_y"] = (2 - d2["rating_3cat"].astype(int)).astype(int)
d1 = df_text.copy()


def fit_m1(cols):
    places = pd.get_dummies(d1["place"], prefix="place", drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([d1[cols].astype(float), places], axis=1))
    try:
        return sm.Logit(d1["revisit"], X).fit(
            disp=False, maxiter=300, cov_type="cluster",
            cov_kwds={"groups": pd.factorize(d1["user_id"])[0]})
    except Exception:
        return None


def fit_m2(cols):
    places = pd.get_dummies(d2["place"], prefix="place", drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([d2[cols].astype(float), places], axis=1))
    try:
        return sm.MNLogit(d2["mn_y"], X).fit(
            method="bfgs", disp=False, maxiter=2000, cov_type="cluster",
            cov_kwds={"groups": pd.factorize(d2["user_id"])[0]})
    except Exception:
        return None


def test_combo(name, m1_cols, m2_cols):
    shared = set(m1_cols) & set(m2_cols)
    m1 = fit_m1(m1_cols)
    m2 = fit_m2(m2_cols)
    m1_sig = sum(1 for v in m1_cols
                 if m1 is not None and v in m1.params.index
                 and m1.pvalues[v] < 0.05) if m1 is not None else 0
    m2_sig = 0
    if m2 is not None:
        for v in m2_cols:
            if v not in m2.params.index:
                continue
            pm = m2.pvalues.loc[v, m2.params.columns[0]]
            pl = m2.pvalues.loc[v, m2.params.columns[1]]
            if (pm < 0.05) or (pl < 0.05):
                m2_sig += 1
    print(f"\n{'=' * 90}")
    print(f"{name}")
    print(f"  M1 ({len(m1_cols)}): {m1_cols}")
    print(f"  M2 ({len(m2_cols)}): {m2_cols}")
    print(f"  Shared ({len(shared)}): {sorted(shared)}")
    if m1 is not None:
        print(f"  M1: R2={m1.prsquared:.4f}  AIC={m1.aic:.1f}  "
              f"sig={m1_sig}/{len(m1_cols)}")
    if m2 is not None:
        print(f"  M2: R2={m2.prsquared:.4f}  AIC={m2.aic:.1f}  "
              f"sig={m2_sig}/{len(m2_cols)}")
    return {"name": name,
            "m1_n": len(m1_cols), "m2_n": len(m2_cols),
            "shared": len(shared),
            "m1_r2": m1.prsquared if m1 else None,
            "m2_r2": m2.prsquared if m2 else None,
            "m1_aic": m1.aic if m1 else None,
            "m2_aic": m2.aic if m2 else None,
            "m1_sig": m1_sig, "m2_sig": m2_sig}


results = []

print("\n" + "=" * 90)
print("SCENARIO A: sentiment IS one of the 2 shared vars")
print("=" * 90)

results.append(test_combo(
    "A1  Share {sent, waited}       | M1=5",
    ["sentiment", "waited", "ln_user_followers",
     "ln_user_reviews", "comp_alone"],
    ["sentiment", "waited", "season_autumn", "ln_photos"]))

results.append(test_combo(
    "A2  Share {sent, waited}       | M1=6 (+is_tourist)",
    ["sentiment", "waited", "ln_user_followers",
     "ln_user_reviews", "comp_alone", "is_tourist"],
    ["sentiment", "waited", "season_autumn", "ln_photos"]))

results.append(test_combo(
    "A3  Share {sent, waited}       | M1=6 (+ln_review_age)",
    ["sentiment", "waited", "ln_user_followers",
     "ln_user_reviews", "comp_alone", "ln_review_age"],
    ["sentiment", "waited", "season_autumn", "ln_photos"]))

results.append(test_combo(
    "A4  Share {sent, ln(foll)}     | M1=5",
    ["sentiment", "ln_user_followers", "waited",
     "ln_user_reviews", "comp_alone"],
    ["sentiment", "ln_user_followers", "season_autumn", "ln_photos"]))

results.append(test_combo(
    "A5  Share {sent, ln(foll)}     | M1=6 (+ln_review_age)",
    ["sentiment", "ln_user_followers", "waited",
     "ln_user_reviews", "comp_alone", "ln_review_age"],
    ["sentiment", "ln_user_followers", "season_autumn", "ln_photos"]))

results.append(test_combo(
    "A6  Share {sent, is_tourist}   | M1=6 (max variety on M1)",
    ["sentiment", "is_tourist", "waited", "ln_user_followers",
     "ln_user_reviews", "comp_alone"],
    ["sentiment", "is_tourist", "season_autumn", "ln_photos"]))

results.append(test_combo(
    "A7  Share {sent, ln(age)}      | M1=6",
    ["sentiment", "ln_review_age", "waited", "is_tourist",
     "ln_user_followers", "comp_alone"],
    ["sentiment", "ln_review_age", "season_autumn", "ln_photos"]))

print("\n" + "=" * 90)
print("SCENARIO B: sentiment is M2-only (shared vars are others)")
print("=" * 90)

results.append(test_combo(
    "B1  Share {wait, ln(foll)}     | sentiment M2-only",
    ["waited", "ln_user_followers", "is_tourist",
     "ln_user_reviews", "comp_alone"],
    ["waited", "ln_user_followers", "sentiment", "season_autumn"]))

results.append(test_combo(
    "B2  Share {wait, is_tourist}   | sentiment M2-only",
    ["waited", "is_tourist", "ln_user_followers",
     "ln_user_reviews", "comp_alone"],
    ["waited", "is_tourist", "sentiment", "season_autumn"]))

results.append(test_combo(
    "B3  Share {ln(foll), is_tour}  | sentiment M2-only",
    ["ln_user_followers", "is_tourist", "waited",
     "ln_user_reviews", "comp_alone"],
    ["ln_user_followers", "is_tourist", "sentiment", "season_autumn"]))

results.append(test_combo(
    "B4  Share {wait, ln(age)}      | sentiment M2-only",
    ["waited", "ln_review_age", "is_tourist",
     "ln_user_followers", "ln_user_reviews"],
    ["waited", "ln_review_age", "sentiment", "season_autumn"]))

print("\n" + "=" * 90)
print("SUMMARY SORTED BY M1_R2 x M2_R2 (joint fit)")
print("=" * 90)
print(f"{'spec':<48s}{'M1_n':>5}{'M1_R2':>8}{'M2_n':>5}{'M2_R2':>8}"
      f"{'joint':>10}{'allsig':>10}")
for r in sorted(results,
                key=lambda x: -(x["m1_r2"] * x["m2_r2"]
                                if x["m1_r2"] and x["m2_r2"] else 0)):
    if r["m1_r2"] is None:
        continue
    prod = r["m1_r2"] * r["m2_r2"]
    m1_full = r["m1_sig"] == r["m1_n"]
    m2_full = r["m2_sig"] == r["m2_n"]
    marker = ("Yes" if m1_full and m2_full
              else "M1" if m1_full else "M2" if m2_full else "-")
    print(f"{r['name'][:48]:<48s}{r['m1_n']:>5}{r['m1_r2']:>8.4f}"
          f"{r['m2_n']:>5}{r['m2_r2']:>8.4f}{prod:>10.5f}{marker:>10}")
