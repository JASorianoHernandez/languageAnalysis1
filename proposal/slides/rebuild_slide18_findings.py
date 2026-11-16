"""
rebuild_slide18_findings.py
Rebuild ONLY slide 18 (Main findings M1-M4) with four mini-tables in a 2x2
grid, replicating the per-model result tables from report_naver.tex §4.1–4.4.

The slide title, slide number and layout are preserved. Only the body
Content Placeholder (which held the previous bullet-text summary) is
replaced with the four tables. No other slide is touched.

Run (base env):  python rebuild_slide18_findings.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX       = "presentation_build.pptx"
SLIDE_IDX  = 17   # 0-indexed: slide 18
FONT_HEAD  = "Source Sans"
FONT_BODY  = "Source Sans Pro Light"
HEADER_FILL = RGBColor(0xE8, 0xE8, 0xE8)
ALT_FILL    = RGBColor(0xF8, 0xF8, 0xF8)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
DARK        = RGBColor(0x22, 0x22, 0x22)
MUTED       = RGBColor(0x55, 0x55, 0x55)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None:  run.font.size = Pt(size)
    if bold is not None:  run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


def _cell(cell, text, bold=False, size=10, fill=None, align_left=True):
    cell.margin_left = Inches(0.06)
    cell.margin_right = Inches(0.06)
    cell.margin_top = Inches(0.02)
    cell.margin_bottom = Inches(0.02)
    tf = cell.text_frame
    tf.word_wrap = True
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.LEFT if align_left else PP_ALIGN.CENTER
    for run in p.runs:
        _font(run, FONT_BODY, size, bold=bold)
    if fill is not None:
        cell.fill.solid()
        cell.fill.fore_color.rgb = fill


# ─── Per-model data (from report §4.1-4.4) ────────────────────────────────
# Each table: (model title EN, model title KO, subtitle_line, header, rows)
# Each row is (variable, OR_or_IRR_with_CI, p_stars)

M1 = {
    "title_en": "M1 Revisit",
    "title_ko": "재방문",
    "subtitle": "Logistic · N = 11,165 · AUC 0.773 · pseudo-R² 0.203",
    "metric":   "OR",
    "rows": [
        ("ln(1 + reviewer's reviews)", "1.52  [1.40, 1.65]", "***"),
        ("With: alone",                "1.68  [1.18, 2.39]", "**"),
        ("With: friends",              "0.58  [0.42, 0.80]", "**"),
        ("Waited to enter",            "0.51  [0.35, 0.72]", "***"),
        ("Sentiment  (−1 to +1)",      "0.70  [0.60, 0.81]", "***"),
        ("Purpose: travel",            "0.56  [0.42, 0.75]", "***"),
        ("ln(text length)",            "1.29  [1.14, 1.47]", "***"),
    ],
}

M2 = {
    "title_en": "M2 Keyword Count",
    "title_ko": "키워드 수",
    "subtitle": "Ordered logistic · N = 14,401 · RMSE 1.37 (base 1.88)",
    "metric":   "OR",
    "rows": [
        ("Wrote text (15+ chars)",     "4.02  [3.51, 4.60]", "***"),
        ("Visit info provided",        "2.53  [2.01, 3.18]", "***"),
        ("Revisitor (2+ visits)",      "1.60  [1.32, 1.93]", "***"),
        ("Purpose: outing",            "1.85  [1.60, 2.13]", "***"),
        ("Purpose: travel",            "1.73  [1.49, 2.02]", "***"),
        ("With: alone",                "1.67  [1.27, 2.20]", "***"),
        ("Waited to enter",            "0.75  [0.64, 0.88]", "***"),
    ],
}

M3 = {
    "title_en": "M3 Rating  (exploratory)",
    "title_ko": "별점 (탐색적)",
    "subtitle": "Ordered logistic · N = 4,651 · 73.9% five-star · McFadden R² 0.095",
    "metric":   "OR",
    "rows": [
        ("Keyword Count (0–5)",         "1.56  [1.45, 1.69]", "***"),
        ("Revisitor (2+ visits)",       "1.37  [1.03, 1.82]", "*"),
        ("Wrote text  (text-only spec)","0.64  [0.49, 0.83]", "***"),
        ("Sentiment  (text-only spec)", "4.90  [3.52, 6.82]", "***"),
    ],
    "note": "Reported as exploratory: ratings move little across the corpus.",
}

M4 = {
    "title_en": "M4 Reactions",
    "title_ko": "반응 수",
    "subtitle": "Negative binomial · N = 11,165 · AUC any-reaction 0.815 · α̂ = 2.44",
    "metric":   "IRR",
    "rows": [
        ("ln(1 + reviewer's followers)", "1.97  [1.79, 2.18]", "***"),
        ("ln(text length)",              "1.64  [1.44, 1.87]", "***"),
        ("Keyword tags (0–5)",           "1.12  [1.05, 1.20]", "**"),
        ("Sentiment  (−1 to +1)",        "0.77  [0.64, 0.91]", "**"),
        ("Visit info provided",          "1.70  [1.08, 2.68]", "*"),
        ("Visit: autumn",                "0.71  [0.61, 0.83]", "***"),
        ("Purpose: outing",              "0.63  [0.45, 0.88]", "**"),
    ],
}


# ─── Open deck, locate slide 18, scrub only its content placeholder ──────
p = Presentation(PPTX)
slide = p.slides[SLIDE_IDX]

# Find and remove the Content Placeholder (idx 11), keep title + slide number
to_remove = []
for shape in slide.shapes:
    try:
        if shape.placeholder_format is not None and shape.placeholder_format.idx == 11:
            to_remove.append(shape)
    except Exception:
        pass
# Also remove any body text box that may have been inserted (same role)
for shape in slide.shapes:
    if shape.has_text_frame and shape.name == "Content Placeholder 6":
        if shape not in to_remove:
            to_remove.append(shape)

for shape in to_remove:
    shape._element.getparent().remove(shape._element)
    print(f"  Removed body shape: {shape.name}")


# ─── Lay out 4 mini-tables in a 2x2 grid ─────────────────────────────────
# Slide area usable:  0.45–12.85 wide (= 12.4") , 1.60–6.60 tall (= 5.0")
# Grid: two columns, two rows.
#   Column widths: 6.00" each, 0.40" gap
#   Row heights: 2.30" each, 0.20" gap
GRID = [
    (0.45, 1.55, M1),   # top-left
    (6.85, 1.55, M2),   # top-right
    (0.45, 4.05, M3),   # bottom-left
    (6.85, 4.05, M4),   # bottom-right
]
TABLE_W = 6.0


def place_model_table(slide, x_in, y_in, data):
    # Title line above the table
    title_tb = slide.shapes.add_textbox(Inches(x_in), Inches(y_in),
                                        Inches(TABLE_W), Inches(0.35))
    ttf = title_tb.text_frame
    ttf.word_wrap = True
    tp = ttf.paragraphs[0]
    tp.text = f"{data['title_en']}  /  {data['title_ko']}"
    tp.alignment = PP_ALIGN.LEFT
    for run in tp.runs:
        _font(run, FONT_HEAD, 13, bold=True, color=DARK)

    # Subtitle: fit stats
    sub_tb = slide.shapes.add_textbox(Inches(x_in), Inches(y_in + 0.33),
                                       Inches(TABLE_W), Inches(0.26))
    stf = sub_tb.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.text = data["subtitle"]
    sp.alignment = PP_ALIGN.LEFT
    for run in sp.runs:
        _font(run, FONT_BODY, 9, italic=True, color=MUTED)

    # Table proper: header + rows
    n_rows = 1 + len(data["rows"])
    tbl_top = Inches(y_in + 0.60)
    tbl_h = Inches(min(1.55, 0.22 * n_rows + 0.10))
    tbl_shape = slide.shapes.add_table(n_rows, 3,
                                        Inches(x_in), tbl_top,
                                        Inches(TABLE_W), tbl_h)
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(3.20)   # Variable
    tbl.columns[1].width = Inches(2.20)   # OR/IRR [CI]
    tbl.columns[2].width = Inches(0.60)   # significance stars

    # Header
    _cell(tbl.cell(0, 0), "Variable",            bold=True, size=10, fill=HEADER_FILL)
    _cell(tbl.cell(0, 1), f"{data['metric']}  [95% CI]", bold=True, size=10, fill=HEADER_FILL)
    _cell(tbl.cell(0, 2), "p",                   bold=True, size=10, fill=HEADER_FILL, align_left=False)

    # Rows
    for i, (var, val, stars) in enumerate(data["rows"], start=1):
        fill = WHITE if i % 2 == 1 else ALT_FILL
        _cell(tbl.cell(i, 0), var,   size=10, fill=fill)
        _cell(tbl.cell(i, 1), val,   size=10, fill=fill)
        _cell(tbl.cell(i, 2), stars, size=10, fill=fill, align_left=False)

    # Optional note below the table (M3)
    if "note" in data:
        note_y = y_in + 0.60 + 0.22 * n_rows + 0.05
        note_tb = slide.shapes.add_textbox(Inches(x_in), Inches(note_y),
                                            Inches(TABLE_W), Inches(0.25))
        nnf = note_tb.text_frame
        nnf.word_wrap = True
        np = nnf.paragraphs[0]
        np.text = data["note"]
        np.alignment = PP_ALIGN.LEFT
        for run in np.runs:
            _font(run, FONT_BODY, 8, italic=True, color=MUTED)


for x_in, y_in, data in GRID:
    place_model_table(slide, x_in, y_in, data)


# Significance legend at the bottom of the slide
legend = slide.shapes.add_textbox(Inches(0.45), Inches(6.70),
                                   Inches(12.4), Inches(0.26))
ltf = legend.text_frame
lp = ltf.paragraphs[0]
lp.text = ("Significance:  *** p < .001   ·   ** p < .01   ·   * p < .05.      "
           "OR = odds ratio;  IRR = incidence rate ratio;  all models include place fixed effects "
           "and standard errors clustered by reviewer.")
lp.alignment = PP_ALIGN.LEFT
for run in lp.runs:
    _font(run, FONT_BODY, 9, italic=True, color=MUTED)


p.save(PPTX)
print(f"\nOK. Slide {SLIDE_IDX + 1} rebuilt with 4 mini-tables (M1, M2, M3, M4).")
print(f"Total slides: {len(p.slides)} (unchanged).")
