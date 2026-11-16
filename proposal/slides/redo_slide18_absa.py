"""
redo_slide18_absa.py
Rebuild ONLY slide 18 with:
  - New title: "Aspect Based Sentiment Analysis / 측면 수준 분석의 작동 방식"
  - Corrected step order (validation happens BEFORE LLM, as part of aspect selection)
  - 2-column layout: 3 steps on the left, 2 steps on the right

Only slide 18 is touched.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

PPTX = "presentation_build.pptx"
SLIDE_IDX = 17   # 0-indexed slide 18
FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
LINE_GREY = RGBColor(0x95, 0x95, 0x95)
DARK      = RGBColor(0x22, 0x22, 0x22)
MUTED     = RGBColor(0x55, 0x55, 0x55)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


p = Presentation(PPTX)
slide = p.slides[SLIDE_IDX]

# ─── Remove everything except Title and Slide Number placeholders ─────────
removed = 0
for shape in list(slide.shapes):
    try:
        pf = shape.placeholder_format
        if pf is not None and pf.idx in (0, 4):
            continue  # keep Title and Slide Number
    except Exception:
        pass
    shape._element.getparent().remove(shape._element)
    removed += 1
print(f"  Removed {removed} old shapes on slide 18")

# ─── Rewrite title: left-aligned, bilingual ───────────────────────────────
title = slide.shapes.title
title.left = Inches(0.45); title.top = Inches(0.40)
title.width = Inches(11.5); title.height = Inches(0.95)
tf = title.text_frame; tf.clear()
p_en = tf.paragraphs[0]
p_en.text = "Aspect Based Sentiment Analysis"
p_en.alignment = PP_ALIGN.LEFT
for run in p_en.runs: _font(run, FONT_HEAD)
p_ko = tf.add_paragraph()
p_ko.text = "측면 수준 분석의 작동 방식"
p_ko.alignment = PP_ALIGN.LEFT
for run in p_ko.runs: _font(run, FONT_HEAD, 20)

# ─── Define the 5 steps (corrected order) ────────────────────────────────
STEPS = [
    ("Step 1 — Review corpus",
     "1단계 — 리뷰 코퍼스",
     "11,164 Korean reviews with text (≥10 chars)   ·   source: naver_dataset.csv"),
    ("Step 2 — Aspect selection",
     "2단계 — 측면 선정",
     "A priori from tourism/hospitality literature "
     "(SERVQUAL — Parasuraman et al., 1988; Chang, 2021; Ko et al., 2018)  "
     "+  unsupervised corroboration on this corpus:  LDA at optimal K = 6 "
     "(coherence c_v = 0.520)  and  BERTopic (K = 15, multilingual E5 "
     "embeddings).  5/6 aspects emerge as topics; crowding retained as a "
     "polarity-dominated dimension (18.1 % of mentions negative)."),
    ("Step 3 — LLM classification",
     "3단계 — LLM 분류",
     "Qwen2.5-7B-Instruct in 4-bit  ·  06_llm_analysis.py --naver  ·  prompt "
     "specifying the 6 aspects + 3 few-shot examples  ·  JSON-parsed output."),
    ("Step 4 — Six aspect labels per review",
     "4단계 — 리뷰당 여섯 측면 라벨",
     "historical/cultural  ·  accessibility  ·  crowding  ·  food  ·  "
     "visual/photo  ·  service/experience     each scored −1 / 0 / +1."),
    ("Step 5 — Regressions (§4.6)",
     "5단계 — 회귀분석 (§4.6)",
     "ABSA-A: six logistic regressions  —  mentions_aspect  ~  visit context "
     "+ reviewer controls + δⱼ   (place FE, SE clustered by reviewer)."),
]

# ─── Layout: 2 columns, left=3 boxes, right=2 boxes ───────────────────────
# Slide usable area (below title): ~ 1.50 to 6.60 vertically (= 5.1")
# Horizontally: 0.45 to 12.85 (= 12.4")
TOP_Y = 1.55
BOX_W = 5.80
LEFT_X  = 0.45
RIGHT_X = 7.05
LEFT_H  = 1.42   # three boxes fit in 5.1" with gaps
RIGHT_H = 1.42
GAP_V   = 0.18


def _add_box(x, y, w, h, en, ko, body, number):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                  Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = LINE_GREY; box.line.width = Emu(12700)
    box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.14); tf.margin_right = Inches(0.14)
    tf.margin_top = Inches(0.06); tf.margin_bottom = Inches(0.06)
    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.LEFT
    p1.text = f"{en}      /      {ko}"
    for run in p1.runs: _font(run, FONT_HEAD, 11, bold=True, color=DARK)
    p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.LEFT
    p2.text = body
    for run in p2.runs: _font(run, FONT_BODY, 9, color=DARK)


# Left column: steps 1, 2, 3
for i, (en, ko, desc) in enumerate(STEPS[:3]):
    y = TOP_Y + i * (LEFT_H + GAP_V)
    _add_box(LEFT_X, y, BOX_W, LEFT_H, en, ko, desc, i + 1)

# Right column: steps 4, 5 (slightly offset so arrows look clean)
RIGHT_TOP_Y = TOP_Y  # same top as left column
RIGHT_H2 = (3 * LEFT_H + 2 * GAP_V - GAP_V) / 2   # fill right column
for i, (en, ko, desc) in enumerate(STEPS[3:]):
    y = RIGHT_TOP_Y + i * (RIGHT_H2 + GAP_V)
    _add_box(RIGHT_X, y, BOX_W, RIGHT_H2, en, ko, desc, i + 4)


# ─── Arrows ───────────────────────────────────────────────────────────────
# Downward arrows between left-column boxes (1→2, 2→3)
for i in range(2):
    y_start = TOP_Y + (i + 1) * LEFT_H + i * GAP_V
    y_end   = y_start + GAP_V
    ax = LEFT_X + BOX_W / 2
    arr = slide.shapes.add_connector(1,
                                      Inches(ax), Inches(y_start),
                                      Inches(ax), Inches(y_end))
    arr.line.color.rgb = LINE_GREY; arr.line.width = Emu(19050)

# Horizontal-ish arrow from box 3 (bottom-left) to box 4 (top-right)
# Box 3 right-middle: (LEFT_X + BOX_W, TOP_Y + 2*(LEFT_H + GAP_V) + LEFT_H/2)
# Box 4 left-middle:  (RIGHT_X,         RIGHT_TOP_Y + RIGHT_H2/2)
x1 = LEFT_X + BOX_W
y1 = TOP_Y + 2 * (LEFT_H + GAP_V) + LEFT_H / 2
x2 = RIGHT_X
y2 = RIGHT_TOP_Y + RIGHT_H2 / 2
# Use an elbow connector (type 3 = bent)
arr_h = slide.shapes.add_connector(2, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
arr_h.line.color.rgb = LINE_GREY; arr_h.line.width = Emu(19050)

# Downward arrow in right column (4→5)
y_start_r = RIGHT_TOP_Y + RIGHT_H2
y_end_r   = y_start_r + GAP_V
ax_r = RIGHT_X + BOX_W / 2
arr_r = slide.shapes.add_connector(1,
                                    Inches(ax_r), Inches(y_start_r),
                                    Inches(ax_r), Inches(y_end_r))
arr_r.line.color.rgb = LINE_GREY; arr_r.line.width = Emu(19050)

p.save(PPTX)
print(f"OK. Slide {SLIDE_IDX + 1} rebuilt in 2-column (3 + 2) layout.")
