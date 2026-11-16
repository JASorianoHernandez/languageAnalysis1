"""
plot_m1_confusion.py

Generate a presentation-quality confusion matrix PNG for M1 (Revisit, binary
logistic regression). Matches the slide colour palette used elsewhere
(forest-green accent #23312D on dark grey text #222222).

Output: ../slides/figures/m1_confusion.png  (also prints absolute path).
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

HERE   = Path(__file__).resolve().parent
CSV    = HERE.parent.parent / "data" / "analysis" / "naver" / "workshop" \
         / "FINAL" / "M1_confusion_matrix.csv"
OUT    = HERE / "figures" / "m1_confusion.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

# ─── Load ──────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV, index_col=0)
cm = df.values.astype(int)            # 2x2
total = cm.sum()

tn, fp = cm[0, 0], cm[0, 1]
fn, tp = cm[1, 0], cm[1, 1]

# Row-normalised percentages (recall from the perspective of the true class)
cm_pct = cm / cm.sum(axis=1, keepdims=True) * 100

# Derived metrics
accuracy    = (tp + tn) / total
sensitivity = tp / (tp + fn)          # recall for class 1
specificity = tn / (tn + fp)          # recall for class 0
precision_1 = tp / (tp + fp)
precision_0 = tn / (tn + fn)

# ─── Figure ────────────────────────────────────────────────────────────────
mpl.rcParams["font.family"]      = ["Malgun Gothic", "Arial", "DejaVu Sans"]
mpl.rcParams["axes.edgecolor"]   = "#222222"
mpl.rcParams["axes.labelcolor"]  = "#222222"
mpl.rcParams["xtick.color"]      = "#222222"
mpl.rcParams["ytick.color"]      = "#222222"

# Custom colormap: light cream -> forest green
cmap = LinearSegmentedColormap.from_list(
    "forest", ["#F6F3EC", "#B6C2B2", "#23312D"], N=256
)

fig, ax = plt.subplots(figsize=(7.6, 5.4), dpi=200)
im = ax.imshow(cm_pct, cmap=cmap, vmin=0, vmax=100, aspect="equal")

# Cell annotations: count + percent
labels_outer = [
    [f"TN  {tn:,}\n{cm_pct[0,0]:.1f}%", f"FP  {fp:,}\n{cm_pct[0,1]:.1f}%"],
    [f"FN  {fn:,}\n{cm_pct[1,0]:.1f}%", f"TP  {tp:,}\n{cm_pct[1,1]:.1f}%"],
]
for i in range(2):
    for j in range(2):
        colour = "white" if cm_pct[i, j] > 55 else "#222222"
        ax.text(j, i, labels_outer[i][j], ha="center", va="center",
                fontsize=15, fontweight="bold", color=colour, linespacing=1.3)

# Ticks and labels
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(["Predicted\nNo revisit (0)", "Predicted\nRevisit (1)"],
                   fontsize=11)
ax.set_yticklabels(["Actual\nNo revisit (0)", "Actual\nRevisit (1)"],
                   fontsize=11)
ax.tick_params(length=0)

# Axis frame
for spine in ax.spines.values():
    spine.set_edgecolor("#AAAAAA")
    spine.set_linewidth(0.8)

# Title
ax.set_title("M1 — Revisit confusion matrix  /  재방문 혼동 행렬",
             fontsize=14, fontweight="bold", color="#222222",
             pad=14, loc="left")

# Side metrics panel
summary = (
    f"N                          = {total:,}\n"
    f"Accuracy                   = {accuracy*100:.1f}%\n"
    f"Sensitivity (TPR, class 1) = {sensitivity*100:.1f}%\n"
    f"Specificity (TNR, class 0) = {specificity*100:.1f}%\n"
    f"Precision   (class 1)      = {precision_1*100:.1f}%\n"
    f"Precision   (class 0)      = {precision_0*100:.1f}%\n"
    f"AUC (5-fold CV)            = 0.80"
)
fig.text(0.65, 0.52, summary,
         ha="left", va="center",
         fontsize=10.5, color="#222222", family="monospace")

# Caption
fig.text(0.08, 0.03,
         "Cells show counts and row-normalised percentages (within each "
         "actual class).  AUC from 5-fold cross-validation.",
         fontsize=8.5, style="italic", color="#555555")

# Layout: compress left side to make room for metrics panel on the right
ax.set_position([0.08, 0.15, 0.52, 0.72])

plt.savefig(OUT, dpi=250, bbox_inches="tight", facecolor="white")
plt.close()

print(f"Saved to: {OUT}")
print(f"Absolute path: {OUT.resolve()}")
