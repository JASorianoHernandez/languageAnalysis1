"""
topic_val_run_all.py
Runs the 3 topic-validation scripts in sequence (lightest to heaviest):
  1. topic_val_02_lda_light.py    (~3-5 min)   K=5 and K=10 only
  2. topic_val_03_bertopic.py     (~15-30 min) BERTopic with multilingual embeddings
  3. topic_val_01_lda_full.py     (~30-60 min) full K=2..15 grid, 3 seeds

Each script prints its progress; this wrapper only chains them and reports
a final elapsed time and which outputs exist.

Run (base env):  python topic_val_run_all.py
"""
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SCRIPTS = [
    ("Light LDA (K=5, K=10)",            "topic_val_02_lda_light.py"),
    ("BERTopic (embeddings + HDBSCAN)",  "topic_val_03_bertopic.py"),
    ("Full LDA grid (K=2..15)",          "topic_val_01_lda_full.py"),
]

OUT_DIR = Path("data/analysis/naver/topic_validation")
EXPECTED_FILES = [
    "lda_light_summary.txt",
    "bertopic_summary.txt",
    "lda_full_bestk.txt",
]

t_total = time.time()
print("=" * 60)
print("TOPIC VALIDATION PIPELINE")
print("=" * 60)
print(f"Running 3 scripts in sequence; outputs will land in {OUT_DIR}/")
print()

for label, script in SCRIPTS:
    print(f"\n{'=' * 60}")
    print(f"[{SCRIPTS.index((label, script))+1}/{len(SCRIPTS)}] {label}")
    print(f"  running: python {script}")
    print("=" * 60)
    t0 = time.time()
    result = subprocess.run([sys.executable, script], capture_output=False)
    elapsed = time.time() - t0
    status = "OK" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
    print(f"\n  {status}  ({elapsed/60:.1f} min)")
    if result.returncode != 0:
        print(f"\nStopping pipeline after {script}. Fix the error and rerun that script.")
        sys.exit(result.returncode)

print(f"\n{'=' * 60}")
print(f"PIPELINE COMPLETE  (total {(time.time()-t_total)/60:.1f} min)")
print("=" * 60)
print(f"\nOutputs in {OUT_DIR}/:")
for f in EXPECTED_FILES:
    p = OUT_DIR / f
    status = "YES" if p.exists() else "MISSING"
    print(f"  [{status}]  {f}")
print()
print("Next step: compare the 3 outputs with our 5 ABSA aspects")
print("  (historical_cultural, accessibility, crowding, food, visual_photo)")
