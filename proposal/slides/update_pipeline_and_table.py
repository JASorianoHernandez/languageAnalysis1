"""
update_pipeline_and_table.py

Updates two slides without touching user's prior edits elsewhere:

  Slide 9 (Research Framework -> Research Pipeline)
    - Rename title to "Research Pipeline / 연구 파이프라인"
    - Rewrite Step 2 (Variables) to reflect only variables used in the
      final spec (2 DVs, 8 IVs grouped by Shared / Only M1 / Only M2)
    - Update Step 3 (Models) from "ordered logistic, exploratory" to
      "multinomial logistic regression", add N for each sample

  Slide 10 (Models & Variables table)
    - Preserve the user's table format (Source Sans 11 pt bold, no fill)
    - Fill in missing cells in Row 2 (Description for Revisit and Rating)
    - Fix Row 3 (Type): change "Ordered Nominal" to "Categorical (3-class)",
      fill in types for every independent variable
    - Fix Row 4 (Model Used): correct the shared vs model-specific
      assignments (previously all said "M1 & M2" which was wrong)
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX = "presentation_v2.pptx"

FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
DARK = RGBColor(0x22, 0x22, 0x22)
MUTED = RGBColor(0x55, 0x55, 0x55)
HEAD = RGBColor(0x23, 0x31, 0x2D)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


def set_title(slide, title_text):
    for shape in slide.shapes:
        if shape.name.startswith("Title"):
            tf = shape.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = title_text
            p.alignment = PP_ALIGN.LEFT
            for run in p.runs:
                _font(run, FONT_HEAD, 28, bold=True, color=DARK)
            return


def strip_body_shapes(slide, keep_names=("Title",)):
    for shape in list(slide.shapes):
        if any(shape.name.startswith(k) for k in keep_names):
            continue
        shape._element.getparent().remove(shape._element)


def add_textbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top),
                                   Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def add_para(tf, text, size=12, bold=False, italic=False, color=DARK,
             space_before=4, first=False, name=FONT_BODY,
             align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_before = Pt(space_before)
    p.text = text
    p.alignment = align
    for run in p.runs:
        _font(run, name, size, bold=bold, italic=italic, color=color)


def set_cell_text(cell, text, size=11, bold=True, color=None,
                  align=PP_ALIGN.CENTER):
    """Set a cell's text while preserving the reference format
    (Source Sans, 11 pt, bold, no fill, default colour)."""
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    p.text = text
    p.alignment = align
    for run in p.runs:
        _font(run, FONT_BODY, size, bold=bold, color=color)


# ─── Load ──────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
print(f"Loaded. Current slide count: {len(p.slides)}")

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Research Framework -> Research Pipeline
# ═══════════════════════════════════════════════════════════════════════════
slide = p.slides[8]
print(f"\nWorking on slide 9: {slide.slide_layout.name}")

# Clear body (keep title placeholder)
strip_body_shapes(slide, keep_names=("Title",))
set_title(slide, "Research Pipeline / 연구 파이프라인")

# Step 1 — Data Acquisition
s1 = add_textbox(slide, 0.5, 1.3, 12.3, 1.4)
add_para(s1, "1.  Data Acquisition / 데이터 수집",
         size=15, bold=True, color=HEAD, first=True)
add_para(s1, "Naver Place scraper  →  29 attractions · 14,401 reviews · "
             "8,276 reviewers",
         size=12, color=DARK, space_before=6)
add_para(s1, "11,165 reviews with text  ·  Yanolja Top 500  ∩  KTO visitor "
             "volume  ·  Seoul (25) + Busan (4)",
         size=12, color=DARK, space_before=3)

# Step 2 — Variables (fully rewritten)
s2 = add_textbox(slide, 0.5, 2.9, 12.3, 2.5)
add_para(s2, "2.  Variables / 변수",
         size=15, bold=True, color=HEAD, first=True)
add_para(s2, "Dependent (2)",
         size=12, bold=True, color=DARK, space_before=6)
add_para(s2,
         "    Revisit    binary {0, 1}        ·    "
         "Rating    3 categories: LOW ≤3.5★ · MID 4–4.5★ · TOP 5★",
         size=11, color=DARK, space_before=2)
add_para(s2, "Independent (8 unique)",
         size=12, bold=True, color=DARK, space_before=6)
add_para(s2, "    Shared  (3)   sentiment · waited · ln(1+followers)",
         size=11, color=DARK, space_before=2)
add_para(s2, "    Only M1 (3)   is_tourist · comp_alone · ln(1+reviews)",
         size=11, color=DARK, space_before=2)
add_para(s2, "    Only M2 (2)   ln(1+photos) · season_autumn",
         size=11, color=DARK, space_before=2)
add_para(s2,
         "Fixed effects  Place (δⱼ, 28 dummies, Gyeongbokgung = reference)  "
         "·  Standard errors clustered by reviewer",
         size=11, italic=True, color=MUTED, space_before=6)

# Step 3 — Models (updated to multinomial, no "exploratory")
s3 = add_textbox(slide, 0.5, 5.65, 12.3, 1.3)
add_para(s3, "3.  Models / 모형",
         size=15, bold=True, color=HEAD, first=True)
add_para(s3, "M1  Revisit    Binary logistic regression"
             "                                    (N = 11,165)",
         size=12, color=DARK, space_before=6)
add_para(s3, "M2  Rating     Multinomial logistic regression  "
             "(TOP as reference)      (N = 4,044)",
         size=12, color=DARK, space_before=3)

print("  Slide 9 updated.")


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Models & Variables table (complete missing + fix wrong cells)
# ═══════════════════════════════════════════════════════════════════════════
slide = p.slides[9]
print(f"\nWorking on slide 10: {slide.slide_layout.name}")

# Locate the table shape
tbl = None
for shape in slide.shapes:
    if shape.has_table:
        tbl = shape.table
        break
assert tbl is not None, "Table not found on slide 10."

# Column mapping (from earlier inspection, 5 rows x 11 cols):
#   Row 0: headers (col 1 = Dependent Variables, col 3 = Independent Variables)
#   Row 1: Variable Name
#   Row 2: Description
#   Row 3: Type
#   Row 4: Model Used
# Column indices:
#   0 Label | 1 Revisit | 2 Rating | 3 sentiment | 4 waited |
#   5 ln(1+followers) | 6 is_tourist | 7 comp_alone |
#   8 ln(1+reviews) | 9 ln(1+photos) | 10 season_autumn

# ── Row 2 (Description) — fill in missing cells for Revisit and Rating ───
set_cell_text(tbl.cell(2, 1), "1 if visitCount ≥ 2, else 0")
set_cell_text(tbl.cell(2, 2), "3 cats: LOW ≤3.5★ / MID 4–4.5★ / TOP 5★")

# ── Row 3 (Type) — correct Rating and fill in IV types ────────────────
set_cell_text(tbl.cell(3, 2), "Categorical (3-class)")   # was "Ordered Nominal"
set_cell_text(tbl.cell(3, 3), "Continuous [-1, 1]")      # sentiment
set_cell_text(tbl.cell(3, 4), "Binary {0, 1}")           # waited
set_cell_text(tbl.cell(3, 5), "Continuous (log)")        # ln(followers)
set_cell_text(tbl.cell(3, 6), "Binary {0, 1}")           # is_tourist
set_cell_text(tbl.cell(3, 7), "Binary {0, 1}")           # comp_alone
set_cell_text(tbl.cell(3, 8), "Continuous (log)")        # ln(reviews)
set_cell_text(tbl.cell(3, 9), "Continuous (log)")        # ln(photos)
set_cell_text(tbl.cell(3, 10), "Binary {0, 1}")          # season_autumn

# ── Row 4 (Model Used) — fix the shared vs model-specific assignments ──
# sentiment, waited, ln(followers): shared (already correct, re-set to normalise)
set_cell_text(tbl.cell(4, 3), "M1 & M2")
set_cell_text(tbl.cell(4, 4), "M1 & M2")
set_cell_text(tbl.cell(4, 5), "M1 & M2")
# is_tourist, comp_alone, ln(reviews): only M1
set_cell_text(tbl.cell(4, 6), "M1 only")
set_cell_text(tbl.cell(4, 7), "M1 only")
set_cell_text(tbl.cell(4, 8), "M1 only")
# ln(photos), season_autumn: only M2
set_cell_text(tbl.cell(4, 9), "M2 only")
set_cell_text(tbl.cell(4, 10), "M2 only")

print("  Slide 10 table updated.")

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"\nFinal slide count: {len(p.slides)} (unchanged).")
print(f"Saved to: {PPTX}")
