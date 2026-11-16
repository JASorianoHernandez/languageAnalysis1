"""
reduce_fit_add_divergent.py

Two operations on presentation_v2.pptx:

1. Reduce Model Fit Summary table (slide 12) to minimum essentials
   (N, pseudo-R², AIC, one classification metric). Preserves the user's
   table format (Source Sans 11 pt bold, no fill — per memory).

2. Insert a new "Divergent traces of satisfaction" content slide between
   slide 15 (M2 Visualising asymmetry) and slide 16 (Section 5 divider).
   This recovers the key interpretive slide the user had deleted and
   restores the paper's conceptual contribution.
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
DARK   = RGBColor(0x22, 0x22, 0x22)
MUTED  = RGBColor(0x55, 0x55, 0x55)
HEAD   = RGBColor(0x23, 0x31, 0x2D)


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


def move_slide(p, old_index, new_index):
    sldIdLst = p.slides._sldIdLst
    slides = list(sldIdLst)
    sldIdLst.remove(slides[old_index])
    sldIdLst.insert(new_index, slides[old_index])


# ─── Load ──────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
print(f"Loaded. Current slide count: {len(p.slides)}")

# ═══════════════════════════════════════════════════════════════════════════
# 1. REBUILD slide 12 (Model Fit Summary) to minimum essentials
# ═══════════════════════════════════════════════════════════════════════════
slide = p.slides[11]
print(f"\nWorking on slide 12 (Model fit summary): {slide.slide_layout.name}")

# Strip body (keep title); rebuild a compact 6x3 table
strip_body_shapes(slide, keep_names=("Title",))
set_title(slide, "Model fit summary / 모형 적합도 요약")

# Compact 6 rows x 3 cols table (one metric per row + header)
tbl = slide.shapes.add_table(6, 3, Inches(1.0), Inches(1.8),
                              Inches(11.3), Inches(3.8)).table

def _set_cell(cell, text, bold=True, size=12):
    cell.text = ""
    para = cell.text_frame.paragraphs[0]
    para.text = text
    para.alignment = PP_ALIGN.CENTER if text else PP_ALIGN.LEFT
    for run in para.runs:
        _font(run, FONT_BODY, size, bold=bold, color=DARK)

# Header row
header = ["Statistic", "M1 Revisit", "M2 Rating"]
for j, h in enumerate(header):
    _set_cell(tbl.cell(0, j), h, bold=True, size=13)

# Data rows (minimum essentials)
rows = [
    ("Model type",            "Binary logit",         "Multinomial logit"),
    ("N observations",        "11,165",               "4,044"),
    ("Pseudo-R²",             "0.201",                "0.190"),
    ("AIC",                   "9,601.5",              "4,753.6"),
    ("Classification quality","AUC = 0.80 (CV)",      "Within ±1 = 95%"),
]
for i, (label, m1, m2) in enumerate(rows, 1):
    # Label column: left aligned, bold
    _set_cell(tbl.cell(i, 0), label, bold=True, size=12)
    tbl.cell(i, 0).text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
    _set_cell(tbl.cell(i, 1), m1, bold=True, size=12)
    _set_cell(tbl.cell(i, 2), m2, bold=True, size=12)

# Compact note at the bottom
note = add_textbox(slide, 1.0, 5.8, 11.3, 0.8)
add_para(note,
         "Both models fit in the ``good'' range for discrete-choice "
         "consumer-research models (McFadden pseudo-R²).",
         size=10, italic=True, color=MUTED, first=True)
add_para(note,
         "두 모형 모두 소비자 연구의 이산 선택 모형에서 ``좋음'' 범위에 속함.",
         size=9, italic=True, color=MUTED, space_before=2)

print("  Slide 12 compacted to 5 essential rows.")


# ═══════════════════════════════════════════════════════════════════════════
# 2. INSERT new slide: Divergent traces of satisfaction
#    Position: after slide 15 (M2 Visualising asymmetric effects),
#    before slide 16 (Section 5 Conclusions)
# ═══════════════════════════════════════════════════════════════════════════

# Find Title and Content layout
L_CONTENT = None
for layout in p.slide_layouts:
    if layout.name == "Title and Content":
        L_CONTENT = layout
        break
assert L_CONTENT is not None

new_slide = p.slides.add_slide(L_CONTENT)
new_index = len(p.slides) - 1
target_index = 15  # 0-based, slide 16 (becomes the Divergent traces slide)

move_slide(p, new_index, target_index)
print(f"\nInserted Divergent traces slide at position {target_index + 1}.")

slide = p.slides[target_index]
strip_body_shapes(slide, keep_names=("Title",))
set_title(slide, "Divergent traces of satisfaction / 만족도의 서로 다른 흔적")

# Correlation box (top)
corr = add_textbox(slide, 0.6, 1.4, 12.0, 1.3)
add_para(corr,
         "Correlation between revisit and rating:  r = 0.08",
         size=18, bold=True, color=HEAD, first=True)
add_para(corr,
         "재방문과 별점 사이의 상관:  r = 0.08",
         size=13, italic=True, color=MUTED, space_before=3)
add_para(corr,
         "Shared variance ≈ 0.6%  —  the two outcomes capture distinct "
         "aspects of satisfaction, not the same construct.",
         size=12, color=DARK, space_before=6)
add_para(corr,
         "공유 분산 약 0.6%  —  두 결과는 만족도의 서로 다른 측면을 포착한다.",
         size=11, italic=True, color=MUTED, space_before=2)

# Shared predictors section
sp = add_textbox(slide, 0.6, 3.3, 12.0, 2.7)
add_para(sp, "Shared predictors act differently in each model",
         size=15, bold=True, color=HEAD, first=True)
add_para(sp, "공유 예측 변수가 두 모형에서 다르게 작용한다",
         size=12, italic=True, color=MUTED, space_before=2)
add_para(sp,
         "    waited          M1  ↓↓ (OR 0.54)      ·  M2  ↑ in LOW (OR 3.10)"
         "      — convergent, different scale",
         size=12, color=DARK, space_before=10)
add_para(sp,
         "    sentiment       M1  ↓   (OR 0.74)     ·  M2  ↓↓↓ in LOW (OR 0.04)"
         "    — different roles",
         size=12, color=DARK, space_before=4)
add_para(sp,
         "    ln(followers)   M1  ↑   (OR 1.23)     ·  M2  ↓ in LOW (OR 0.71)"
         "       — convergent",
         size=12, color=DARK, space_before=4)

# Takeaway
tk = add_textbox(slide, 0.6, 6.3, 12.0, 1.0)
add_para(tk,
         "Takeaway: declared satisfaction (rating) and behavioural "
         "satisfaction (revisit) are related but genuinely distinct traces "
         "of a latent construct.",
         size=12, italic=True, color=MUTED, first=True)
add_para(tk,
         "요점: 선언된 만족도(별점)와 행동적 만족도(재방문)는 관련은 있지만 "
         "잠재적 구성개념의 진정으로 구별되는 흔적이다.",
         size=11, italic=True, color=MUTED, space_before=3)

print("  Divergent traces slide content added.")

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"\nFinal slide count: {len(p.slides)}")
print(f"Saved to: {PPTX}")
