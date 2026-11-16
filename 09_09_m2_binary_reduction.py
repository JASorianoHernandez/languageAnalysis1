"""
09_09_m2_binary_reduction.py
Explore how much we can reduce M2 (binary logit P(5★)) without losing fit.

M1 is held fixed at 7 vars (binary logit, Revisit) and NOT re-estimated here —
we only vary M2's predictor set. For each M2 spec we report:
  - N, pseudo-R², AIC, BIC
  - # significant vars
  - Delta vs. full-7 baseline
  - Which vars kept, which dropped

Three families of reductions:
  SINGLE-DROP   7-var full minus one var at a time (7 specs)
  PAIRS         specific 5-var combos
  SMALL         4-var and 3-var curated specs
  MINIMAL       2-var and 1-var floors

Outputs: data/analysis/naver/workshop/m2_reduction/
  m2_reduction_summary.csv    all specs, metrics side by side
  m2_<key>_coefs.csv          per-spec coefficients
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
OUT = DIR / "workshop" / "m2_reduction"
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


# ─── Build specs ────────────────────────────────────────────────────────────
SPECS = {}

# Baseline (D's M2)
SPECS["M2_full7"] = {"family": "baseline", "vars": ALL7[:],
                     "name": "FULL 7 vars (D's M2)"}

# Single-drop (7 options)
for drop in ALL7:
    key = f"M2_drop_{drop}"
    SPECS[key] = {
        "family": "single-drop",
        "vars":   [v for v in ALL7 if v != drop],
        "name":   f"7 - {LABELS[drop]} (6 vars)",
    }

# 5-var specific pairs (interesting combos)
SPECS["M2_sig4+rev"] = {
    "family": "5-var",
    "vars":   ["waited", "is_tourist", "ln_user_followers",
               "sentiment", "ln_user_reviews"],
    "name":   "sig-core + ln(reviews)",
}
SPECS["M2_sig4+alone"] = {
    "family": "5-var",
    "vars":   ["waited", "is_tourist", "ln_user_followers",
               "sentiment", "comp_alone"],
    "name":   "sig-core + alone",
}
SPECS["M2_sig4+age"] = {
    "family": "5-var",
    "vars":   ["waited", "is_tourist", "ln_user_followers",
               "sentiment", "ln_review_age"],
    "name":   "sig-core + ln(age)",
}
SPECS["M2_no_sentiment_6"] = {
    "family": "5-var",
    "vars":   ["waited", "is_tourist", "ln_user_followers",
               "ln_user_reviews", "comp_alone", "ln_review_age"],
    "name":   "6 vars WITHOUT sentiment",
}

# 4-var specs
SPECS["M2_sig_only"] = {
    "family": "4-var",
    "vars":   ["waited", "is_tourist", "ln_user_followers", "sentiment"],
    "name":   "Only vars sig in M2 full (= E's M2)",
}
SPECS["M2_no_sent_4"] = {
    "family": "4-var",
    "vars":   ["waited", "is_tourist", "ln_user_followers", "ln_user_reviews"],
    "name":   "4 vars WITHOUT sentiment",
}

# 3-var specs
SPECS["M2_3_core"] = {
    "family": "3-var",
    "vars":   ["waited", "sentiment", "ln_user_followers"],
    "name":   "3 vars: service + text + reviewer",
}
SPECS["M2_3_no_sent"] = {
    "family": "3-var",
    "vars":   ["waited", "is_tourist", "ln_user_followers"],
    "name":   "3 vars: service + visit + reviewer (no sent)",
}

# 2-var floors
SPECS["M2_2_wait_sent"] = {
    "family": "minimum",
    "vars":   ["waited", "sentiment"],
    "name":   "2 vars: waited + sentiment",
}
SPECS["M2_1_sent"] = {
    "family": "minimum",
    "vars":   ["sentiment"],
    "name":   "1 var: sentiment only",
}
SPECS["M2_1_wait"] = {
    "family": "minimum",
    "vars":   ["waited"],
    "name":   "1 var: waited only",
}

# ─── Systematic enumeration: ALL combos keeping sentiment ───────────────────
# 6 non-sentiment variables -> 2^6 = 64 possible subsets to combine with sent.
# Family name encodes size: with_sent_<size>v  (size = 1..7, including sent).
OTHERS = [v for v in ALL7 if v != "sentiment"]        # 6 vars

SHORT = {
    "waited":            "wait",
    "is_tourist":        "tour",
    "ln_user_followers": "foll",
    "ln_user_reviews":   "revs",
    "comp_alone":        "alon",
    "ln_review_age":     "age",
}

for k in range(0, len(OTHERS) + 1):                   # 0..6 others
    for combo in combinations(OTHERS, k):
        size = k + 1                                  # sentiment counts
        if k == 0:
            key_tag = "only"
        else:
            key_tag = "_".join(SHORT[v] for v in combo)
        key = f"S_{size}v_sent+{key_tag}"
        if key in SPECS:                              # avoid duplicate
            continue
        other_labels = [LABELS[v] for v in combo]
        name = (f"sent + {k} others: {', '.join(other_labels)}"
                if combo else "sent only")
        SPECS[key] = {
            "family": f"with_sent_{size}v",
            "vars":   ["sentiment"] + list(combo),
            "name":   name,
        }
# At the end of this block, we have 64 extra specs covering every subset
# of the 6 non-sentiment variables combined with sentiment.


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


def tidy_binary(res):
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "p": res.pvalues})
    out = out[~out.index.str.startswith(("place_", "const"))]
    out["label"] = [LABELS.get(idx, idx) for idx in out.index]
    out["OR"]    = np.exp(out["coef"])
    out["sig"]   = pd.cut(out["p"], [-1, 0.001, 0.01, 0.05, 0.1, 1.1],
                          labels=["***", "**", "*", ".", ""])
    return out[["label", "coef", "OR", "se", "p", "sig"]]


def fit_m2_binary(data, cols):
    d = data.dropna(subset=["rating"]).reset_index(drop=True)
    d["five_star"] = (d["rating"] == 5).astype(int)
    d = varying_places(d, "five_star")
    m = sm.Logit(d["five_star"], design(d, cols)).fit(
        disp=False, maxiter=300,
        cov_type="cluster", cov_kwds=clusters(d))
    return m, d


# ─── Run ────────────────────────────────────────────────────────────────────
def main():
    df_all = pd.read_csv(DIR / "naver_dataset.csv", encoding="utf-8-sig")
    df_text = df_all[df_all["has_text"] == 1].reset_index(drop=True)
    df_text = derive(df_text)
    print(f"Loaded: {len(df_text)} reviews with text")
    print(f"Testing {len(SPECS)} M2 (binary P(5★)) specifications\n")

    # Baseline R² (used for delta calculation)
    baseline_r2 = None
    results = []
    for key, spec in SPECS.items():
        m, d = fit_m2_binary(df_text, spec["vars"])
        t = tidy_binary(m)
        t.round(4).to_csv(OUT / f"m2_{key}_coefs.csv", encoding="utf-8-sig")

        n_sig = int((t["p"] < 0.05).sum())
        r2 = m.prsquared
        if key == "M2_full7":
            baseline_r2 = r2
        delta = r2 - baseline_r2 if baseline_r2 is not None else np.nan
        delta_pct = 100 * delta / baseline_r2 if baseline_r2 else np.nan

        vars_sig = [t.loc[idx, "label"] for idx in t.index if t.loc[idx, "p"] < 0.05]
        print(f"[{key:<24s}] n={len(spec['vars']):>2}  "
              f"R²={r2:.4f}  Δ={delta:+.4f} ({delta_pct:+5.1f}%)  "
              f"AIC={m.aic:>7.1f}  sig={n_sig}/{len(spec['vars'])}  "
              f"[{', '.join(vars_sig)}]")

        results.append({
            "key":        key,
            "family":     spec["family"],
            "name":       spec["name"],
            "n_vars":     len(spec["vars"]),
            "N":          int(m.nobs),
            "R2":         round(r2, 4),
            "delta_R2":   round(delta, 4) if not np.isnan(delta) else "",
            "delta_pct":  round(delta_pct, 1) if not np.isnan(delta_pct) else "",
            "AIC":        round(m.aic, 1),
            "BIC":        round(m.bic, 1),
            "LLF":        round(m.llf, 2),
            "n_sig":      n_sig,
            "sig_vars":   "; ".join(vars_sig),
            "vars":       "; ".join(spec["vars"]),
        })

    summary = pd.DataFrame(results)
    summary["R2_per_var"] = summary["R2"] / summary["n_vars"]
    summary.to_csv(OUT / "m2_reduction_summary.csv", index=False,
                   encoding="utf-8-sig")

    print("\n" + "=" * 110)
    print(f"SUMMARY (baseline D's M2 = full 7 vars, R² = {baseline_r2:.4f})")
    print(f"Total specs tested: {len(summary)}")
    print("=" * 110)

    # ── Best spec at each size (the "efficiency frontier") ──────────────
    print("\n>>> EFFICIENCY FRONTIER: best R² at each number of variables <<<")
    frontier = (summary.sort_values("R2", ascending=False)
                       .drop_duplicates("n_vars")
                       .sort_values("n_vars"))
    print(frontier[["n_vars", "key", "R2", "delta_R2", "delta_pct",
                    "AIC", "n_sig", "sig_vars"]].to_string(index=False))

    # ── Top 15 overall by R² ───────────────────────────────────────────
    print("\n>>> TOP 15 OVERALL BY R² <<<")
    print(summary.sort_values("R2", ascending=False).head(15)[
        ["key", "n_vars", "R2", "delta_R2", "delta_pct", "AIC",
         "n_sig"]].to_string(index=False))

    # ── Best spec in each "with_sent" family ───────────────────────────
    print("\n>>> BEST SPEC PER FAMILY <<<")
    best_by_family = (summary.sort_values("R2", ascending=False)
                             .drop_duplicates("family")
                             .sort_values(["family"]))
    print(best_by_family[["family", "n_vars", "key", "R2", "delta_R2",
                          "AIC"]].to_string(index=False))

    # ── Smallest spec that keeps >=95% / >=90% / >=80% of baseline R² ──
    print("\n>>> SMALLEST SPEC THAT KEEPS AT LEAST X% OF BASELINE R² <<<")
    for threshold_pct in [95, 90, 80, 70]:
        target = baseline_r2 * threshold_pct / 100
        qualifying = summary[summary["R2"] >= target].sort_values("n_vars")
        if not qualifying.empty:
            r = qualifying.iloc[0]
            print(f"  >= {threshold_pct}% of baseline (R² >= {target:.4f}): "
                  f"{r['key']}  ({r['n_vars']} vars, R²={r['R2']:.4f}, "
                  f"loses {100 - 100 * r['R2'] / baseline_r2:.1f}%)")

    # ── Top 10 by efficiency (R² per variable) ─────────────────────────
    print("\n>>> TOP 10 BY R²-PER-VARIABLE (efficiency) <<<")
    print(summary.sort_values("R2_per_var", ascending=False).head(10)[
        ["key", "n_vars", "R2", "R2_per_var"]].to_string(index=False))

    print(f"\nSaved: {OUT}/m2_reduction_summary.csv  "
          f"and {len(SPECS)} coefficient files")


if __name__ == "__main__":
    main()
