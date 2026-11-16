"""
build_all.py
Single consolidated builder for the Naver Place presentation. Takes a fresh
copy of templateppt.pptx (presentation_build.pptx) and applies all sections
in order, WITHOUT any slide deletion (which triggers python-pptx's
duplicate-name bug). Produces 20 slides.

Order of operations:
  1. Fix title slide (slide 1)
  2. Replace slide 4 body (Introduction) + add [1] footnote
  3. Add slide 5 (Research Questions) after slide 4
  4. Update slides 7, 8, 9 (Theoretical Background)
  5. Add slides 11, 12, 13, 14 (Data, Framework, Variables, Models) after slide 10
  6. Add slides 15-20 (Results section + Conclusion + Closing)

Run from this directory (base env):  python build_all.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

PPTX       = "presentation_build.pptx"
FONT_HEAD  = "Source Sans"
FONT_BODY  = "Source Sans Pro Light"
MONO       = "Consolas"
LINE_GREY  = RGBColor(0x95, 0x95, 0x95)
FILL_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_DARK  = RGBColor(0x22, 0x22, 0x22)

# ─── Generic helpers ─────────────────────────────────────────────────────
def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


def _set_title_top(slide, title_en, title_ko):
    """Place a bilingual title at the top-left (Slide 4 geometry)."""
    title = slide.shapes.title
    title.left = Inches(0.45); title.top = Inches(0.40)
    title.width = Inches(11.5); title.height = Inches(0.95)
    tf = title.text_frame
    tf.clear()
    p_en = tf.paragraphs[0]; p_en.text = title_en
    for run in p_en.runs: _font(run, FONT_HEAD)
    p_ko = tf.add_paragraph(); p_ko.text = title_ko
    for run in p_ko.runs: _font(run, FONT_HEAD, 20)


def _remove_ph(slide, idx):
    for shape in list(slide.shapes):
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == idx:
                shape._element.getparent().remove(shape._element)
        except Exception:
            pass


def _add_slide_number(slide):
    sn = slide.shapes.add_textbox(Inches(9.33), Inches(6.69), Inches(3.0), Inches(0.40))
    sn.text_frame.paragraphs[0].text = ""


def _apply_body(shape, body_items):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.clear()
    for i, item in enumerate(body_items):
        if isinstance(item, tuple):
            text, is_en = item[0], item[1]
        else:
            text, is_en = item, True
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.text = text
        for run in para.runs:
            _font(run, FONT_BODY)
            if not is_en and text.strip():
                run.font.size = Pt(12)


def _add_content_slide(prs, title_en, title_ko, body_items):
    """Layout 3 'Title text and image', title at top, body spans full width,
    picture placeholder removed."""
    layout = prs.slide_masters[0].slide_layouts[3]
    slide = prs.slides.add_slide(layout)
    _remove_ph(slide, 10)  # picture
    _set_title_top(slide, title_en, title_ko)
    # Reposition content placeholder (idx 11) to full width
    body = None
    for shape in slide.shapes:
        if shape is slide.shapes.title: continue
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == 11:
                body = shape; break
        except Exception: pass
    if body is None:
        body = slide.shapes.add_textbox(Inches(0.45), Inches(1.60), Inches(12.4), Inches(5.0))
    else:
        body.left = Inches(0.45); body.top = Inches(1.60)
        body.width = Inches(12.4); body.height = Inches(5.0)
    _apply_body(body, body_items)
    _add_slide_number(slide)
    return slide


def _add_section_title(prs, label_en, label_ko, number):
    layout = prs.slide_masters[0].slide_layouts[2]  # Section Title 1
    slide = prs.slides.add_slide(layout)
    tf = slide.shapes.title.text_frame
    tf.clear()
    p_en = tf.paragraphs[0]; p_en.text = f"{number}. {label_en}"
    for run in p_en.runs: _font(run, FONT_HEAD)
    p_ko = tf.add_paragraph(); p_ko.text = f"{number}. {label_ko}"
    for run in p_ko.runs: _font(run, FONT_HEAD, 28)
    return slide


def _move_slide(prs, from_idx, to_idx):
    xml_slides = prs.slides._sldIdLst
    sl = list(xml_slides)[from_idx]
    xml_slides.remove(sl)
    xml_slides.insert(to_idx, sl)


# ─────────────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
total_before = len(p.slides)
print(f"Starting from template: {total_before} slides")


# ─── Step 1: Fix slide 1 title ───────────────────────────────────────────
slide1 = p.slides[0]
title_shape = next((s for s in slide1.shapes
                    if s.has_text_frame and "Rotten and Fresh" in s.text_frame.text),
                   None)
if title_shape is None:
    title_shape = next((s for s in slide1.shapes if s.has_text_frame), None)
tf = title_shape.text_frame; tf.clear()
p_en = tf.paragraphs[0]
p_en.text = "Visit Context, Information Diversity and Reader Response on Naver Place"
for run in p_en.runs: _font(run, FONT_HEAD)
p_ko = tf.add_paragraph()
p_ko.text = "네이버 플레이스의 방문 맥락, 정보 다양성, 이용자 반응"
for run in p_ko.runs: _font(run, FONT_HEAD, 22)
tf.add_paragraph().text = ""
p3 = tf.add_paragraph(); p3.text = "Jorge Adan Soriano Hernandez"
for run in p3.runs: _font(run, FONT_HEAD, 16)
p4 = tf.add_paragraph(); p4.text = "소리아노 에르난데스 호르헤 아단"
for run in p4.runs: _font(run, FONT_HEAD, 14)
p5 = tf.add_paragraph(); p5.text = "Department of Data Science, Hoseo University"
for run in p5.runs: _font(run, FONT_HEAD, 12)
p6 = tf.add_paragraph(); p6.text = "호서대학교 데이터사이언스학과"
for run in p6.runs: _font(run, FONT_HEAD, 12)
p7 = tf.add_paragraph(); p7.text = "October 2026  |  2026년 10월"
for run in p7.runs: _font(run, FONT_HEAD, 11)
print("  [1] Title slide updated")


# ─── Step 2: Replace slide 4 body + add [1] footnote ─────────────────────
slide4 = p.slides[3]
body4 = next((s for s in slide4.shapes if s.name == "Content Placeholder 6"), None)
body4_items = [
    ("Online reviews drive travel decisions.", True),
    ("온라인 리뷰는 여행 결정을 좌우한다.", False),
    ("", True),
    ("Information diversity in reviews predicts business performance [1], "
     "but who writes diverse reviews stays unobserved.", True),
    ("리뷰의 정보 다양성은 사업체 성과를 예측하나 [1], 작성자 측 요인은 관찰되지 않는다.", False),
    ("", True),
    ("This study takes the construct to the individual review, combined with "
     "Naver's structured visit context: companion, purpose, wait, reservation.", True),
    ("본 연구는 이 개념을 개별 리뷰 수준으로 확장하고, 네이버의 구조화된 방문 맥락"
     "(동반자, 목적, 대기, 예약)과 결합한다.", False),
]
_apply_body(body4, body4_items)
# Footnote [1]
tb = slide4.shapes.add_textbox(Inches(0.45), Inches(6.50), Inches(10.0), Inches(0.28))
rtf = tb.text_frame; rtf.word_wrap = True
rtf.paragraphs[0].text = ("[1] Lee, M., Jeong, D., & Kim, A. J. (2026). The impact of "
                          "information diversity on online reviews and business performance. "
                          "Journal of Consumer Studies, 37.")
for run in rtf.paragraphs[0].runs: _font(run, FONT_BODY, 10)
print("  [2] Slide 4 (Introduction) body + [1] footnote")


# ─── Step 3: Add slide 5 Research Questions ──────────────────────────────
rqs = [
    "1. Which visit contexts predict returning to the same attraction?",
    "    어떤 방문 맥락이 재방문과 연관되는가?",
    "",
    "2. Which reviewers and visit contexts produce more diverse keywords?",
    "    어떤 작성자와 방문 맥락이 더 많은 키워드를 생성하는가?",
    "",
    "3. Which reviews receive reactions? Does sentiment help?",
    "    어떤 리뷰가 반응을 받는가? 감성은 도움이 되는가?",
    "",
    "4. Which aspects do reviewer groups discuss, and does content predict "
    "engagement beyond sentiment?",
    "    어떤 방문 측면을 작성자 그룹이 언급하며, 내용이 감성 이상의 몰입을 예측하는가?",
]
# convert to body items format
rq_body = []
for i, text in enumerate(rqs):
    is_en = not any(ord(c) > 127 for c in text)
    rq_body.append((text, is_en))
s5 = _add_content_slide(p, "Research Questions", "연구 질문", rq_body)
_move_slide(p, len(p.slides) - 1, 4)  # move to position 5 (index 4)
print("  [3] Slide 5 Research Questions added")


# ─── Step 4: Update slides 7, 8, 9 (Theoretical Background) ──────────────
# After step 3, slide positions: 1-4 original, 5=RQs, then 6-10 were 5-9.
# Slide 7 (old 6, now 7): Information Diversity (actually index 6 after RQ insert)
# Let me use the labels directly.
def _find_body_up(slide):
    """Pick the Content Placeholder 6 with the smaller top (the body, not footnote)."""
    cands = [s for s in slide.shapes
             if s.has_text_frame and s.name == "Content Placeholder 6"]
    return min(cands, key=lambda s: s.top) if cands else None

sl7_items = [
    ("Information diversity measures how many distinct keywords a review carries, "
     "independent of its length or sentiment.", True),
    ("정보 다양성은 리뷰 길이나 감성과 무관하게 리뷰가 담은 서로 다른 키워드 수를 측정한다.", False),
    ("", True),
    ("Higher diversity predicts business performance separately from review volume [1].", True),
    ("리뷰 양과 독립적으로 사업체 성과를 예측한다 [1].", False),
]
_apply_body(_find_body_up(p.slides[6]), sl7_items)

sl8_items = [
    ("Review helpfulness captures how useful other viewers find a review.", True),
    ("리뷰 유용성은 다른 이용자가 리뷰를 얼마나 유용하게 느끼는지를 포착한다.", False),
    ("", True),
    ("Prior work operationalizes it through content dissimilarity in text [2]; "
     "this study uses reader reactions as a behavioural proxy.", True),
    ("선행 연구는 이를 텍스트 내용의 비유사성으로 조작화하며 [2], "
     "본 연구는 이용자 반응을 행동적 대리 지표로 사용한다.", False),
]
_apply_body(_find_body_up(p.slides[7]), sl8_items)

sl9_items = [
    ("Research gap", True),
    ("연구 공백", False),
    ("Prior work observes performance at the aggregate level, but what each "
     "review discusses and the visit context behind it stay unobserved.", True),
    ("선행 연구는 집계 수준에서 성과를 관찰하지만, 각 리뷰가 다루는 내용과 "
     "그 방문 맥락은 관찰되지 않는다.", False),
    ("", True),
    ("This study contributes", True),
    ("본 연구의 기여", False),
    ("(i)   Review-level replication of the diversity–performance link.", True),
    ("        다양성–성과 관계의 리뷰 수준 재현.", False),
    ("(ii)  Platform-structured visit context (companion, purpose, wait, "
     "reservation) as a joint predictor set.", True),
    ("        플랫폼 구조화된 방문 맥락(동반자·목적·대기·예약)의 통합 예측 변수 세트.", False),
    ("(iii) Aspect-level analysis of what reviews discuss, cross-cut by visit context.", True),
    ("        리뷰 내용의 측면별 분석, 방문 맥락과 교차.", False),
]
body9 = _find_body_up(p.slides[8])
body9.top = Inches(1.85); body9.height = Inches(4.5)
_apply_body(body9, sl9_items)
print("  [4] Theoretical Background (slides 7-9) bodies updated")


# ─── Step 5: Add Data, Framework, Variables, Models (slides 11-14) ──────
# After slide 10 (3. Methodology), add 4 content slides.

# Slide 11: Data
_add_content_slide(p, "Data", "데이터", [
    ("29 Korean tourist attractions · 14,401 reviews · 11,165 with text · 8,276 reviewers.", True),
    ("한국 관광지 29곳 · 리뷰 14,401건 · 텍스트 포함 11,165건 · 작성자 8,276명.", False),
    ("", True),
    ("Attractions selected by crossing Yanolja Research's \"Korea's Top 500\" ranking with "
     "Korea Tourism Organization visitor volume, inside typological strata (palaces, hanok "
     "villages, markets, parks, museums, modern landmarks).", True),
    ("관광지는 야놀자 리서치 「대한민국 Top 500」과 한국관광공사 방문자 지표를 교차하여, "
     "유형별 층위(궁궐·한옥마을·시장·공원·박물관·현대 랜드마크)에서 선정.", False),
    ("", True),
    ("Cities: Seoul (25) and Busan (4). Unit of analysis: a review i at place j, not the business-week.", True),
    ("도시: 서울 25곳, 부산 4곳. 분석 단위는 관광지 j의 리뷰 i이며, 사업체-주 단위가 아니다.", False),
])

# Slide 12: Research Framework (diagram)
layout = p.slide_masters[0].slide_layouts[3]
fw_slide = p.slides.add_slide(layout)
_remove_ph(fw_slide, 10)
_remove_ph(fw_slide, 11)
_set_title_top(fw_slide, "Research Framework", "연구 프레임워크")
_add_slide_number(fw_slide)

def _box(x, y, w, h, title_en, title_ko, lines):
    shape = fw_slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                       Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = FILL_WHITE
    shape.line.color.rgb = LINE_GREY; shape.line.width = Emu(12700)
    shape.shadow.inherit = False
    tf = shape.text_frame; tf.word_wrap = True
    tf.margin_left = Inches(0.15); tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.08); tf.margin_bottom = Inches(0.08)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    p.text = f"{title_en}  /  {title_ko}"
    for run in p.runs: _font(run, FONT_HEAD, 14, bold=True, color=TEXT_DARK)
    for line in lines:
        para = tf.add_paragraph(); para.text = line; para.alignment = PP_ALIGN.LEFT
        for run in para.runs: _font(run, FONT_BODY, 11, color=TEXT_DARK)

_box(1.5, 1.55, 10.3, 1.25, "Data Acquisition", "데이터 수집", [
    "Naver Place scraper  →  29 attractions · 14,401 reviews · 8,276 reviewers",
    "11,165 with text  ·  Yanolja Top 500 ∩ KTO visitor volume  ·  Seoul (25) + Busan (4)",
])
c1 = fw_slide.shapes.add_connector(1, Inches(6.65), Inches(2.80), Inches(6.65), Inches(3.10))
c1.line.color.rgb = LINE_GREY; c1.line.width = Emu(19050)
_box(1.5, 3.10, 10.3, 1.80, "Variables", "변수", [
    "DV (4):  Revisit · Keyword Count (0–5) · Rating (1–5) · Reactions",
    "IV:  Visit Context (companion · purpose · wait · reservation)  +  Sentiment  +  Aspect dummies (§4.6)",
    "Controls:  text length · reviewer history · followers · review age · season · weekend · verification",
    "Fixed effects:  Place (δⱼ)   ·   Standard errors clustered by reviewer",
])
c2 = fw_slide.shapes.add_connector(1, Inches(6.65), Inches(4.90), Inches(6.65), Inches(5.20))
c2.line.color.rgb = LINE_GREY; c2.line.width = Emu(19050)
_box(1.5, 5.20, 10.3, 1.25, "Models", "모형", [
    "M1 Revisit  (logistic)   ·   M2 Keyword Count  (ordered logistic)",
    "M3 Rating  (ordered logistic, exploratory)   ·   M4 Reactions  (negative binomial)",
])

# Slide 13: Variables (table)
layout = p.slide_masters[0].slide_layouts[3]
var_slide = p.slides.add_slide(layout)
_remove_ph(var_slide, 10)
_remove_ph(var_slide, 11)
_set_title_top(var_slide, "Variables", "변수")
_add_slide_number(var_slide)
rows_data = [
    ("Role", "Variable", "Description"),
    ("DV", "Revisit  재방문", "binary — 2+ visits (0/1)"),
    ("DV", "Keyword Count  키워드 수", "ordinal 0–5 — information diversity"),
    ("DV", "Rating  별점", "ordinal 1–5 stars (exploratory)"),
    ("DV", "Reactions  반응 수", "count — reader interactions (helpfulness proxy)"),
    ("IV", "Companion  동반자", "6 dummies: alone, partner, friends, children, family, colleagues"),
    ("IV", "Purpose  방문 목적", "5 dummies: travel, outing, daily, date, social"),
    ("IV", "Waited  대기 경험", "binary — queued before entry"),
    ("IV", "Reserved  사전 예약", "binary — advance reservation"),
    ("IV", "Sentiment  감성 점수", "continuous (−1 to +1), BERT-based (Karabila et al. 2024)"),
    ("IV", "Aspect mentions  측면 언급", "6 dummies (ABSA, §4.6 only)"),
    ("Control", "Text length, images", "ln(chars), image count"),
    ("Control", "Reviewer activity", "ln(reviews), ln(followers)"),
    ("Control", "Review age", "ln(days since post)"),
    ("Control", "Season / Weekend / Verification", "dummies"),
    ("Control", "Place FE  δⱼ", "28 place dummies (reference: Gyeongbokgung)"),
]
table_shape = var_slide.shapes.add_table(len(rows_data), 3,
                                          Inches(0.60), Inches(1.60),
                                          Inches(12.1), Inches(5.0))
tbl = table_shape.table
tbl.columns[0].width = Inches(1.3)
tbl.columns[1].width = Inches(3.7)
tbl.columns[2].width = Inches(7.1)
for i, row in enumerate(rows_data):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.margin_left = Inches(0.06); cell.margin_right = Inches(0.06)
        cell.margin_top = Inches(0.02); cell.margin_bottom = Inches(0.02)
        tf = cell.text_frame; tf.word_wrap = True; tf.clear()
        para = tf.paragraphs[0]; para.text = val
        for run in para.runs:
            _font(run, FONT_BODY, 12 if i == 0 else 11, bold=(i == 0))
        cell.fill.solid()
        if i == 0:
            cell.fill.fore_color.rgb = RGBColor(0xE8, 0xE8, 0xE8)
        else:
            cell.fill.fore_color.rgb = FILL_WHITE if i % 2 == 1 else RGBColor(0xF8, 0xF8, 0xF8)

# Slide 14: Models (explicit equations)
layout = p.slide_masters[0].slide_layouts[3]
mod_slide = p.slides.add_slide(layout)
_remove_ph(mod_slide, 10)
_remove_ph(mod_slide, 11)
_set_title_top(mod_slide, "Models", "모형")
_add_slide_number(mod_slide)
intro = mod_slide.shapes.add_textbox(Inches(0.45), Inches(1.50), Inches(12.4), Inches(0.60))
itf = intro.text_frame; itf.word_wrap = True
ip = itf.paragraphs[0]
ip.text = ("Four models — each matching the measurement scale of its outcome. "
           "All include place fixed effects δⱼ; standard errors clustered by reviewer.")
for run in ip.runs: _font(run, FONT_BODY, 12)
ip2 = itf.add_paragraph()
ip2.text = ("네 가지 모형 — 각 종속변수의 측정 척도에 맞춤. "
            "모두 관광지 고정효과 δⱼ 포함; 표준오차는 작성자 단위로 클러스터링.")
for run in ip2.runs: _font(run, FONT_BODY, 10)

eqs = mod_slide.shapes.add_textbox(Inches(0.45), Inches(2.35), Inches(12.4), Inches(4.2))
etf = eqs.text_frame; etf.word_wrap = True

def _eqline(text, mono=False, bold=False, size=12, idx=None, space=False):
    if idx == 0:
        para = etf.paragraphs[0]
    else:
        para = etf.add_paragraph()
    if space: para.space_before = Pt(6)
    para.text = text
    for run in para.runs:
        _font(run, MONO if mono else FONT_BODY, size, bold=bold)

_eqline("M1  Revisit  (binary)   →   logistic regression", bold=True, size=12, idx=0)
_eqline("        logit  P(Revisit_ij)  =  β₀  +  x_ij′ β  +  δⱼ", mono=True, size=12)
_eqline("M2  Keyword Count  (ordinal 0–5)   →   ordered logistic", bold=True, size=12, space=True)
_eqline("        P(KC_ij ≤ k)  =  [ 1 + exp(−(τ_k − x_ij′ β − δⱼ)) ]⁻¹      k = 0, …, 4", mono=True, size=12)
_eqline("        (ordinal, not count: the 0–5 range is platform-capped at five, not Poisson-generated)", size=10)
_eqline("M3  Rating  (ordinal 1–5)   →   ordered logistic (exploratory)", bold=True, size=12, space=True)
_eqline("        P(Rating_ij ≤ k)  =  [ 1 + exp(−(τ_k − x_ij′ β − δⱼ)) ]⁻¹      k = 1, …, 4", mono=True, size=12)
_eqline("M4  Reactions  (overdispersed count)   →   negative binomial", bold=True, size=12, space=True)
_eqline("        Reactions_ij  ~  NegBin(μ_ij, α)", mono=True, size=12)
_eqline("        ln μ_ij  =  β₀  +  x_ij′ β  +  γ · ln(Age_ij)  +  δⱼ", mono=True, size=12)
_eqline("        (ln(Age) enters as an exposure offset — not a regular β — because reactions accumulate over time)", size=10)

legend = mod_slide.shapes.add_textbox(Inches(0.45), Inches(6.30), Inches(12.4), Inches(0.35))
ltf = legend.text_frame; lp = ltf.paragraphs[0]
lp.text = ("x_ij = regressor vector (visit context + sentiment + controls)   ·   "
           "β = coefficients   ·   δⱼ = place FE   ·   τ_k = thresholds   ·   "
           "γ = log-age elasticity (M4 offset)   ·   α = NB dispersion (α̂ = 2.44)")
for run in lp.runs: _font(run, FONT_BODY, 9, italic=True)

# Slides were appended in order (Data, Framework, Variables, Models) and the
# "3. Methodology" section header is at position 9 (0-indexed), so no move
# is needed — order is already correct: slides 11, 12, 13, 14.

print("  [5] Methodology (slides 11-14): Data, Framework, Variables, Models added")


# ─── Step 6: Add Results section + Conclusion + Closing ──────────────────
_add_section_title(p, "Results", "결과", 4)

# M1-M4 findings
_add_content_slide(p, "Main findings (M1–M4)", "주요 결과 (M1–M4)", [
    ("M1 Revisit  (logistic, AUC = 0.773)", True),
    ("  Reviewer history       OR = 1.52 ***    Visited alone     OR = 1.68 **", True),
    ("  Waited to enter        OR = 0.51 ***    Travel group      OR = 0.56 ***", True),
    ("  작성자 리뷰 이력과 혼자 방문은 재방문을 높인다; 대기와 여행 목적은 낮춘다.", False),
    ("", True),
    ("M2 Keyword Count  (ordered logistic, RMSE 1.37 vs 1.88 base)", True),
    ("  Wrote text             OR = 4.02 ***    Visit info given  OR = 2.53 ***", True),
    ("  Revisitor              OR = 1.60 ***    Purpose: outing   OR = 1.85 ***", True),
    ("  텍스트 작성 및 방문 정보 제공이 키워드 수를 크게 늘린다.", False),
    ("", True),
    ("M3 Rating  (exploratory – ratings move little, 73.9\\% five-star)", True),
    ("  Keyword count          OR = 1.56 ***    Revisitor         OR = 1.37 *", True),
    ("  별점은 변동이 작아 탐색적으로만 보고; 키워드 수가 가장 강한 예측 변수.", False),
    ("", True),
    ("M4 Reactions  (negative binomial, AUC any-reaction 0.815)", True),
    ("  ln(followers)          IRR = 1.97 ***   ln(text length)   IRR = 1.64 ***", True),
    ("  Sentiment (−1 to +1)   IRR = 0.77 **     Visit: autumn     IRR = 0.71 ***", True),
    ("  팔로워 수와 텍스트 길이가 반응을 늘리고, 긍정 감성과 가을 방문은 줄인다.", False),
])

# Aspect-level findings
_add_content_slide(p, "Aspect-level analysis (6 aspects, N = 11,164)",
                   "측면 수준 분석 (6개 측면, N = 11,164)", [
    ("ABSA labels on six dimensions (LLM, 06_llm_analysis.py): historical/cultural (50.4\\%), "
     "visual (63.8\\%), service/experience (27.4\\%), accessibility (19.8\\%), crowding (16.3\\%), "
     "food (6.9\\%).", True),
    ("LLM 기반 분류기로 여섯 가지 측면 라벨링: 역사·문화 50.4\\%, 시각 63.8\\%, 서비스·체험 27.4\\%, "
     "접근성 19.8\\%, 혼잡 16.3\\%, 음식 6.9\\%.", False),
    ("", True),
    ("Six aspects specified a priori and validated post-hoc against unsupervised topic extraction "
     "(LDA at optimal K = 6, BERTopic K = 15). All six except crowding emerge as distinct topics; "
     "crowding is retained as polarity-dominated (18.1\\% of mentions negative, the highest).", True),
    ("여섯 측면은 사전 지정, 비지도 토픽 추출(LDA K = 6, BERTopic K = 15)로 사후 검증. "
     "혼잡은 극성 중심의 차원이므로 유지.", False),
    ("", True),
    ("Four findings from the \"who mentions what\" regressions:", True),
    ("  (1) Children drive narrative-rich reviews across historical, accessibility and service "
     "(ORs 1.22–1.55).", True),
    ("  (2) Service friction splits two ways: waited → crowding (OR 2.13 ***); reserved → crowding "
     "↓ 0.69 ** but service/experience ↑ 2.39 ***.", True),
    ("  (3) Date-purpose raises food mentions by 51\\% (OR 1.51 *); alone visits lower them (OR 0.64 *).", True),
    ("  (4) Service/experience is empirically distinct (pseudo-R² = 0.371), with structurally "
     "different predictors.", True),
    ("  (1) 아이와 방문: 다양한 측면의 언급 증가. (2) 대기 → 혼잡 ↑, 예약 → 서비스 ↑ 혼잡 ↓. "
     "(3) 데이트 → 음식 ↑, 혼자 → 음식 ↓. (4) 서비스·체험은 독립 차원.", False),
    ("", True),
    ("Reactions by aspect content: no aspect reaches p < .05 after controls. Engagement is driven "
     "by reviewer identity (followers, revisitor, text length), not by review content.", True),
    ("아스펙트 내용과 반응: 통제 후 p < .05 도달하는 측면 없음. 몰입은 작성자 특성에 의해 좌우된다.", False),
])

# Conclusion section
_add_section_title(p, "Conclusion and Implications", "결론 및 시사점", 5)

# Implications + Limitations
_add_content_slide(p, "Implications and Limitations", "시사점과 한계", [
    ("Implications / 시사점", True),
    ("  For platforms: engagement is reviewer-identity-driven. Reviewer retention and reviewer "
     "experience may matter more than nudging keyword choice.", True),
    ("  For attraction managers: queueing is the single strongest negative signal for return, "
     "and the only one in this report that is directly actionable.", True),
    ("  플랫폼: 몰입은 작성자 정체성에 의해 좌우된다. "
     "운영자: 대기 시간이 재방문의 가장 강한 부정 신호다.", False),
    ("", True),
    ("Limitations and future work / 한계 및 향후 과제", True),
    ("  Associations only — cross-sectional design, not causal. Lee et al. (2026) use a "
     "keyword-expansion event; we do not have an equivalent lag.", True),
    ("  Model 1 predicts a visit that already occurred — it profiles returning visitors "
     "rather than explaining why anyone returns.", True),
    ("  A single platform; Naver reviewers may differ from Korean reviewers at large. "
     "Place and time fixed effects + Hausman test are the next addition.", True),
    ("  횡단면 설계, 인과적이지 않음. 모형 1은 재방문자를 특성화할 뿐 원인을 설명하지 않음. "
     "단일 플랫폼; 시간 고정효과와 Hausman 검정이 향후 과제.", False),
])

# Closing slide (Thank you) — uses the Closing layout
layout = p.slide_masters[0].slide_layouts[12]
closing = p.slides.add_slide(layout)
ctf = closing.shapes.title.text_frame; ctf.clear()
pc_en = ctf.paragraphs[0]; pc_en.text = "Thank you"
for run in pc_en.runs: _font(run, FONT_HEAD)
pc_ko = ctf.add_paragraph(); pc_ko.text = "감사합니다"
for run in pc_ko.runs: _font(run, FONT_HEAD, 24)
# Content area
closing_items = [
    ("Jorge Adan Soriano Hernandez", True),
    ("Department of Data Science, Hoseo University", True),
    ("호서대학교 데이터사이언스학과", False),
    ("", True),
    ("Full report, data and scripts available in the project repository.", True),
    ("전체 보고서, 데이터, 스크립트는 프로젝트 저장소에서 열람 가능.", False),
    ("", True),
    ("Questions and discussion / 질문 및 토론", True),
]
for shape in closing.shapes:
    if shape is closing.shapes.title: continue
    try:
        if shape.placeholder_format is not None and shape.placeholder_format.idx == 10:
            _apply_body(shape, closing_items)
            break
    except Exception: pass

print("  [6] Results + Conclusion + Closing (slides 15-20) added")

p.save(PPTX)
print(f"\nFinal: {len(p.slides)} slides in {PPTX}")
