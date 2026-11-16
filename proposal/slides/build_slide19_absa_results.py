"""
build_slide19_absa_results.py
Rebuild slide 19 (Aspect-level analysis results) with Combo 1 layout:
  - LEFT (60%):  Table ABSA-A matrix (visit context x 6 aspects, OR + stars)
  - RIGHT (40%): Horizontal bar chart image (mention rates) + 3 highlight bullets
                 + bottom note about reactions null

Also generates the bar chart as a PNG in figures/ and inserts it as an image.
Only slide 19 is touched. Everything else is preserved.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX = "presentation_build.pptx"
SLIDE_IDX = 18   # 0-indexed slide 19

FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
HEADER_FILL = RGBColor(0xE8, 0xE8, 0xE8)
ALT_FILL    = RGBColor(0xF8, 0xF8, 0xF8)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
DARK        = RGBColor(0x22, 0x22, 0x22)
MUTED       = RGBColor(0x55, 0x55, 0x55)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


def _cell(cell, text, bold=False, size=9, fill=None, align_left=True):
    cell.margin_left = Inches(0.05); cell.margin_right = Inches(0.05)
    cell.margin_top = Inches(0.02);  cell.margin_bottom = Inches(0.02)
    tf = cell.text_frame; tf.word_wrap = True; tf.clear()
    p = tf.paragraphs[0]; p.text = text
    p.alignment = PP_ALIGN.LEFT if align_left else PP_ALIGN.CENTER
    for run in p.runs: _font(run, FONT_BODY, size, bold=bold)
    if fill is not None:
        cell.fill.solid(); cell.fill.fore_color.rgb = fill


# ─── Step 1: Generate bar chart PNG ──────────────────────────────────────
figures_dir = Path("figures")
figures_dir.mkdir(exist_ok=True)
png_path = figures_dir / "aspect_mention_rates.png"

aspects = ["Visual", "Historical", "Service", "Accessibility", "Crowding", "Food"]
rates   = [63.8,     50.4,         27.4,      19.8,            16.3,       6.9]
# Sort descending (already in order)
colors = ["#2b5876", "#4a7891", "#6a9bb3", "#8bbdce", "#bedce6", "#dceef2"]

fig, ax = plt.subplots(figsize=(5.0, 3.0), dpi=160)
y_pos = range(len(aspects))
ax.barh(y_pos, rates, color=colors, edgecolor="#333333", linewidth=0.4)
ax.set_yticks(list(y_pos))
ax.set_yticklabels(aspects, fontsize=10)
ax.invert_yaxis()
ax.set_xlim(0, 72)
ax.set_xlabel("Mention rate (% of 11,164 reviews)", fontsize=9)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.spines["left"].set_color("#888888")
ax.spines["bottom"].set_color("#888888")
ax.tick_params(axis="both", colors="#444444", labelsize=9)
# Value labels
for i, v in enumerate(rates):
    ax.text(v + 1.2, i, f"{v:.1f}%", va="center", fontsize=9, color="#333333")
ax.set_axisbelow(True)
ax.grid(axis="x", color="#dddddd", linewidth=0.5)
plt.tight_layout()
plt.savefig(png_path, dpi=160, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"  Saved bar chart: {png_path}")


# ─── Step 2: Rebuild slide 19 content ─────────────────────────────────────
p = Presentation(PPTX)
slide = p.slides[SLIDE_IDX]

# Remove everything except Title (idx 0) and Slide-number placeholder (idx 4)
removed = 0
for shape in list(slide.shapes):
    try:
        pf = shape.placeholder_format
        if pf is not None and pf.idx in (0, 4):
            continue
    except Exception:
        pass
    shape._element.getparent().remove(shape._element)
    removed += 1
print(f"  Removed {removed} old shapes on slide 19")


# ─── Add left-side ABSA-A matrix table ───────────────────────────────────
# Rows: visit-context variables (significant effects only)
# Columns: Visit context | Hist | Access | Crowd | Food | Visual | Service
header = ["Visit context", "Hist.", "Access.", "Crowd.", "Food", "Visual", "Service"]
rows = [
    ["With: alone",              "–",      "–",      "–",      "0.64 *",  "–",      "0.52 **"],
    ["With: partner / spouse",   "–",      "–",      "1.25 *", "–",       "1.21 *", "–"],
    ["With: friends",            "–",      "–",      "–",      "–",       "1.28 *", "–"],
    ["With: children",           "1.22 *", "1.22 *", "–",      "–",       "–",      "1.55 ***"],
    ["With: parents/relatives",  "–",      "–",      "–",      "–",       "1.28 **","–"],
    ["With: colleagues",         "–",      "–",      "0.72 *", "–",       "–",      "–"],
    ["Purpose: outing",          "–",      "–",      "–",      "–",       "–",      "0.75 **"],
    ["Purpose: date",            "–",      "–",      "0.76 *", "1.51 *",  "–",      "–"],
    ["Waited to enter",          "–",      "–",      "2.13 ***","–",      "–",      "–"],
    ["Reservation",              "–",      "–",      "0.69 **","–",       "–",      "2.39 ***"],
    ["ln(text length)",          "2.18 ***","1.67 ***","1.85 ***","1.40 ***","1.67 ***","2.30 ***"],
    ["Mention rate",             "50.4%",  "19.8%",  "16.3%",  "6.9%",    "63.8%",  "27.4%"],
    ["Pseudo-R²",                "0.471",  "0.079",  "0.113",  "0.133",   "0.217",  "0.371"],
]

n_rows = 1 + len(rows)
tbl_left = Inches(0.35)
tbl_top  = Inches(1.60)
tbl_w    = Inches(7.70)
tbl_h    = Inches(4.60)

tbl_shape = slide.shapes.add_table(n_rows, 7, tbl_left, tbl_top, tbl_w, tbl_h)
tbl = tbl_shape.table
tbl.columns[0].width = Inches(1.80)
tbl.columns[1].width = Inches(0.90)
tbl.columns[2].width = Inches(0.95)
tbl.columns[3].width = Inches(0.95)
tbl.columns[4].width = Inches(0.95)
tbl.columns[5].width = Inches(0.95)
tbl.columns[6].width = Inches(1.20)

# Header
for j, h in enumerate(header):
    _cell(tbl.cell(0, j), h, bold=True, size=9, fill=HEADER_FILL,
          align_left=(j == 0))

# Rows
for i, row in enumerate(rows, start=1):
    fill = WHITE if i % 2 == 1 else ALT_FILL
    is_summary = row[0] in ("Mention rate", "Pseudo-R²")
    for j, val in enumerate(row):
        _cell(tbl.cell(i, j), val,
              bold=is_summary and j == 0,
              italic=False,
              size=9, fill=fill,
              align_left=(j == 0)) if False else None  # ignore italic kw
        # Re-apply with correct italic handling
        c = tbl.cell(i, j)
        c.margin_left = Inches(0.05); c.margin_right = Inches(0.05)
        c.margin_top = Inches(0.02);  c.margin_bottom = Inches(0.02)
        tf = c.text_frame; tf.word_wrap = True; tf.clear()
        par = tf.paragraphs[0]; par.text = val
        par.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
        for run in par.runs:
            _font(run, FONT_BODY, 9, bold=(is_summary and j == 0),
                  italic=is_summary)
        c.fill.solid(); c.fill.fore_color.rgb = fill


# Note under the table
note_tb = slide.shapes.add_textbox(Inches(0.35), Inches(6.30),
                                    Inches(7.70), Inches(0.35))
nf = note_tb.text_frame
nf.word_wrap = True
nf_p = nf.paragraphs[0]
nf_p.text = ("Blank cells = p ≥ .05.   Significance:  *** p<.001   ** p<.01   * p<.05.   "
             "Place FE and non-significant companion/purpose dummies not shown.")
nf_p.alignment = PP_ALIGN.LEFT
for run in nf_p.runs: _font(run, FONT_BODY, 8, italic=True, color=MUTED)


# ─── Add right-side bar chart image ──────────────────────────────────────
pic_left = Inches(8.30)
pic_top  = Inches(1.55)
pic_w    = Inches(4.70)
# Insert at the position, let aspect ratio determine height
slide.shapes.add_picture(str(png_path), pic_left, pic_top, width=pic_w)


# ─── Right-side highlights text ──────────────────────────────────────────
hl_tb = slide.shapes.add_textbox(Inches(8.30), Inches(4.60),
                                  Inches(4.70), Inches(1.90))
htf = hl_tb.text_frame
htf.word_wrap = True

def _add_line(text, bold=False, size=11, italic=False, idx=None, color=None, space=False):
    if idx == 0:
        para = htf.paragraphs[0]
    else:
        para = htf.add_paragraph()
    if space:
        para.space_before = Pt(2)
    para.text = text
    para.alignment = PP_ALIGN.LEFT
    for run in para.runs:
        _font(run, FONT_BODY, size, bold=bold, italic=italic,
              color=color if color else DARK)


_add_line("Highlights", bold=True, size=12, idx=0, color=DARK)
_add_line("•  Children  →  more mentions in 3 aspects "
          "(historical, access, service: ORs 1.22 – 1.55)", size=10)
_add_line("•  Waited  →  crowding ×2.13 ***;  "
          "Reserved  →  crowding ↓, service ×2.39 ***", size=10, space=True)
_add_line("•  Date-purpose  →  food ×1.51;  "
          "alone  →  food & service ↓", size=10, space=True)
_add_line("•  Six aspects validated by LDA K=6 + BERTopic K=15",
          size=10, space=True, italic=True, color=MUTED)


# ─── Bottom note: reactions null ─────────────────────────────────────────
null_tb = slide.shapes.add_textbox(Inches(8.30), Inches(6.30),
                                    Inches(4.70), Inches(0.60))
ntf = null_tb.text_frame
ntf.word_wrap = True
np_ = ntf.paragraphs[0]
np_.text = ("Reactions by aspect content:  no aspect reaches p<.05 after "
            "reviewer controls — engagement is reviewer-identity driven.")
np_.alignment = PP_ALIGN.LEFT
for run in np_.runs: _font(run, FONT_BODY, 9, italic=True, color=MUTED)


p.save(PPTX)
print(f"\nOK. Slide {SLIDE_IDX + 1} rebuilt: ABSA-A matrix (left) + bar chart "
      f"image + highlights (right).")
print(f"Total slides: {len(p.slides)} (unchanged).")
