"""
fix_slides_17_18.py
Fix the earlier mistake where rebuild_slide18_findings.py targeted index 17
(Aspect-level analysis) instead of index 16 (Main findings M1-M4).

Steps:
  1. On slide 18 (Aspect-level, index 17): remove the misplaced M1-M4 tables
     and legend text boxes; restore the aspect-level body text.
  2. On slide 17 (Main findings, index 16): remove the current bullet-text
     Content Placeholder and add the four mini-tables (M1-M4) in a 2x2 grid.

Only slides 17 and 18 are touched. Everything else is preserved.

Run (base env):  python fix_slides_17_18.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX = "presentation_build.pptx"
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


# ─── STEP 1: Restore slide 18 (Aspect-level analysis) ─────────────────────
slide18 = p.slides[17]
# Remove everything except the Title placeholder (idx 0) and any Slide Number
# placeholder (idx 4).
removed = 0
for shape in list(slide18.shapes):
    try:
        pf = shape.placeholder_format
        if pf is not None and pf.idx in (0, 4):
            continue  # keep title and slide number
    except Exception:
        pass
    # Remove any text box, table, etc. that I added
    shape._element.getparent().remove(shape._element)
    removed += 1
print(f"  Slide 18: removed {removed} shapes (misplaced M1-M4 content)")

# Add back the Aspect-level body as a single text box
aspect_tb = slide18.shapes.add_textbox(Inches(0.45), Inches(1.60),
                                        Inches(12.4), Inches(5.0))
atf = aspect_tb.text_frame
atf.word_wrap = True

aspect_body = [
    ("ABSA labels on six dimensions (LLM, 06_llm_analysis.py): historical/cultural "
     "(50.4%), visual (63.8%), service/experience (27.4%), accessibility (19.8%), "
     "crowding (16.3%), food (6.9%).", True),
    ("LLM 기반 분류기로 여섯 가지 측면 라벨링: 역사·문화 50.4%, 시각 63.8%, "
     "서비스·체험 27.4%, 접근성 19.8%, 혼잡 16.3%, 음식 6.9%.", False),
    ("", True),
    ("Six aspects specified a priori and validated post-hoc against unsupervised "
     "topic extraction (LDA at optimal K = 6, BERTopic K = 15). All six except "
     "crowding emerge as distinct topics; crowding is retained as polarity-dominated "
     "(18.1% of mentions negative, the highest).", True),
    ("여섯 측면은 사전 지정, 비지도 토픽 추출(LDA K = 6, BERTopic K = 15)로 사후 검증. "
     "혼잡은 극성 중심의 차원이므로 유지.", False),
    ("", True),
    ("Four findings from the \"who mentions what\" regressions:", True),
    ("  (1) Children drive narrative-rich reviews across historical, accessibility "
     "and service (ORs 1.22–1.55).", True),
    ("  (2) Service friction splits two ways: waited → crowding (OR 2.13 ***); "
     "reserved → crowding ↓ 0.69 ** but service/experience ↑ 2.39 ***.", True),
    ("  (3) Date-purpose raises food mentions by 51% (OR 1.51 *); alone visits "
     "lower them (OR 0.64 *).", True),
    ("  (4) Service/experience is empirically distinct (pseudo-R² = 0.371), with "
     "structurally different predictors.", True),
    ("  (1) 아이와 방문: 다양한 측면의 언급 증가. (2) 대기 → 혼잡 ↑, 예약 → 서비스 ↑ "
     "혼잡 ↓. (3) 데이트 → 음식 ↑, 혼자 → 음식 ↓. (4) 서비스·체험은 독립 차원.", False),
    ("", True),
    ("Reactions by aspect content: no aspect reaches p < .05 after controls. "
     "Engagement is driven by reviewer identity (followers, revisitor, text length), "
     "not by review content.", True),
    ("아스펙트 내용과 반응: 통제 후 p < .05 도달하는 측면 없음. 몰입은 작성자 특성에 "
     "의해 좌우된다.", False),
]
for i, (text, is_en) in enumerate(aspect_body):
    para = atf.paragraphs[0] if i == 0 else atf.add_paragraph()
    para.text = text
    para.alignment = PP_ALIGN.LEFT
    for run in para.runs:
        _font(run, FONT_BODY)
        if not is_en and text.strip():
            run.font.size = Pt(12)
print("  Slide 18: aspect-level body restored")


# ─── STEP 2: Rebuild slide 17 (Main findings M1-M4) with 4 tables ─────────
slide17 = p.slides[16]
removed = 0
for shape in list(slide17.shapes):
    try:
        pf = shape.placeholder_format
        if pf is not None and pf.idx == 0:
            continue  # keep title
        if pf is not None and pf.idx == 4:
            continue  # keep slide number
    except Exception:
        pass
    # Delete content placeholder (idx 11) with the bullet-text summary
    # Also any legacy text boxes.
    try:
        pf = shape.placeholder_format
        if pf is not None and pf.idx == 11:
            shape._element.getparent().remove(shape._element); removed += 1; continue
    except Exception:
        pass
    # Keep "TextBox 3" (slide-number stand-in) if present at bottom-right
    if shape.has_text_frame and shape.name == "Content Placeholder 2":
        shape._element.getparent().remove(shape._element); removed += 1
print(f"  Slide 17: removed {removed} old body shape(s)")

M1 = {
    "title_en": "M1 Revisit",  "title_ko": "재방문",
    "subtitle": "Logistic · N = 11,165 · AUC 0.773 · pseudo-R² 0.203",
    "metric": "OR",
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
    "title_en": "M2 Keyword Count", "title_ko": "키워드 수",
    "subtitle": "Ordered logistic · N = 14,401 · RMSE 1.37 (base 1.88)",
    "metric": "OR",
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
    "title_en": "M3 Rating  (exploratory)", "title_ko": "별점 (탐색적)",
    "subtitle": "Ordered logistic · N = 4,651 · 73.9% five-star · McFadden R² 0.095",
    "metric": "OR",
    "rows": [
        ("Keyword Count (0–5)",          "1.56  [1.45, 1.69]", "***"),
        ("Revisitor (2+ visits)",        "1.37  [1.03, 1.82]", "*"),
        ("Wrote text  (text-only spec)", "0.64  [0.49, 0.83]", "***"),
        ("Sentiment  (text-only spec)",  "4.90  [3.52, 6.82]", "***"),
    ],
    "note": "Reported as exploratory: ratings move little across the corpus.",
}
M4 = {
    "title_en": "M4 Reactions", "title_ko": "반응 수",
    "subtitle": "Negative binomial · N = 11,165 · AUC any-reaction 0.815 · α̂ = 2.44",
    "metric": "IRR",
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

GRID = [
    (0.45, 1.55, M1),
    (6.85, 1.55, M2),
    (0.45, 4.05, M3),
    (6.85, 4.05, M4),
]
TABLE_W = 6.0


def place_model_table(slide, x_in, y_in, data):
    title_tb = slide.shapes.add_textbox(Inches(x_in), Inches(y_in),
                                        Inches(TABLE_W), Inches(0.35))
    tp = title_tb.text_frame.paragraphs[0]
    tp.text = f"{data['title_en']}  /  {data['title_ko']}"
    tp.alignment = PP_ALIGN.LEFT
    for run in tp.runs: _font(run, FONT_HEAD, 13, bold=True, color=DARK)

    sub_tb = slide.shapes.add_textbox(Inches(x_in), Inches(y_in + 0.33),
                                       Inches(TABLE_W), Inches(0.26))
    sp = sub_tb.text_frame.paragraphs[0]
    sp.text = data["subtitle"]; sp.alignment = PP_ALIGN.LEFT
    for run in sp.runs: _font(run, FONT_BODY, 9, italic=True, color=MUTED)

    n_rows = 1 + len(data["rows"])
    tbl_shape = slide.shapes.add_table(n_rows, 3,
                                        Inches(x_in), Inches(y_in + 0.60),
                                        Inches(TABLE_W),
                                        Inches(min(1.55, 0.22 * n_rows + 0.10)))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(3.20)
    tbl.columns[1].width = Inches(2.20)
    tbl.columns[2].width = Inches(0.60)
    _cell(tbl.cell(0, 0), "Variable", bold=True, size=10, fill=HEADER_FILL)
    _cell(tbl.cell(0, 1), f"{data['metric']}  [95% CI]", bold=True, size=10, fill=HEADER_FILL)
    _cell(tbl.cell(0, 2), "p", bold=True, size=10, fill=HEADER_FILL, align_left=False)
    for i, (var, val, stars) in enumerate(data["rows"], start=1):
        fill = WHITE if i % 2 == 1 else ALT_FILL
        _cell(tbl.cell(i, 0), var, size=10, fill=fill)
        _cell(tbl.cell(i, 1), val, size=10, fill=fill)
        _cell(tbl.cell(i, 2), stars, size=10, fill=fill, align_left=False)
    if "note" in data:
        note_y = y_in + 0.60 + 0.22 * n_rows + 0.05
        note_tb = slide.shapes.add_textbox(Inches(x_in), Inches(note_y),
                                            Inches(TABLE_W), Inches(0.25))
        np = note_tb.text_frame.paragraphs[0]
        np.text = data["note"]; np.alignment = PP_ALIGN.LEFT
        for run in np.runs: _font(run, FONT_BODY, 8, italic=True, color=MUTED)


for x_in, y_in, data in GRID:
    place_model_table(slide17, x_in, y_in, data)

legend = slide17.shapes.add_textbox(Inches(0.45), Inches(6.70),
                                      Inches(12.4), Inches(0.26))
lp = legend.text_frame.paragraphs[0]
lp.text = ("Significance:  *** p < .001   ·   ** p < .01   ·   * p < .05.      "
            "OR = odds ratio;  IRR = incidence rate ratio;  all models include "
            "place fixed effects and standard errors clustered by reviewer.")
lp.alignment = PP_ALIGN.LEFT
for run in lp.runs: _font(run, FONT_BODY, 9, italic=True, color=MUTED)
print("  Slide 17: 4 mini-tables (M1-M4) + legend added")


p.save(PPTX)
print(f"\nOK. Total slides: {len(p.slides)} (unchanged).")
