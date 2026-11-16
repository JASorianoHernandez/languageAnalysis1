"""
fix_slide17_add_absa_pipeline.py
Two targeted edits only:

  1. Slide 17 (Main findings M1-M4): rebuild the four mini-tables with
     TWO columns each (Variable  |  OR/IRR  [CI]  stars), merging the
     significance column into the value column.
  2. Insert a NEW slide BEFORE the Aspect-level results slide, with a
     "How the ABSA analysis works" pipeline diagram so the audience sees
     how aspect labels were produced before seeing the regressions.

No other slide is touched. Manual edits on other slides are preserved.

Run (base env):  python fix_slide17_add_absa_pipeline.py
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
FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
HEADER_FILL = RGBColor(0xE8, 0xE8, 0xE8)
ALT_FILL    = RGBColor(0xF8, 0xF8, 0xF8)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
LINE_GREY   = RGBColor(0x95, 0x95, 0x95)
DARK        = RGBColor(0x22, 0x22, 0x22)
MUTED       = RGBColor(0x55, 0x55, 0x55)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


def _cell(cell, text, bold=False, size=10, fill=None, align_left=True):
    cell.margin_left = Inches(0.06); cell.margin_right = Inches(0.06)
    cell.margin_top = Inches(0.02);  cell.margin_bottom = Inches(0.02)
    tf = cell.text_frame; tf.word_wrap = True; tf.clear()
    p = tf.paragraphs[0]; p.text = text
    p.alignment = PP_ALIGN.LEFT if align_left else PP_ALIGN.CENTER
    for run in p.runs: _font(run, FONT_BODY, size, bold=bold)
    if fill is not None:
        cell.fill.solid(); cell.fill.fore_color.rgb = fill


p = Presentation(PPTX)


# ─── STEP 1: Rebuild slide 17 with 2-column tables ────────────────────────
slide17 = p.slides[16]

# Remove the 4 current tables + their title/subtitle text boxes + note + legend
# that were added by the previous script. Keep only Title and slide-number.
keep_names = set()
to_keep = []
for shape in slide17.shapes:
    try:
        pf = shape.placeholder_format
        if pf is not None and pf.idx in (0, 4):
            to_keep.append(shape); continue
    except Exception:
        pass
    # TextBox 3 (slide-number stand-in, empty) — keep
    if shape.has_text_frame and (not shape.text_frame.text.strip()) \
            and 9.0 < shape.left / 914400 < 10.0:
        to_keep.append(shape); continue
removed = 0
for shape in list(slide17.shapes):
    if shape not in to_keep:
        shape._element.getparent().remove(shape._element)
        removed += 1
print(f"  Slide 17: removed {removed} old table/textbox shapes")

# Data: value column now = "OR  [95% CI]  stars"
def _combo(or_ci, stars):
    return f"{or_ci}   {stars}".rstrip()

M1 = {
    "title_en": "M1 Revisit",  "title_ko": "재방문",
    "subtitle": "Logistic · N = 11,165 · AUC 0.773 · pseudo-R² 0.203",
    "metric":   "OR",
    "rows": [
        ("ln(1 + reviewer's reviews)", _combo("1.52  [1.40, 1.65]", "***")),
        ("With: alone",                _combo("1.68  [1.18, 2.39]", "**")),
        ("With: friends",              _combo("0.58  [0.42, 0.80]", "**")),
        ("Waited to enter",            _combo("0.51  [0.35, 0.72]", "***")),
        ("Sentiment  (−1 to +1)",      _combo("0.70  [0.60, 0.81]", "***")),
        ("Purpose: travel",            _combo("0.56  [0.42, 0.75]", "***")),
        ("ln(text length)",            _combo("1.29  [1.14, 1.47]", "***")),
    ],
}
M2 = {
    "title_en": "M2 Keyword Count",  "title_ko": "키워드 수",
    "subtitle": "Ordered logistic · N = 14,401 · RMSE 1.37 (base 1.88)",
    "metric":   "OR",
    "rows": [
        ("Wrote text (15+ chars)",     _combo("4.02  [3.51, 4.60]", "***")),
        ("Visit info provided",        _combo("2.53  [2.01, 3.18]", "***")),
        ("Revisitor (2+ visits)",      _combo("1.60  [1.32, 1.93]", "***")),
        ("Purpose: outing",            _combo("1.85  [1.60, 2.13]", "***")),
        ("Purpose: travel",            _combo("1.73  [1.49, 2.02]", "***")),
        ("With: alone",                _combo("1.67  [1.27, 2.20]", "***")),
        ("Waited to enter",            _combo("0.75  [0.64, 0.88]", "***")),
    ],
}
M3 = {
    "title_en": "M3 Rating  (exploratory)",  "title_ko": "별점 (탐색적)",
    "subtitle": "Ordered logistic · N = 4,651 · 73.9% five-star · McFadden R² 0.095",
    "metric":   "OR",
    "rows": [
        ("Keyword Count (0–5)",            _combo("1.56  [1.45, 1.69]", "***")),
        ("Revisitor (2+ visits)",          _combo("1.37  [1.03, 1.82]", "*")),
        ("Wrote text  (text-only spec)",   _combo("0.64  [0.49, 0.83]", "***")),
        ("Sentiment  (text-only spec)",    _combo("4.90  [3.52, 6.82]", "***")),
    ],
    "note": "Reported as exploratory: ratings move little across the corpus.",
}
M4 = {
    "title_en": "M4 Reactions",  "title_ko": "반응 수",
    "subtitle": "Negative binomial · N = 11,165 · AUC any-reaction 0.815 · α̂ = 2.44",
    "metric":   "IRR",
    "rows": [
        ("ln(1 + reviewer's followers)", _combo("1.97  [1.79, 2.18]", "***")),
        ("ln(text length)",              _combo("1.64  [1.44, 1.87]", "***")),
        ("Keyword tags (0–5)",           _combo("1.12  [1.05, 1.20]", "**")),
        ("Sentiment  (−1 to +1)",        _combo("0.77  [0.64, 0.91]", "**")),
        ("Visit info provided",          _combo("1.70  [1.08, 2.68]", "*")),
        ("Visit: autumn",                _combo("0.71  [0.61, 0.83]", "***")),
        ("Purpose: outing",              _combo("0.63  [0.45, 0.88]", "**")),
    ],
}

GRID = [
    (0.45, 1.55, M1),
    (6.85, 1.55, M2),
    (0.45, 4.05, M3),
    (6.85, 4.05, M4),
]
TABLE_W = 6.0


def place_model_table_2col(slide, x_in, y_in, data):
    # Title
    title_tb = slide.shapes.add_textbox(Inches(x_in), Inches(y_in),
                                        Inches(TABLE_W), Inches(0.35))
    tp = title_tb.text_frame.paragraphs[0]
    tp.text = f"{data['title_en']}  /  {data['title_ko']}"
    tp.alignment = PP_ALIGN.LEFT
    for run in tp.runs: _font(run, FONT_HEAD, 13, bold=True, color=DARK)
    # Subtitle
    sub_tb = slide.shapes.add_textbox(Inches(x_in), Inches(y_in + 0.33),
                                       Inches(TABLE_W), Inches(0.26))
    sp = sub_tb.text_frame.paragraphs[0]
    sp.text = data["subtitle"]; sp.alignment = PP_ALIGN.LEFT
    for run in sp.runs: _font(run, FONT_BODY, 9, italic=True, color=MUTED)
    # Table (2 columns)
    n_rows = 1 + len(data["rows"])
    tbl_h = Inches(min(1.65, 0.22 * n_rows + 0.10))
    tbl_shape = slide.shapes.add_table(n_rows, 2,
                                        Inches(x_in), Inches(y_in + 0.60),
                                        Inches(TABLE_W), tbl_h)
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(3.30)
    tbl.columns[1].width = Inches(2.70)
    _cell(tbl.cell(0, 0), "Variable", bold=True, size=10, fill=HEADER_FILL)
    _cell(tbl.cell(0, 1), f"{data['metric']}  [95% CI]", bold=True, size=10, fill=HEADER_FILL)
    for i, (var, val) in enumerate(data["rows"], start=1):
        fill = WHITE if i % 2 == 1 else ALT_FILL
        _cell(tbl.cell(i, 0), var, size=10, fill=fill)
        _cell(tbl.cell(i, 1), val, size=10, fill=fill)
    # Note
    if "note" in data:
        note_y = y_in + 0.60 + 0.22 * n_rows + 0.05
        note_tb = slide.shapes.add_textbox(Inches(x_in), Inches(note_y),
                                            Inches(TABLE_W), Inches(0.25))
        np = note_tb.text_frame.paragraphs[0]
        np.text = data["note"]; np.alignment = PP_ALIGN.LEFT
        for run in np.runs: _font(run, FONT_BODY, 8, italic=True, color=MUTED)


for x_in, y_in, data in GRID:
    place_model_table_2col(slide17, x_in, y_in, data)

# Legend at the bottom
legend = slide17.shapes.add_textbox(Inches(0.45), Inches(6.70),
                                     Inches(12.4), Inches(0.26))
lp = legend.text_frame.paragraphs[0]
lp.text = ("Significance:  *** p < .001   ·   ** p < .01   ·   * p < .05.      "
            "OR = odds ratio;  IRR = incidence rate ratio;  all models include "
            "place fixed effects and standard errors clustered by reviewer.")
lp.alignment = PP_ALIGN.LEFT
for run in lp.runs: _font(run, FONT_BODY, 9, italic=True, color=MUTED)
print("  Slide 17: 4 mini-tables rebuilt with 2 columns")


# ─── STEP 2: Insert "How the ABSA analysis works" slide before current 18 ─
layout = p.slide_masters[0].slide_layouts[3]
new_slide = p.slides.add_slide(layout)
# Remove picture + content placeholders
for shape in list(new_slide.shapes):
    try:
        if shape.placeholder_format is not None and shape.placeholder_format.idx in (10, 11):
            shape._element.getparent().remove(shape._element)
    except Exception:
        pass

# Title
title = new_slide.shapes.title
title.left = Inches(0.45); title.top = Inches(0.40)
title.width = Inches(11.5); title.height = Inches(0.95)
ttf = title.text_frame; ttf.clear()
p_en = ttf.paragraphs[0]
p_en.text = "How the aspect-level analysis works"
p_en.alignment = PP_ALIGN.LEFT
for run in p_en.runs: _font(run, FONT_HEAD)
p_ko = ttf.add_paragraph()
p_ko.text = "측면 수준 분석의 작동 방식"
p_ko.alignment = PP_ALIGN.LEFT
for run in p_ko.runs: _font(run, FONT_HEAD, 20)

# Slide number box
sn = new_slide.shapes.add_textbox(Inches(9.33), Inches(6.69), Inches(3.0), Inches(0.40))
sn.text_frame.paragraphs[0].text = ""


# Five rounded boxes in a vertical pipeline with downward arrows
PIPELINE = [
    ("Step 1 — Review corpus",
     "1단계 — 리뷰 코퍼스",
     "11,164 Korean reviews with text (≥ 10 chars)   ·   source:  naver_dataset.csv"),
    ("Step 2 — LLM aspect classifier",
     "2단계 — LLM 측면 분류기",
     "Qwen2.5-7B-Instruct (4-bit)  ·  06_llm_analysis.py --naver  ·  prompt + 3 few-shot examples"),
    ("Step 3 — Six aspect labels per review",
     "3단계 — 리뷰당 여섯 측면 라벨",
     "historical/cultural · accessibility · crowding · food · visual/photo · service/experience   —   each scored −1 / 0 / +1"),
    ("Step 4 — Post-hoc validation of the aspect set",
     "4단계 — 측면 집합의 사후 검증",
     "LDA at optimal K = 6 (coherence c_v = 0.520)  +  BERTopic (K = 15, multilingual E5 embeddings)   →   5/6 aspects emerge as topics"),
    ("Step 5 — Regressions (§4.6)",
     "5단계 — 회귀분석 (§4.6)",
     "ABSA-A: six logistic regressions  —  mentions_aspect  ~  visit context + reviewer controls + δⱼ    (place FE,  SE clustered by reviewer)"),
]

TOP_Y = 1.55
BOX_H = 0.82
GAP   = 0.20
LEFT  = 1.0
WIDTH = 11.3

for i, (en, ko, desc) in enumerate(PIPELINE):
    y = TOP_Y + i * (BOX_H + GAP)
    box = new_slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                      Inches(LEFT), Inches(y),
                                      Inches(WIDTH), Inches(BOX_H))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = LINE_GREY; box.line.width = Emu(12700)
    box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.15); tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.05); tf.margin_bottom = Inches(0.05)
    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.LEFT
    p1.text = f"{en}      /      {ko}"
    for run in p1.runs: _font(run, FONT_HEAD, 12, bold=True, color=DARK)
    p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.LEFT
    p2.text = desc
    for run in p2.runs: _font(run, FONT_BODY, 10, color=DARK)
    # Downward arrow between boxes
    if i < len(PIPELINE) - 1:
        ax = LEFT + WIDTH / 2
        y1 = y + BOX_H
        y2 = y1 + GAP
        arr = new_slide.shapes.add_connector(1, Inches(ax), Inches(y1),
                                              Inches(ax), Inches(y2))
        arr.line.color.rgb = LINE_GREY; arr.line.width = Emu(19050)

# Move the new slide (currently at the end) to position 18 (0-index 17),
# so it lands immediately BEFORE the current Aspect-level results slide.
xml_slides = p.slides._sldIdLst
slides_list = list(xml_slides)
new_elem = slides_list[-1]
xml_slides.remove(new_elem)
xml_slides.insert(17, new_elem)
print("  Slide 18 (NEW): How ABSA works pipeline — inserted before Aspect-level results")


p.save(PPTX)
print(f"\nOK. Total slides: {len(p.slides)}.")
