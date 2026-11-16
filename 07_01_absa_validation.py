"""
07_01_absa_validation.py
Validate the LLM-based ABSA (06_llm_analysis.py) against blind manual coding.

Step 1  python 07_01_absa_validation.py
        -> data/analysis/absa_validation.csv  (50 reviews, 25 KO + 25 EN, empty label columns)
        -> data/analysis/absa_codebook.md     (coding rules)
        The file contains no model output, sentiment score or rating (blind coding).
        Reviews used in the prompt pilot (absa_pilot.csv) are excluded.
Step 2  open the CSV in Excel, write -1 / 0 / 1 in the five aspect columns,
        save as "CSV UTF-8"
Step 3  python 07_01_absa_validation.py --score
        -> data/analysis/absa_validation_agreement.csv
        Cohen's kappa and accuracy per aspect and language, model vs human.

Use --force with step 1 to overwrite an existing (possibly already coded) file.

Run (base env).
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

from hypothesis_dictionaries import read_csv_any

ANALYSIS = Path("data/analysis")
VALIDATION_FILE = ANALYSIS / "absa_validation.csv"
CODEBOOK_FILE = ANALYSIS / "absa_codebook.md"
AGREEMENT_FILE = ANALYSIS / "absa_validation_agreement.csv"
ASPECTS = ["historical_cultural", "accessibility", "crowding", "food", "visual_photo"]
N_PER_LANG = 25
SEED = 2026

CODEBOOK = """# ABSA coding rules

For each review and each aspect write **1** (positive), **-1** (negative) or **0**
(not mentioned, or mentioned without a positive/negative judgement).
Judge only what the review says, not what you know about the place.
If one aspect gets both praise and criticism, choose the dominant one; if balanced, use 0.

| Aspect | Covers | Examples |
|---|---|---|
| historical_cultural | history, heritage, traditional culture, architecture, cultural activities (hanbok, ceremonies, history tours) | "조선의 역사를 느낄 수 있어요" = 1 |
| accessibility | getting there, public transport, parking, opening hours, tickets, reservations, facilities, convenience | "주차가 너무 힘들어요" = -1 ; "close to the subway" = 1 |
| crowding | crowd level and comfort | "사람이 너무 많아요", "waited an hour" = -1 ; "quiet on weekdays", "not crowded" = 1 |
| food | food, drinks, restaurants, street food, cafes, food prices | "빈대떡이 맛있어요" = 1 ; "overpriced food" = -1 |
| visual_photo | scenery, views, night views, beauty, decorations, photo spots | "야경이 예뻐요" = 1 |

**Crowding rule:** a lively or bustling atmosphere described only as fun ("활기차요",
"vibrant", "불야성") is **0**, not +1 or -1. Code crowding only when the review judges the
crowd level or comfort itself.

Save the file as **CSV UTF-8** when you finish.
"""


def export():
    if VALIDATION_FILE.exists() and "--force" not in sys.argv:
        print(f"{VALIDATION_FILE} already exists and may contain your coding.")
        print("Run with --score to compute agreement, or --force to overwrite it.")
        return

    corpus = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
    pilot_path = ANALYSIS / "absa_pilot.csv"
    if pilot_path.exists():
        pilot_texts = set(read_csv_any(pilot_path)["text"])
        corpus = corpus[~corpus["text"].isin(pilot_texts)]

    picks = []
    for lang in ("ko", "en"):
        sub = corpus[corpus.language == lang].sample(frac=1, random_state=SEED)
        per_place = -(-N_PER_LANG // sub["place"].nunique())
        picks.append(sub.groupby("place").head(per_place).head(N_PER_LANG))
    sample = pd.concat(picks).sample(frac=1, random_state=SEED).reset_index(drop=True)

    out = pd.DataFrame({"id": range(1, len(sample) + 1), "language": sample["language"],
                        "place": sample["place"], "text": sample["text"]})
    for a in ASPECTS:
        out[a] = ""
    out.to_csv(VALIDATION_FILE, index=False, encoding="utf-8-sig")
    CODEBOOK_FILE.write_text(CODEBOOK, encoding="utf-8")

    print(out.groupby(["language", "place"]).size().unstack(0).to_string())
    print(f"\nSaved {len(out)} reviews to {VALIDATION_FILE}")
    print(f"Coding rules: {CODEBOOK_FILE}")


def score():
    if not VALIDATION_FILE.exists():
        print(f"{VALIDATION_FILE} not found. Run without arguments first.")
        return
    model_path = ANALYSIS / "absa_results.csv"
    human = read_csv_any(VALIDATION_FILE)
    model = read_csv_any(model_path)

    for a in ASPECTS:
        human[a] = pd.to_numeric(human[a], errors="coerce")
    coded = human.dropna(subset=ASPECTS)
    bad = coded[~coded[ASPECTS].isin([-1, 0, 1]).all(axis=1)]
    if len(bad):
        print(f"Rows with values other than -1/0/1 (fix them): ids {bad['id'].tolist()}")
        return
    if coded.empty:
        print("No fully coded rows yet: fill all five aspect columns with -1, 0 or 1.")
        return
    print(f"Coded reviews: {len(coded)} / {len(human)}")

    merged = coded.merge(model[["text", "language", *ASPECTS]], on=["text", "language"],
                         how="left", suffixes=("_human", "_model"))
    missing = merged[[f"{a}_model" for a in ASPECTS]].isna().any(axis=1).sum()
    if missing:
        print(f"Warning: {missing} reviews have no valid model answer; they are skipped per aspect.")

    rows = []
    for lang in ("ko", "en", "all"):
        sub = merged if lang == "all" else merged[merged.language == lang]
        for a in ASPECTS:
            pair = sub[[f"{a}_human", f"{a}_model"]].dropna()
            h, m = pair.iloc[:, 0].astype(int), pair.iloc[:, 1].astype(int)
            if len(pair) == 0:
                continue
            same_single_label = h.nunique() == 1 and m.nunique() == 1 and h.iloc[0] == m.iloc[0]
            rows.append({
                "language": lang, "aspect": a, "n": len(pair),
                "accuracy": (h == m).mean(),
                "kappa": 1.0 if same_single_label else cohen_kappa_score(h, m, labels=[-1, 0, 1]),
                "kappa_mention": 1.0 if same_single_label else
                    cohen_kappa_score(h != 0, m != 0),
                "human_mentions": int((h != 0).sum()), "model_mentions": int((m != 0).sum()),
            })
    agree = pd.DataFrame(rows).round(3)
    agree.to_csv(AGREEMENT_FILE, index=False, encoding="utf-8-sig")

    print("\nAgreement model vs human (kappa: >0.80 almost perfect, 0.61-0.80 substantial,"
          " 0.41-0.60 moderate, <0.40 weak)\n")
    print(agree.to_string(index=False))
    print("\nkappa = agreement on -1/0/1; kappa_mention = agreement on whether the aspect is mentioned")
    print(f"\nSaved {AGREEMENT_FILE}")


if __name__ == "__main__":
    score() if "--score" in sys.argv else export()
