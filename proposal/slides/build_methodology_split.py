"""
build_methodology_split.py
Replace the combined 'Variables and Models' slide with three separate
methodology slides, matching the structure of the paper and resumen:
  - Slide 12 (new): Research Framework diagram
  - Slide 13 (new): Variables  (mirrors \tblVariables in paper)
  - Slide 14 (new): Models     (M1-M4 with explicit equations)

Everything after (Results, Conclusion, Closing) is kept and renumbered
automatically by PowerPoint.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX = "presentation_build.pptx"
FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
MONO = "Consolas"

LINE_GREY = RGBColor(0x95, 0x95, 0x95)
FILL_LIGHT = RGBColor(0xF4, 0xF4, 0xF4)
FILL_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_DARK = RGBColor(0x22, 0x22, 0x22)


# ─── helpers ──────────────────────────────────────────────────────────────
def _put_title(slide, en, ko):
    """Place a bilingual title at the top-left (Slide 4 geometry)."""
    title = slide.shapes.title
    title.left = Inches(0.45)
    title.top = Inches(0.40)
    title.width = Inches(11.5)
    title.height = Inches(0.95)
    tf = title.text_frame
    tf.clear()
    p_en = tf.paragraphs[0]
    p_en.text = en
    for run in p_en.runs:
        run.font.name = FONT_HEAD
    p_ko = tf.add_paragraph()
    p_ko.text = ko
    for run in p_ko.runs:
        run.font.name = FONT_HEAD
        run.font.size = Pt(20)


def _remove_picture_ph(slide):
    for shape in list(slide.shapes):
        if shape.has_text_frame:
            continue
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == 10:
                shape._element.getparent().remove(shape._element)
        except Exception:
            pass


def _remove_body_ph(slide):
    """Remove the body (Content Placeholder) so we can custom-layout."""
    title = slide.shapes.title
    for shape in list(slide.shapes):
        if shape is title:
            continue
        if shape.has_text_frame:
            try:
                if shape.placeholder_format is not None and shape.placeholder_format.idx == 11:
                    shape._element.getparent().remove(shape._element)
            except Exception:
                pass


def _add_slide_number(slide):
    sn = slide.shapes.add_textbox(Inches(9.33), Inches(6.69), Inches(3.0), Inches(0.40))
    sn.text_frame.paragraphs[0].text = ""


# ─── SLIDE 12: Research Framework diagram ────────────────────────────────
def build_framework_slide(prs):
    layout = prs.slide_masters[0].slide_layouts[3]  # Title text and image
    slide = prs.slides.add_slide(layout)
    _remove_picture_ph(slide)
    _remove_body_ph(slide)
    _put_title(slide, "Research Framework", "연구 프레임워크")
    _add_slide_number(slide)

    # Three stacked rounded rectangles connected by arrows
    def box(x, y, w, h, title_en, title_ko, body_lines):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                       Inches(x), Inches(y), Inches(w), Inches(h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = FILL_WHITE
        shape.line.color.rgb = LINE_GREY
        shape.line.width = Emu(12700)  # ~1pt
        shape.shadow.inherit = False
        tf = shape.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.15)
        tf.margin_right = Inches(0.15)
        tf.margin_top = Inches(0.08)
        tf.margin_bottom = Inches(0.08)
        # Title line (EN + KO)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        p.text = f"{title_en}  /  {title_ko}"
        for run in p.runs:
            run.font.name = FONT_HEAD
            run.font.bold = True
            run.font.size = Pt(14)
            run.font.color.rgb = TEXT_DARK
        for line in body_lines:
            para = tf.add_paragraph()
            para.text = line
            para.alignment = PP_ALIGN.LEFT
            for run in para.runs:
                run.font.name = FONT_BODY
                run.font.size = Pt(11)
                run.font.color.rgb = TEXT_DARK

    # Data block
    box(1.5, 1.55, 10.3, 1.25, "Data Acquisition", "데이터 수집", [
        "Naver Place scraper  →  29 attractions · 14,401 reviews · 8,276 reviewers",
        "11,165 with text  ·  Yanolja Top 500 ∩ KTO visitor volume  ·  Seoul (25) + Busan (4)",
    ])
    # Arrow 1
    arr1 = slide.shapes.add_connector(1, Inches(6.65), Inches(2.80), Inches(6.65), Inches(3.10))
    arr1.line.color.rgb = LINE_GREY
    arr1.line.width = Emu(19050)  # 1.5pt

    # Variables block
    box(1.5, 3.10, 10.3, 1.80, "Variables", "변수", [
        "DV (4):  Revisit · Keyword Count (0–5) · Rating (1–5) · Reactions",
        "IV:  Visit Context (companion · purpose · wait · reservation)  +  Sentiment  +  Aspect dummies (§4.6)",
        "Controls:  text length · reviewer history · followers · review age · season · weekend · verification",
        "Fixed effects:  Place (δⱼ)   ·   Standard errors clustered by reviewer",
    ])
    # Arrow 2
    arr2 = slide.shapes.add_connector(1, Inches(6.65), Inches(4.90), Inches(6.65), Inches(5.20))
    arr2.line.color.rgb = LINE_GREY
    arr2.line.width = Emu(19050)

    # Models block
    box(1.5, 5.20, 10.3, 1.25, "Models", "모형", [
        "M1 Revisit  (logistic)   ·   M2 Keyword Count  (ordered logistic)",
        "M3 Rating  (ordered logistic, exploratory)   ·   M4 Reactions  (negative binomial)",
    ])
    return slide


# ─── SLIDE 13: Variables (table) ──────────────────────────────────────────
def build_variables_slide(prs):
    layout = prs.slide_masters[0].slide_layouts[3]
    slide = prs.slides.add_slide(layout)
    _remove_picture_ph(slide)
    _remove_body_ph(slide)
    _put_title(slide, "Variables", "변수")
    _add_slide_number(slide)

    rows_data = [
        ("Role",         "Variable",             "Description"),
        ("DV",           "Revisit  재방문",        "binary — 2+ visits (0/1)"),
        ("DV",           "Keyword Count  키워드 수", "ordinal 0–5 — information diversity"),
        ("DV",           "Rating  별점",           "ordinal 1–5 stars (exploratory)"),
        ("DV",           "Reactions  반응 수",     "count — reader interactions (helpfulness proxy)"),
        ("IV",           "Companion  동반자",      "6 dummies: alone, partner, friends, children, family, colleagues"),
        ("IV",           "Purpose  방문 목적",     "5 dummies: travel, outing, daily, date, social"),
        ("IV",           "Waited  대기 경험",      "binary — queued before entry"),
        ("IV",           "Reserved  사전 예약",    "binary — advance reservation"),
        ("IV",           "Sentiment  감성 점수",   "continuous (−1 to +1), BERT-based (Karabila et al. 2024)"),
        ("IV",           "Aspect mentions  측면 언급", "6 dummies (ABSA, §4.6 only)"),
        ("Control",      "Text length, images",   "ln(chars), image count"),
        ("Control",      "Reviewer activity",     "ln(reviews), ln(followers)"),
        ("Control",      "Review age",            "ln(days since post)"),
        ("Control",      "Season / Weekend / Verification", "dummies"),
        ("Control",      "Place FE  δⱼ",           "28 place dummies (reference: Gyeongbokgung)"),
    ]
    n_rows = len(rows_data)
    n_cols = 3
    left   = Inches(0.60)
    top    = Inches(1.60)
    width  = Inches(12.1)
    height = Inches(5.0)

    table_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    tbl = table_shape.table
    # Column widths
    tbl.columns[0].width = Inches(1.3)
    tbl.columns[1].width = Inches(3.7)
    tbl.columns[2].width = Inches(7.1)

    for i, row in enumerate(rows_data):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            tf = cell.text_frame
            tf.word_wrap = True
            tf.clear()
            p = tf.paragraphs[0]
            p.text = val
            for run in p.runs:
                run.font.name = FONT_BODY
                run.font.size = Pt(11)
                if i == 0:
                    run.font.bold = True
                    run.font.size = Pt(12)
            # Alternate row shading
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(0xE8, 0xE8, 0xE8)
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = FILL_WHITE if i % 2 == 1 else RGBColor(0xF8, 0xF8, 0xF8)

    return slide


# ─── SLIDE 14: Models (explicit equations) ────────────────────────────────
def build_models_slide(prs):
    layout = prs.slide_masters[0].slide_layouts[3]
    slide = prs.slides.add_slide(layout)
    _remove_picture_ph(slide)
    _remove_body_ph(slide)
    _put_title(slide, "Models", "모형")
    _add_slide_number(slide)

    # Intro line
    intro = slide.shapes.add_textbox(Inches(0.45), Inches(1.50), Inches(12.4), Inches(0.60))
    tf = intro.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = ("Four models — each matching the measurement scale of its outcome.  "
              "All include place fixed effects δⱼ; standard errors clustered by reviewer.")
    for run in p.runs:
        run.font.name = FONT_BODY
        run.font.size = Pt(12)
    p2 = tf.add_paragraph()
    p2.text = ("네 가지 모형 — 각 종속변수의 측정 척도에 맞춤.  "
               "모두 관광지 고정효과 δⱼ 포함; 표준오차는 작성자 단위로 클러스터링.")
    for run in p2.runs:
        run.font.name = FONT_BODY
        run.font.size = Pt(10)

    # Equation box content
    eqs = slide.shapes.add_textbox(Inches(0.45), Inches(2.35), Inches(12.4), Inches(4.2))
    tf = eqs.text_frame
    tf.word_wrap = True

    def _addline(text, *, bold=False, mono=False, size=12, para_idx=None, before_space=False):
        if para_idx == 0:
            para = tf.paragraphs[0]
        else:
            para = tf.add_paragraph()
        if before_space:
            para.space_before = Pt(6)
        para.text = text
        for run in para.runs:
            run.font.name = MONO if mono else FONT_BODY
            run.font.size = Pt(size)
            run.font.bold = bold

    # M1
    _addline("M1  Revisit  (binary)   →   logistic regression",
             bold=True, size=12, para_idx=0)
    _addline("        logit  P(Revisit_ij)  =  β₀  +  x_ij′ β  +  δⱼ",
             mono=True, size=12)

    # M2
    _addline("M2  Keyword Count  (ordinal 0–5)   →   ordered logistic",
             bold=True, size=12, before_space=True)
    _addline("        P(KC_ij ≤ k)  =  [ 1 + exp(−(τ_k − x_ij′ β − δⱼ)) ]⁻¹      k = 0, …, 4",
             mono=True, size=12)
    _addline("        (ordinal, not count:  the 0–5 range is platform-capped at five, not Poisson-generated)",
             size=10)

    # M3
    _addline("M3  Rating  (ordinal 1–5)   →   ordered logistic (exploratory)",
             bold=True, size=12, before_space=True)
    _addline("        P(Rating_ij ≤ k)  =  [ 1 + exp(−(τ_k − x_ij′ β − δⱼ)) ]⁻¹      k = 1, …, 4",
             mono=True, size=12)

    # M4
    _addline("M4  Reactions  (overdispersed count)   →   negative binomial",
             bold=True, size=12, before_space=True)
    _addline("        Reactions_ij  ~  NegBin(μ_ij, α)",
             mono=True, size=12)
    _addline("        ln μ_ij  =  β₀  +  x_ij′ β  +  γ · ln(Age_ij)  +  δⱼ",
             mono=True, size=12)
    _addline("        (ln(Age) enters as an exposure offset — not a regular β — because reactions "
             "accumulate over time)",
             size=10)

    # Legend
    legend = slide.shapes.add_textbox(Inches(0.45), Inches(6.30), Inches(12.4), Inches(0.35))
    ltf = legend.text_frame
    lp = ltf.paragraphs[0]
    lp.text = ("x_ij = regressor vector (visit context + sentiment + controls)   ·   "
               "β = coefficients   ·   δⱼ = place FE   ·   τ_k = ordered-logit thresholds   ·   "
               "γ = log-age elasticity (M4 offset)   ·   α = NB dispersion (α̂ = 2.44)")
    for run in lp.runs:
        run.font.name = FONT_BODY
        run.font.size = Pt(9)
        run.font.italic = True
    return slide


# ─── Delete current slide 12 and insert the three new slides at position 12 ─
p = Presentation(PPTX)
total_before = len(p.slides)

xml_slides = p.slides._sldIdLst
slides_list = list(xml_slides)
# Current slide 12 is 0-indexed 11
old_slide_12 = slides_list[11]
xml_slides.remove(old_slide_12)
print(f"Removed old slide 12 (combined Variables and Models).")

# Build three new slides (appended at the end)
build_framework_slide(p)
build_variables_slide(p)
build_models_slide(p)

# Move them to positions 12, 13, 14 (0-indexed 11, 12, 13)
xml_slides = p.slides._sldIdLst
slides_list = list(xml_slides)
new_fw, new_var, new_mod = slides_list[-3], slides_list[-2], slides_list[-1]
for s in (new_fw, new_var, new_mod):
    xml_slides.remove(s)
xml_slides.insert(11, new_fw)
xml_slides.insert(12, new_var)
xml_slides.insert(13, new_mod)

p.save(PPTX)
print(f"OK. {PPTX} slides: {total_before} -> {len(p.slides)}")
print("  Slide 12: Research Framework diagram")
print("  Slide 13: Variables (full table)")
print("  Slide 14: Models (M1-M4 explicit equations)")
print("  (Results, Conclusion, Closing shift to 15-20)")
