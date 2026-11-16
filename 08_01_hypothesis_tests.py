"""
08_01_hypothesis_tests.py
Hofstede-based hypothesis tests: domestic (KO) vs foreign (EN) reviewers.

Design follows Chen et al. (2024): each hypothesis has a bilingual target
dictionary (hypothesis_dictionaries.py), and every test uses all reviews of
each language (review = unit).
  Test A (intensity): share of target tokens per review, one-sided Mann-Whitney U
  Test B (presence):  does the review mention the topic at all, 2x2 chi-square
                      (one-sided via the sign of the difference; Fisher if expected < 5)
H5 uses sentiment (-1 to 1): Test A on the score, Test B on the share of positive reviews
(> 0.05, the "positive" label of 03_01_analyze.py).
Each test family is Holm-corrected separately.

Sensitivity run: the same tests without ambiguous terms. Terms come from
dictionary_precision.csv (07_02_dictionary_check.py) or a default list.

Outputs (data/analysis/):
  hypothesis_tests.csv              one row per hypothesis (full dictionaries)
  hypothesis_tests_sensitivity.csv  full vs reduced dictionaries
  hypothesis_by_place.csv           descriptive means per place (no tests, n too small)
  hypothesis_matched_terms.csv      most frequent matched terms
  figures/13_hypothesis_tests.png

Run (base env):  python 08_01_hypothesis_tests.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")
from collections import Counter

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, chi2_contingency, fisher_exact
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

from hypothesis_dictionaries import (
    HYPOTHESES, ANALYSIS, PLACE_EN, build_matcher, load_corpus,
    load_exclusions, describe_exclusions,
)

FIGS = ANALYSIS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

RNG = np.random.default_rng(42)
N_BOOT = 5000
ALPHA = 0.05
PALETTE = {"ko": "#2563EB", "en": "#DC2626"}
WORD_HYPOTHESES = [h for h in HYPOTHESES if h.get("metric") != "sentiment"]


# ── features ─────────────────────────────────────────────────────────────────
def compute_features(df, exclusions=None):
    out = df.copy()
    matched_rows = []
    for h in WORD_HYPOTHESES:
        excl = (exclusions or {}).get(h["id"], {})
        matchers = {lang: build_matcher(h[lang], excl.get(lang, [])) for lang in ("ko", "en")}
        shares, hits_any = [], []
        counters = {"ko": Counter(), "en": Counter()}
        for toks, lang in zip(out["tokens"], out["language"]):
            hits = [t for t in toks if matchers[lang](t)]
            counters[lang].update(hits)
            shares.append(100 * len(hits) / len(toks))
            hits_any.append(len(hits) > 0)
        out[h["id"]] = shares
        out[h["id"] + "_any"] = hits_any
        for lang in ("ko", "en"):
            for term, c in counters[lang].most_common(10):
                matched_rows.append({"hypothesis": h["id"], "language": lang,
                                     "term": term, "count": c})
    out["sentiment_any"] = np.where(out["sentiment"].isna(), np.nan, out["sentiment"] > 0.05)
    return out, matched_rows


# ── tests ────────────────────────────────────────────────────────────────────
def boot_mean_ci(x):
    idx = RNG.integers(0, len(x), (N_BOOT, len(x)))
    return np.percentile(x[idx].mean(axis=1), [2.5, 97.5])


def boot_diff_ci(a, b):
    ia = RNG.integers(0, len(a), (N_BOOT, len(a)))
    ib = RNG.integers(0, len(b), (N_BOOT, len(b)))
    return np.percentile(a[ia].mean(axis=1) - b[ib].mean(axis=1), [2.5, 97.5])


def holm(pvals):
    order = np.argsort(pvals)
    adj = np.empty(len(pvals))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(pvals) - rank) * pvals[i])
        adj[i] = min(running, 1.0)
    return adj


def presence_test(ko_any, en_any, direction):
    """2x2 test on mention / no mention; returns one-sided p in both directions."""
    table = np.array([[ko_any.sum(), len(ko_any) - ko_any.sum()],
                      [en_any.sum(), len(en_any) - en_any.sum()]])
    chi2, p_two, _, expected = chi2_contingency(table, correction=False)
    if expected.min() < 5:
        alt = "greater" if direction == "ko>en" else "less"
        _, p_one = fisher_exact(table, alternative=alt)
        _, p_rev = fisher_exact(table, alternative="less" if alt == "greater" else "greater")
        method = "Fisher"
    else:
        diff = ko_any.mean() - en_any.mean()
        expected_sign = 1 if direction == "ko>en" else -1
        p_one = p_two / 2 if np.sign(diff) == expected_sign else 1 - p_two / 2
        p_rev = 1 - p_one
        method = "chi-square"
    a, b = table[0] + 0.5
    c, d = table[1] + 0.5
    return {
        "chi2": chi2, "phi": np.sqrt(chi2 / table.sum()),
        "odds_ratio_ko_en": (a * d) / (b * c),
        "presence_p": p_one, "presence_p_reverse": p_rev, "presence_method": method,
    }


def verdict(p_holm, p_rev_holm):
    return np.select([p_holm < ALPHA, p_rev_holm < ALPHA],
                     ["Supported", "Opposite direction"], default="Not supported")


def run_tests(feat):
    rows, group_ci = [], {}
    for h in HYPOTHESES:
        col = "sentiment" if h.get("metric") == "sentiment" else h["id"]
        ko = feat.loc[feat.language == "ko", col].dropna().to_numpy(float)
        en = feat.loc[feat.language == "en", col].dropna().to_numpy(float)
        hi, lo = (ko, en) if h["direction"] == "ko>en" else (en, ko)

        u, p = mannwhitneyu(hi, lo, alternative="greater")
        _, p_rev = mannwhitneyu(lo, hi, alternative="greater")
        ci_low, ci_high = boot_diff_ci(ko, en)

        ko_any = feat.loc[feat.language == "ko", col + "_any"].dropna().to_numpy(float)
        en_any = feat.loc[feat.language == "en", col + "_any"].dropna().to_numpy(float)
        group_ci[h["id"]] = {
            "ko": boot_mean_ci(ko), "en": boot_mean_ci(en),
            "ko_any": 100 * boot_mean_ci(ko_any), "en_any": 100 * boot_mean_ci(en_any),
        }

        rows.append({
            "hypothesis": h["id"], "dimension": h["dimension"], "label": h["label"],
            "statement": h["statement"], "direction": h["direction"],
            "metric": "sentiment (-1 to 1)" if col == "sentiment" else "% target tokens",
            "presence_metric": "% positive reviews" if col == "sentiment" else "% reviews mentioning",
            "n_ko": len(ko), "n_en": len(en),
            "ko_mean": ko.mean(), "en_mean": en.mean(),
            "diff_ko_en": ko.mean() - en.mean(), "ci95_low": ci_low, "ci95_high": ci_high,
            "U": u, "effect_r": 2 * u / (len(hi) * len(lo)) - 1,
            "p_value": p, "p_reverse": p_rev,
            "ko_presence_pct": 100 * ko_any.mean(), "en_presence_pct": 100 * en_any.mean(),
            **presence_test(ko_any, en_any, h["direction"]),
        })

    res = pd.DataFrame(rows)
    res["p_holm"] = holm(res["p_value"].to_numpy())
    res["p_reverse_holm"] = holm(res["p_reverse"].to_numpy())
    res["result"] = verdict(res["p_holm"], res["p_reverse_holm"])
    res["presence_p_holm"] = holm(res["presence_p"].to_numpy())
    res["presence_p_reverse_holm"] = holm(res["presence_p_reverse"].to_numpy())
    res["presence_result"] = verdict(res["presence_p_holm"], res["presence_p_reverse_holm"])
    return res, group_ci


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."


# ── main run ─────────────────────────────────────────────────────────────────
df = load_corpus()
print(f"Reviews: {len(df)}  (KO={sum(df.language == 'ko')}, EN={sum(df.language == 'en')})")

feat, matched_rows = compute_features(df)
res, group_ci = run_tests(feat)

res.to_csv(ANALYSIS / "hypothesis_tests.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(matched_rows).to_csv(ANALYSIS / "hypothesis_matched_terms.csv",
                                  index=False, encoding="utf-8-sig")

value_cols = [h["id"] for h in WORD_HYPOTHESES] + ["sentiment"]
by_place = feat.groupby(["place", "language"])[value_cols].mean().round(3).reset_index()
by_place.insert(1, "place_en", by_place["place"].map(PLACE_EN))
by_place.to_csv(ANALYSIS / "hypothesis_by_place.csv", index=False, encoding="utf-8-sig")

print("\n" + "=" * 92)
print("TEST A  Intensity: % target tokens per review (H5: sentiment score), Mann-Whitney U")
print("-" * 92)
print(f"{'H':<4}{'Dimension':<23}{'Label':<24}{'KO':>8}{'EN':>8}{'p(Holm)':>10}{'r':>7}   Result")
print("-" * 92)
for _, r in res.iterrows():
    print(f"{r.hypothesis:<4}{r.dimension:<23}{r.label:<24}{r.ko_mean:>8.3f}{r.en_mean:>8.3f}"
          f"{r.p_holm:>10.4f}{r.effect_r:>7.2f}   {r.result} {stars(r.p_holm)}")
print("=" * 92)

print("\n" + "=" * 92)
print("TEST B  Presence: % reviews mentioning the topic (H5: % positive reviews), chi-square")
print("-" * 92)
print(f"{'H':<4}{'Dimension':<23}{'Label':<24}{'KO %':>7}{'EN %':>7}{'chi2':>7}"
      f"{'p(Holm)':>9}{'phi':>6}{'OR':>6}   Result")
print("-" * 92)
for _, r in res.iterrows():
    print(f"{r.hypothesis:<4}{r.dimension:<23}{r.label:<24}{r.ko_presence_pct:>7.1f}"
          f"{r.en_presence_pct:>7.1f}{r.chi2:>7.2f}{r.presence_p_holm:>9.4f}{r.phi:>6.2f}"
          f"{r.odds_ratio_ko_en:>6.2f}   {r.presence_result} {stars(r.presence_p_holm)}")
print("=" * 92)
print("OR = odds ratio KO vs EN (>1: Korean reviews more likely to mention the topic)")

print("\nMost frequent matched terms (check the dictionaries):")
mt = pd.DataFrame(matched_rows)
for h in WORD_HYPOTHESES:
    for lang in ("ko", "en"):
        sub = mt[(mt.hypothesis == h["id"]) & (mt.language == lang)].head(6)
        terms = ", ".join(f"{t}({c})" for t, c in zip(sub.term, sub["count"]))
        print(f"  {h['id']} {lang.upper()}: {terms}")


# ── sensitivity run ──────────────────────────────────────────────────────────
exclusions, source = load_exclusions()
res_red, _ = run_tests(compute_features(df, exclusions)[0])

keep = ["hypothesis", "label", "ko_presence_pct", "en_presence_pct", "presence_p_holm",
        "presence_result", "ko_mean", "en_mean", "p_holm", "result"]
sens = res[keep].merge(res_red[keep], on=["hypothesis", "label"], suffixes=("_full", "_reduced"))
sens.insert(2, "excluded_terms", [describe_exclusions({h: exclusions.get(h, {})})
                                  for h in sens["hypothesis"]])
sens["robust"] = np.where(
    sens["presence_result_full"] == sens["presence_result_reduced"], "yes", "NO")
sens.to_csv(ANALYSIS / "hypothesis_tests_sensitivity.csv", index=False, encoding="utf-8-sig")

print("\n" + "=" * 92)
print("SENSITIVITY  Test B with vs without ambiguous terms")
print(f"Source: {source}")
print(f"Excluded: {describe_exclusions(exclusions)}")
print("-" * 92)
print(f"{'H':<4}{'Label':<24}{'Full KO/EN %':>15}{'p(Holm)':>9}"
      f"{'Reduced KO/EN %':>18}{'p(Holm)':>9}   Robust")
print("-" * 92)
for _, r in sens.iterrows():
    full = f"{r.ko_presence_pct_full:.1f}/{r.en_presence_pct_full:.1f}"
    red = f"{r.ko_presence_pct_reduced:.1f}/{r.en_presence_pct_reduced:.1f}"
    print(f"{r.hypothesis:<4}{r.label:<24}{full:>15}{r.presence_p_holm_full:>9.4f}"
          f"{red:>18}{r.presence_p_holm_reduced:>9.4f}   {r.robust}")
print("=" * 92)


# ── figure (full dictionaries) ───────────────────────────────────────────────
def draw_panel(ax, means, cis, ylabel, verdict_text, p_holm):
    yerr = [[m - c[0] for m, c in zip(means, cis)], [c[1] - m for m, c in zip(means, cis)]]
    ax.bar([0, 1], means, 0.6, yerr=yerr, capsize=5,
           color=[PALETTE["ko"], PALETTE["en"]], alpha=0.85)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Korean", "English"])
    ax.set_ylabel(ylabel, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    top = max(c[1] for c in cis)
    ax.set_ylim(0, top * 1.28)
    ax.text(0.5, top * 1.14, f"{verdict_text}\np = {p_holm:.3f} {stars(p_holm)}",
            ha="center", va="center", fontsize=8.5)


fig, axes = plt.subplots(2, len(HYPOTHESES), figsize=(17, 9))
for j, (h, (_, r)) in enumerate(zip(HYPOTHESES, res.iterrows())):
    expected = "KO > EN" if h["direction"] == "ko>en" else "EN > KO"
    ci = group_ci[h["id"]]
    draw_panel(axes[0, j], [r.ko_mean, r.en_mean], [ci["ko"], ci["en"]],
               r.metric, f"{expected}: {r.result}", r.p_holm)
    draw_panel(axes[1, j], [r.ko_presence_pct, r.en_presence_pct], [ci["ko_any"], ci["en_any"]],
               r.presence_metric, f"{expected}: {r.presence_result}", r.presence_p_holm)
    axes[0, j].set_title(f"{h['id']}  {h['label']}\n({h['dimension']})",
                         fontsize=10.5, fontweight="bold")

axes[0, 0].annotate("A  Intensity\n(Mann-Whitney U)", xy=(-0.42, 0.5), xycoords="axes fraction",
                    rotation=90, ha="center", va="center", fontsize=11, fontweight="bold")
axes[1, 0].annotate("B  Presence\n(chi-square)", xy=(-0.42, 0.5), xycoords="axes fraction",
                    rotation=90, ha="center", va="center", fontsize=11, fontweight="bold")
fig.suptitle("Hofstede-based hypothesis tests: domestic vs foreign reviewers "
             "(one-sided, Holm-corrected per test family; bars = mean ± 95% bootstrap CI)",
             fontsize=11.5, fontweight="bold")
fig.tight_layout()
fig.savefig(FIGS / "13_hypothesis_tests.png", dpi=300, bbox_inches="tight")
plt.close()

print(f"\nSaved: {ANALYSIS / 'hypothesis_tests.csv'}")
print(f"Saved: {ANALYSIS / 'hypothesis_tests_sensitivity.csv'}")
print(f"Saved: {ANALYSIS / 'hypothesis_by_place.csv'}")
print(f"Saved: {ANALYSIS / 'hypothesis_matched_terms.csv'}")
print(f"Saved: {FIGS / '13_hypothesis_tests.png'}")
