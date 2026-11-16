"""
run_pipeline.py
Run the cross-cultural branch (02_cc -> 08_01) then the Naver-only branch
(02_naver -> 09_02) in order, each step in its own environment. See places.json
and README.md's stage table for the full numbering, shared across both
branches, and which stage each script belongs to.
Scraping (01_01 Naver, 01_02 Google Maps) is not included: it is run manually,
one place at a time.

Each run gets its own timestamped folder, logs/pipeline/<YYYYMMDD_HHMM>/<step>.log,
so older runs are never overwritten; the run stops at the first failing step.

Usage (any env):
  python run_pipeline.py                  all steps (~75 min, two LLM steps on GPU)
  python run_pipeline.py --skip-llm       skip the two 06_llm_analysis steps (~15 min)
  python run_pipeline.py --from 09        start at the first step whose script starts with "09"
  python run_pipeline.py --list           show the steps and exit
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE = r"C:\Users\crono\anaconda3\python.exe"
GPU = r"C:\Users\crono\anaconda3\envs\faiss-gpu\python.exe"
LOGS = Path("logs/pipeline")

STEPS = [
    ("02_cc_build_corpus.py", [], BASE, "Balanced, deduplicated KO/EN corpus"),
    ("03_01_analyze.py", [], BASE, "Sentiment, LDA, TF-IDF, TTR"),
    ("03_02_lda_k_selection.py", [], BASE, "Coherence / perplexity by K"),
    ("04_01_visualize.py", [], BASE, "Figures, Mann-Whitney, analysis_data.json"),
    ("04_02_geo_bubble.py", [], BASE, "Geographic bubble maps"),
    ("05_01_advanced_nlp.py", [], GPU, "Embeddings, cross-lingual similarity, motivation"),
    ("06_llm_analysis.py", [], GPU, "ABSA + summaries, 7B 4-bit (~20 min)"),
    ("07_01_absa_validation.py", ["--score"], BASE, "ABSA vs manual coding (if coded)"),
    ("07_02_dictionary_check.py", ["--score"], BASE, "Dictionary precision from KWIC coding"),
    ("08_01_hypothesis_tests.py", [], BASE, "Hofstede hypothesis tests + sensitivity"),
    ("02_naver_build_dataset.py", [], BASE, "Korean-only dataset + sentiment"),
    ("06_llm_analysis.py", ["--naver"], GPU, "ABSA on Korean-only dataset (~40 min)"),
    ("09_01_naver_models.py", [], BASE, "Revisit and keyword-diversity models"),
    ("09_02_rating_checks.py", [], BASE, "Star ratings: sentiment validation, H5, revisit"),
]


def label(script, args):
    return script + (" " + " ".join(args) if args else "")


def main():
    if "--list" in sys.argv:
        for i, (script, args, py, desc) in enumerate(STEPS, 1):
            env = "gpu " if py == GPU else "base"
            print(f"{i:>2}. [{env}] {label(script, args):<36} {desc}")
        return

    steps = STEPS
    if "--from" in sys.argv:
        prefix = sys.argv[sys.argv.index("--from") + 1]
        start = next(i for i, s in enumerate(STEPS) if s[0].startswith(prefix))
        steps = STEPS[start:]
    if "--skip-llm" in sys.argv:
        steps = [s for s in steps if s[0] != "06_llm_analysis.py"]

    run_id = datetime.now().strftime("%Y%m%d_%H%M")
    run_logs = LOGS / run_id
    run_logs.mkdir(parents=True, exist_ok=True)
    print(f"Run folder: {run_logs}")

    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    t_all = time.time()
    for i, (script, args, py, desc) in enumerate(steps, 1):
        name = label(script, args)
        log = run_logs / (name.replace(" --", "_").replace(".py", "") + ".log")
        print(f"[{i}/{len(steps)}] {name:<36} {desc} ... ", end="", flush=True)
        t0 = time.time()
        with log.open("w", encoding="utf-8") as fh:
            code = subprocess.run([py, script, *args], stdout=fh, stderr=subprocess.STDOUT,
                                  env=env).returncode
        mins = (time.time() - t0) / 60
        if code != 0:
            print(f"FAILED (exit {code}, {mins:.1f} min). See {log}")
            sys.exit(code)
        print(f"ok ({mins:.1f} min)")
    print(f"\nAll {len(steps)} steps finished in {(time.time() - t_all) / 60:.1f} min. Logs: {run_logs}")


if __name__ == "__main__":
    main()
