"""
07_02_dictionary_check.py
Manual validation of the hypothesis dictionaries via keyword-in-context (KWIC).

Step 1  python 07_02_dictionary_check.py
        -> data/analysis/dictionary_check.csv  (up to 20 random contexts per matched term)
Step 2  open the CSV in Excel, write 1 (valid) or 0 (not valid) in the "valid" column,
        save as "CSV UTF-8"
Step 3  python 07_02_dictionary_check.py --score
        -> data/analysis/dictionary_precision.csv  (precision per term)
Step 4  python 08_01_hypothesis_tests.py
        -> the sensitivity run now drops terms below the precision threshold

Use --force with step 1 to overwrite an existing (possibly already coded) check file.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import sys

import numpy as np
import pandas as pd

from hypothesis_dictionaries import (
    HYPOTHESES, CHECK_FILE, PRECISION_FILE, PRECISION_THRESHOLD, MIN_REVIEWED,
    build_matcher, load_corpus, read_csv_any,
)

SAMPLE_PER_TERM = 20
WINDOW = 45
RNG = np.random.default_rng(42)


def kwic(text, start, end):
    left = text[max(0, start - WINDOW):start]
    right = text[end:end + WINDOW]
    snippet = f"{'...' if start > WINDOW else ''}{left}[{text[start:end]}]{right}"
    snippet += "..." if end + WINDOW < len(text) else ""
    return " ".join(snippet.split())


def export():
    if CHECK_FILE.exists() and "--force" not in sys.argv:
        print(f"{CHECK_FILE} already exists and may contain your coding.")
        print("Run with --score to compute precision, or --force to overwrite it.")
        return

    df = load_corpus()
    rows = []
    for h in HYPOTHESES:
        if h.get("metric") == "sentiment":
            continue
        for lang in ("ko", "en"):
            match = build_matcher(h[lang])
            hits = [(form, i, s, e)
                    for i, spans in df.loc[df.language == lang, "spans"].items()
                    for form, s, e in spans if match(form)]
            by_term = {}
            for hit in hits:
                by_term.setdefault(hit[0], []).append(hit)
            for term, occ in by_term.items():
                pick = RNG.choice(len(occ), size=min(SAMPLE_PER_TERM, len(occ)), replace=False)
                for k in sorted(pick):
                    _, i, s, e = occ[k]
                    rows.append({
                        "hypothesis": h["id"], "label": h["label"], "language": lang,
                        "term": term, "term_total": len(occ), "place": df.at[i, "place"],
                        "context": kwic(str(df.at[i, "text"]), s, e), "valid": "",
                    })

    out = pd.DataFrame(rows).sort_values(
        ["hypothesis", "language", "term_total", "term"], ascending=[True, True, False, True])
    out.to_csv(CHECK_FILE, index=False, encoding="utf-8-sig")

    summary = out.groupby(["hypothesis", "language"]).agg(
        terms=("term", "nunique"), contexts=("term", "size"))
    print(summary.to_string())
    print(f"\nSaved {len(out)} contexts to {CHECK_FILE}")
    print("Next: fill the 'valid' column with 1/0, save as CSV UTF-8, then run with --score")


def score():
    if not CHECK_FILE.exists():
        print(f"{CHECK_FILE} not found. Run without arguments first.")
        return
    chk = read_csv_any(CHECK_FILE)
    chk["valid"] = pd.to_numeric(chk["valid"], errors="coerce")
    coded = chk.dropna(subset=["valid"])
    if coded.empty:
        print("No coded rows yet: fill the 'valid' column with 1 or 0.")
        return

    prec = coded.groupby(["hypothesis", "language", "term"]).agg(
        term_total=("term_total", "first"), n_reviewed=("valid", "size"),
        n_valid=("valid", "sum")).reset_index()
    prec["precision"] = (prec["n_valid"] / prec["n_reviewed"]).round(3)
    prec["action"] = np.where(
        prec["n_reviewed"] < MIN_REVIEWED, "keep (too few reviewed)",
        np.where(prec["precision"] < PRECISION_THRESHOLD, "EXCLUDE", "keep"))
    prec = prec.sort_values(["hypothesis", "language", "term_total"], ascending=[True, True, False])
    prec.to_csv(PRECISION_FILE, index=False, encoding="utf-8-sig")

    print(f"Coded rows: {len(coded)} / {len(chk)}\n")
    print(prec.to_string(index=False))

    overall = coded.groupby(["hypothesis", "language"])["valid"].mean().unstack().round(3)
    print("\nOverall dictionary precision (share of valid contexts):")
    print(overall.to_string())
    print(f"\nSaved {PRECISION_FILE}")
    print("Next: run 08_01_hypothesis_tests.py; terms marked EXCLUDE are dropped in the sensitivity run.")


if __name__ == "__main__":
    score() if "--score" in sys.argv else export()
