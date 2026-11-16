"""
build_v2.py
Build the workshop presentation from templateppt.pptx, matching the final
specification of report_naver_v2.tex (2 models, no ABSA, 8 unique vars).
Output: presentation_v2.pptx
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from copy import deepcopy
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

TEMPLATE = "templateppt.pptx"
OUT      = "presentation_v2.pptx"

FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
DARK   = RGBColor(0x22, 0x22, 0x22)
MUTED  = RGBColor(0x55, 0x55, 0x55)
ACCENT = RGBColor(0x40, 0x55, 0x70)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


def _set_para(p, text, size=14, bold=False, italic=False, color=DARK,
              align=PP_ALIGN.LEFT, name=FONT_BODY, space_before=0):
    p.text = text
    p.alignment = align
    if space_before:
        p.space_before = Pt(space_before)
    for run in p.runs:
        _font(run, name, size, bold=bold, italic=italic, color=color)


def set_title(slide, title_text, subtitle=None):
    """Fill the title placeholder (idx=0) and optional subtitle (idx=1)."""
    title = slide.shapes.title
    tf = title.text_frame
    tf.clear()
    _set_para(tf.paragraphs[0], title_text, size=28, bold=True,
              color=DARK, name=FONT_HEAD, align=PP_ALIGN.LEFT)


def add_textbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top),
                                   Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def add_para(tf, text, size=12, bold=False, italic=False, color=DARK,
             bullet=False, space_before=4, first=False):
    if first:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.space_before = Pt(space_before)
    p.text = ("•  " + text) if bullet else text
    p.alignment = PP_ALIGN.LEFT
    for run in p.runs:
        _font(run, FONT_BODY, size, bold=bold, italic=italic, color=color)


def strip_placeholders(slide, keep=(0,)):
    """Remove placeholders except those with indices in keep."""
    for shape in list(slide.placeholders):
        try:
            idx = shape.placeholder_format.idx
        except Exception:
            continue
        if idx not in keep:
            sp = shape._element
            sp.getparent().remove(sp)


# ─── Load template, clear existing slides ───────────────────────────────────
p = Presentation(TEMPLATE)
# Remove all existing slides but keep layouts
xml_slides = p.slides._sldIdLst
slides = list(xml_slides)
for slide in slides:
    xml_slides.remove(slide)
# Clean the orphaned slide parts
for rel_id in list(p.part.rels):
    rel = p.part.rels[rel_id]
    if "slide" in rel.target_ref and "slideLayout" not in rel.target_ref \
       and "slideMaster" not in rel.target_ref:
        try:
            p.part.drop_rel(rel_id)
        except Exception:
            pass

# ─── Layout aliases ────────────────────────────────────────────────────────
L_TITLE   = p.slide_layouts[0]
L_AGENDA  = p.slide_layouts[1]
L_SECTION = p.slide_layouts[2]
L_CONTENT = p.slide_layouts[4]
L_2COL    = p.slide_layouts[6]
L_TABLE   = p.slide_layouts[11]
L_CLOSE   = p.slide_layouts[12]

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_TITLE)
# Replace placeholder text if present
for ph in s.placeholders:
    try:
        idx = ph.placeholder_format.idx
    except Exception:
        continue
    tf = ph.text_frame
    tf.clear()
    if idx == 0:  # title
        _set_para(tf.paragraphs[0],
                  "An Empirical Analysis of Visit Context\nand Review Outcomes in Online Reviews of\nKorean Tourist Attractions",
                  size=30, bold=True, color=DARK, name=FONT_HEAD)
    elif idx == 1:  # subtitle
        _set_para(tf.paragraphs[0],
                  "국내 관광명소 온라인 리뷰에서 방문 맥락과 리뷰 결과에 관한 실증분석",
                  size=16, italic=True, color=MUTED, name=FONT_HEAD)
    else:
        _set_para(tf.paragraphs[0],
                  "Jorge Adan Soriano Hernandez · Department of Data Science, Hoseo University",
                  size=14, color=MUTED)

# Add author info textbox at bottom
tb = add_textbox(s, 0.6, 6.5, 12.0, 0.8)
add_para(tb, "Jorge Adan Soriano Hernandez (소리아노 에르난데스 호르헤 아단)",
         size=12, color=MUTED, first=True)
add_para(tb, "Department of Data Science, Hoseo University · 호서대학교 데이터사이언스학과",
         size=10, color=MUTED, italic=True)
add_para(tb, "2026년 한국생산운영관리학회 추계학술대회 · October 2026",
         size=10, color=MUTED, italic=True)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Agenda
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_AGENDA)
set_title(s, "Agenda")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.0)
items = [
    ("1.", "Introduction — background, visit context, research questions"),
    ("2.", "Methodology — data, variables, two parallel models"),
    ("3.", "Results — Model 1 (Revisit) and Model 2 (Rating)"),
    ("4.", "Interpretation — divergent traces of satisfaction"),
    ("5.", "Conclusion — implications and limitations"),
]
for i, (num, txt) in enumerate(items):
    add_para(tb, f"{num}  {txt}", size=18, bold=(i == 0), color=ACCENT,
             space_before=10, first=(i == 0))

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Section Title: Introduction
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_SECTION)
set_title(s, "1. Introduction")
tb = add_textbox(s, 0.6, 2.8, 12.0, 1.5)
add_para(tb, "Background · Research Questions · Contribution",
         size=20, italic=True, color=MUTED, first=True)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Research background
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Research background")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Online reviews drive tourism decisions",
         size=18, bold=True, color=ACCENT, first=True)
add_para(tb, "Travellers consult reviews, photos and ratings before deciding to visit or return.",
         size=14, color=DARK, space_before=6)
add_para(tb, "Naver Place is unique: structured visit-context metadata",
         size=18, bold=True, color=ACCENT, space_before=16)
add_para(tb, "Unlike most platforms (TripAdvisor, Google), Naver Place records who the reviewer went with, why they came, whether they waited, and whether they reserved.",
         size=14, color=DARK, space_before=6)
add_para(tb, "Research gap", size=18, bold=True, color=ACCENT, space_before=16)
add_para(tb, "Prior work treats reviews as text only or aggregates to business-week level (Lee, Jeong & Kim, 2026). The visit context in which each individual review was written has not been exploited as a review-level predictor set.",
         size=14, color=DARK, space_before=6)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Research Questions
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Research questions")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "RQ1 — Revisit", size=20, bold=True, color=ACCENT, first=True)
add_para(tb, "How do visit context and reviewer characteristics shape the probability that a review is written by a returning visitor?",
         size=15, color=DARK, space_before=6)
add_para(tb, "RQ2 — Rating", size=20, bold=True, color=ACCENT, space_before=18)
add_para(tb, "How do visit context and reviewer characteristics shape the probability of each star-rating category (TOP 5★, MID 4-4.5★, LOW ≤3.5★)?",
         size=15, color=DARK, space_before=6)
add_para(tb, "Framework", size=20, bold=True, color=ACCENT, space_before=18)
add_para(tb, "Both outcomes are observable traces of a latent satisfaction construct — rating is the declared trace, revisit is the behavioural trace. We model them in parallel.",
         size=14, color=DARK, italic=True, space_before=6)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Section Title: Methodology
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_SECTION)
set_title(s, "2. Methodology")
tb = add_textbox(s, 0.6, 2.8, 12.0, 1.5)
add_para(tb, "Data · Variables · Model specification",
         size=20, italic=True, color=MUTED, first=True)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Data
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Data")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Source", size=18, bold=True, color=ACCENT, first=True)
add_para(tb, "Naver Place reviews, scraped per attraction, Korean language",
         size=14, color=DARK, bullet=True, space_before=6)
add_para(tb, "Sample size", size=18, bold=True, color=ACCENT, space_before=14)
add_para(tb, "14,401 reviews from 8,276 reviewers across 29 attractions",
         size=14, color=DARK, bullet=True, space_before=6)
add_para(tb, "11,165 with free-text content → M1 Revisit sample",
         size=14, color=DARK, bullet=True, space_before=4)
add_para(tb, "4,044 with text AND star rating → M2 Rating sample",
         size=14, color=DARK, bullet=True, space_before=4)
add_para(tb, "Attraction selection", size=18, bold=True, color=ACCENT, space_before=14)
add_para(tb, "Stratified sampling across typological categories (palaces, traditional quarters, markets, museums, parks, beaches, theme parks), minimum 30 Korean reviews per site",
         size=14, color=DARK, bullet=True, space_before=6)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Variables table
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Variables — shared core and model-specific additions")

tbl = s.shapes.add_table(10, 4, Inches(0.6), Inches(1.4),
                          Inches(12.0), Inches(5.0)).table
# header
headers = ["Variable", "Description", "M1", "M2"]
for j, h in enumerate(headers):
    cell = tbl.cell(0, j)
    cell.text = ""
    _set_para(cell.text_frame.paragraphs[0], h, size=14, bold=True,
              color=WHITE, name=FONT_HEAD, align=PP_ALIGN.CENTER)
    cell.fill.solid()
    cell.fill.fore_color.rgb = ACCENT

rows = [
    ("sentiment",        "BERT sentiment of the text",       "✓", "✓"),
    ("waited",           "Had to queue at entrance",         "✓", "✓"),
    ("ln(1+followers)",  "Reviewer's follower count",         "✓", "✓"),
    ("is_tourist",       "Visit purpose was 'travel'",        "✓", ""),
    ("comp_alone",       "Visit was solo",                    "✓", ""),
    ("ln(1+reviews)",    "Reviewer's prior review count",     "✓", ""),
    ("ln(1+photos)",     "Photos attached to the review",     "",  "✓"),
    ("season_autumn",    "Visit was in autumn",               "",  "✓"),
    ("Total",            "3 shared + 3 M1-only + 2 M2-only = 8 unique", "6", "5"),
]
for i, row in enumerate(rows, 1):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = ""
        is_total = (row[0] == "Total")
        _set_para(cell.text_frame.paragraphs[0], val,
                  size=12, bold=is_total,
                  color=DARK, align=(PP_ALIGN.LEFT if j < 2 else PP_ALIGN.CENTER))

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Model 1 equation
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Model 1 — Binary logistic regression (Revisit)")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Outcome: Revisit_ij = 1 if reviewer's visit count ≥ 2, 0 otherwise",
         size=14, italic=True, color=MUTED, first=True)
add_para(tb, "", size=4, space_before=8)
add_para(tb, "logit P(Revisit_ij = 1) = α", size=15, bold=True,
         color=ACCENT, space_before=8)
add_para(tb, "            + β1 · waited_ij", size=14, color=DARK, space_before=2)
add_para(tb, "            + β2 · is_tourist_ij", size=14, color=DARK, space_before=2)
add_para(tb, "            + β3 · sentiment_ij", size=14, color=DARK, space_before=2)
add_para(tb, "            + β4 · comp_alone_ij", size=14, color=DARK, space_before=2)
add_para(tb, "            + β5 · ln(1 + reviews_ij)", size=14, color=DARK, space_before=2)
add_para(tb, "            + β6 · ln(1 + followers_ij)", size=14, color=DARK, space_before=2)
add_para(tb, "            + δ_j   (place fixed effect)", size=14, color=DARK, space_before=2)
add_para(tb, "SE clustered by reviewer (user_id). 28 place dummies (Gyeongbokgung = reference).",
         size=12, italic=True, color=MUTED, space_before=14)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Model 2 equation
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Model 2 — Multinomial logistic regression (Rating)")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Outcome: Y_ij ∈ {LOW (≤3.5★), MID (4-4.5★), TOP (5★)}, base = TOP",
         size=14, italic=True, color=MUTED, first=True)
add_para(tb, "", size=4, space_before=8)
add_para(tb, "For each k ∈ {MID, LOW}:", size=14, color=DARK, space_before=6)
add_para(tb, "log[ P(Y_ij = k) / P(Y_ij = TOP) ] = α_k", size=15, bold=True,
         color=ACCENT, space_before=6)
add_para(tb, "            + γ_k1 · sentiment_ij", size=14, color=DARK, space_before=2)
add_para(tb, "            + γ_k2 · waited_ij", size=14, color=DARK, space_before=2)
add_para(tb, "            + γ_k3 · ln(1 + followers_ij)", size=14, color=DARK, space_before=2)
add_para(tb, "            + γ_k4 · ln(1 + photos_ij)", size=14, color=DARK, space_before=2)
add_para(tb, "            + γ_k5 · season_autumn_ij", size=14, color=DARK, space_before=2)
add_para(tb, "            + δ_jk   (place fixed effect, category-specific)", size=14, color=DARK, space_before=2)
add_para(tb, "Each non-reference category gets its own intercept α_k, slope vector γ_k, and FE δ_jk.",
         size=12, italic=True, color=MUTED, space_before=10)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Why multinomial (Brant test)
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Why multinomial, not ordered logit?")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Initial attempt: ordered logistic regression",
         size=16, bold=True, color=ACCENT, first=True)
add_para(tb, "Natural choice for ordinal outcome like star rating.",
         size=14, color=DARK, space_before=4)
add_para(tb, "But Brant test rejected the proportional-odds assumption",
         size=16, bold=True, color=ACCENT, space_before=14)
add_para(tb, "Overall test: χ² = 18.8, df = 7, p = 0.009",
         size=14, color=DARK, bullet=True, space_before=4)
add_para(tb, "Violations: sentiment (p = 0.002) and ln(review_age) (p = 0.005)",
         size=14, color=DARK, bullet=True, space_before=4)
add_para(tb, "Multinomial logit removes the assumption by design",
         size=16, bold=True, color=ACCENT, space_before=14)
add_para(tb, "Each category comparison (MID vs TOP, LOW vs TOP) gets its own coefficients — no equality constraint imposed.",
         size=14, color=DARK, space_before=4)
add_para(tb, "Trade-off: the ordinal structure of the rating is not imposed on the fit; however, within-±1 accuracy of 95% confirms the ordering is still captured empirically.",
         size=13, italic=True, color=MUTED, space_before=10)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 12 — Section Title: Results
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_SECTION)
set_title(s, "3. Results")
tb = add_textbox(s, 0.6, 2.8, 12.0, 1.5)
add_para(tb, "Model fit · M1 Revisit · M2 Rating · Joint interpretation",
         size=20, italic=True, color=MUTED, first=True)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 13 — Model fit summary (table)
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Model fit summary")

tbl = s.shapes.add_table(10, 3, Inches(0.6), Inches(1.4),
                          Inches(12.0), Inches(5.0)).table
headers = ["Statistic", "M1 Revisit", "M2 Rating"]
for j, h in enumerate(headers):
    cell = tbl.cell(0, j); cell.text = ""
    _set_para(cell.text_frame.paragraphs[0], h, size=14, bold=True,
              color=WHITE, name=FONT_HEAD, align=PP_ALIGN.CENTER)
    cell.fill.solid(); cell.fill.fore_color.rgb = ACCENT

rows = [
    ("Model type",                 "Binary logit",      "Multinomial logit"),
    ("Reference category",         "no revisit (0)",     "TOP (5★)"),
    ("N observations",             "11,165",             "4,044"),
    ("Predictors",                 "6",                  "5 (per comparison)"),
    ("Place fixed effects",        "28",                 "28 (per comparison)"),
    ("Pseudo-R²",                  "0.201",              "0.190"),
    ("AIC",                        "9,601.5",            "4,753.6"),
    ("BIC",                        "9,857.7",            "5,157.1"),
    ("AUC / Exact accuracy (CV)",  "0.80",               "0.77 (within ±1: 0.95)"),
]
for i, row in enumerate(rows, 1):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j); cell.text = ""
        _set_para(cell.text_frame.paragraphs[0], val, size=12, color=DARK,
                  align=(PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER))

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 14 — Model 1 Revisit results (table + forest)
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Model 1 — Revisit (binary logit, N=11,165)")

# Left: table
tbl = s.shapes.add_table(7, 3, Inches(0.4), Inches(1.4),
                          Inches(6.0), Inches(3.6)).table
headers = ["Variable", "OR", "p"]
for j, h in enumerate(headers):
    cell = tbl.cell(0, j); cell.text = ""
    _set_para(cell.text_frame.paragraphs[0], h, size=12, bold=True,
              color=WHITE, align=PP_ALIGN.CENTER)
    cell.fill.solid(); cell.fill.fore_color.rgb = ACCENT

rows = [
    ("Waited",             "0.54", "0.001 **"),
    ("Tourist",            "0.55", "<.001 ***"),
    ("Sentiment",          "0.74", "<.001 ***"),
    ("Alone",              "2.26", "<.001 ***"),
    ("ln(1+reviews)",      "1.31", "<.001 ***"),
    ("ln(1+followers)",    "1.23", "<.001 ***"),
]
for i, row in enumerate(rows, 1):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j); cell.text = ""
        _set_para(cell.text_frame.paragraphs[0], val, size=11, color=DARK,
                  align=(PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER))

# Right: forest plot image
fig_path = Path("../../data/analysis/naver/workshop/FINAL/figures/forest_m1.png")
if fig_path.exists():
    s.shapes.add_picture(str(fig_path), Inches(6.6), Inches(1.4),
                          width=Inches(6.4), height=Inches(3.2))

tb = add_textbox(s, 0.4, 5.2, 12.5, 2.0)
add_para(tb, "Headline: waiting at the entrance halves the odds of a revisit (OR 0.54). Alone visitors are 2.3× more likely to return. Tourists are 45% less likely.",
         size=13, italic=True, color=MUTED, first=True)
add_para(tb, "Pseudo-R² = 0.201 · AUC = 0.80 (5-fold CV grouped by reviewer)",
         size=12, color=MUTED, space_before=4)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 15 — Model 2 Rating results (table)
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Model 2 — Rating (multinomial logit, N=4,044)")

tbl = s.shapes.add_table(6, 5, Inches(0.4), Inches(1.4),
                          Inches(12.5), Inches(3.2)).table
# Column headers (merged top row would be ideal, keep simple)
hdrs = ["Variable", "OR (MID vs TOP)", "p (MID)", "OR (LOW vs TOP)", "p (LOW)"]
for j, h in enumerate(hdrs):
    cell = tbl.cell(0, j); cell.text = ""
    _set_para(cell.text_frame.paragraphs[0], h, size=12, bold=True,
              color=WHITE, align=PP_ALIGN.CENTER)
    cell.fill.solid(); cell.fill.fore_color.rgb = ACCENT

rows = [
    ("Sentiment",       "0.44",  "<.001 ***",  "0.04",  "<.001 ***"),
    ("Waited",          "1.21",  "0.326",      "3.10",  "<.001 ***"),
    ("ln(1+followers)", "0.95",  "0.287",      "0.71",  "<.001 ***"),
    ("ln(1+photos)",    "0.81",  "0.197",      "0.44",  "0.043 *"),
    ("Season autumn",   "0.39",  "<.001 ***",  "0.38",  "<.001 ***"),
]
for i, row in enumerate(rows, 1):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j); cell.text = ""
        _set_para(cell.text_frame.paragraphs[0], val, size=11, color=DARK,
                  align=(PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER))

tb = add_textbox(s, 0.4, 4.8, 12.5, 2.4)
add_para(tb, "Key insight: predictors operate ASYMMETRICALLY across comparisons",
         size=14, bold=True, color=ACCENT, first=True)
add_para(tb, "waited: not significant for MID vs TOP, but TRIPLES odds of LOW vs TOP → 'disaster signal', not 'mediocrity signal'",
         size=12, color=DARK, bullet=True, space_before=6)
add_para(tb, "sentiment: dominant in both, but far stronger for LOW (OR 0.04) than MID (OR 0.44) — partly mechanical since both from same text",
         size=12, color=DARK, bullet=True, space_before=4)
add_para(tb, "season_autumn: equal protective effect on both MID and LOW (OR ≈ 0.4) — autumn is Korean tourism peak",
         size=12, color=DARK, bullet=True, space_before=4)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 16 — Forest plot M2
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Model 2 — Visualising asymmetric effects")
fig_path = Path("../../data/analysis/naver/workshop/FINAL/figures/forest_m2.png")
if fig_path.exists():
    s.shapes.add_picture(str(fig_path), Inches(0.5), Inches(1.5),
                          width=Inches(12.3), height=Inches(3.2))
tb = add_textbox(s, 0.5, 5.0, 12.3, 2.0)
add_para(tb, "Each row is one predictor. Left panel: effect on MID vs TOP. Right panel: effect on LOW vs TOP. Blue = significant at p<0.05.",
         size=13, italic=True, color=MUTED, first=True)
add_para(tb, "The multinomial decomposition is visible: 'waited' hardly moves MID (left) but strongly pushes LOW (right); sentiment pushes both strongly in the same direction.",
         size=13, color=DARK, space_before=6)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 17 — Divergence and the latent satisfaction frame
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Divergent traces of satisfaction")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Revisit and Rating are weakly correlated (r = 0.08)",
         size=16, bold=True, color=ACCENT, first=True)
add_para(tb, "In the shared sample (N = 4,044), the correlation between revisit and the five-star indicator is only 0.08 → shared variance ≈ 0.6%. The two outcomes capture distinct aspects of satisfaction, not the same construct.",
         size=14, color=DARK, space_before=6)
add_para(tb, "Shared predictors operate differently", size=16, bold=True,
         color=ACCENT, space_before=16)
add_para(tb, "waited  —  M1: OR 0.54 (↓ revisit) · M2: OR 3.10 for LOW (↑ bad rating) — convergent direction, different magnitude",
         size=13, color=DARK, bullet=True, space_before=6)
add_para(tb, "sentiment  —  M1: OR 0.74 (↓ revisit) · M2: OR 0.04 for LOW (massive protective) — different roles",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "ln(followers)  —  M1: OR 1.23 (↑ revisit) · M2: OR 0.71 for LOW (protective) — convergent",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Takeaway: declared satisfaction (rating) and behavioural satisfaction (revisit) are related but genuinely distinct traces of a latent construct.",
         size=13, italic=True, color=MUTED, space_before=14)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 18 — Section Title: Conclusion
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_SECTION)
set_title(s, "4. Conclusion")
tb = add_textbox(s, 0.6, 2.8, 12.0, 1.5)
add_para(tb, "Summary · Implications · Limitations",
         size=20, italic=True, color=MUTED, first=True)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 19 — Summary + Implications
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Summary and implications")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Main findings", size=16, bold=True, color=ACCENT, first=True)
add_para(tb, "Waiting is the strongest and most consistent negative predictor: halves revisit odds, triples odds of a LOW rating",
         size=13, color=DARK, bullet=True, space_before=6)
add_para(tb, "Reviewer-identity (followers, prior reviews) predicts revisit; weak for rating",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Tourists ↓ revisit; alone visitors ↑ revisit (opposite social signals)",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Autumn ↑ TOP rating; season_autumn OR ≈ 0.4 for both MID and LOW",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Implications", size=16, bold=True, color=ACCENT, space_before=16)
add_para(tb, "Attraction managers: reduce entrance waiting — one lever affects BOTH outcomes",
         size=13, color=DARK, bullet=True, space_before=6)
add_para(tb, "Platforms: reviewer-retention investment likely outperforms content-side nudges for driving revisit",
         size=13, color=DARK, bullet=True, space_before=4)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 20 — Limitations
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CONTENT)
set_title(s, "Limitations and future work")
tb = add_textbox(s, 0.6, 1.5, 12.0, 5.5)
add_para(tb, "Limitations", size=16, bold=True, color=ACCENT, first=True)
add_para(tb, "Associations only — cross-sectional design, no causal identification",
         size=13, color=DARK, bullet=True, space_before=6)
add_para(tb, "M1 profiles returning visitors, does not explain why anyone returns (temporal ordering)",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Sentiment-rating association partly mechanical (same reviewing session)",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "MID rating class is sandwiched between TOP (75%) and LOW (7%); multinomial routes most predictions to the extremes",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Single platform (Naver); nothing separates its reviewer population from Korean reviewers at large",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Future work", size=16, bold=True, color=ACCENT, space_before=16)
add_para(tb, "Add month fixed effects + Hausman test (FE vs RE)",
         size=13, color=DARK, bullet=True, space_before=6)
add_para(tb, "Instrumental variable for waiting (natural experiment, event study)",
         size=13, color=DARK, bullet=True, space_before=4)
add_para(tb, "Cross-platform validation (Kakao, Google Maps) if comparable visit-context data become available",
         size=13, color=DARK, bullet=True, space_before=4)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 21 — Thank You
# ═══════════════════════════════════════════════════════════════════════════
s = p.slides.add_slide(L_CLOSE)
for ph in s.placeholders:
    tf = ph.text_frame; tf.clear()
    try:
        idx = ph.placeholder_format.idx
    except Exception:
        continue
    if idx == 0:
        _set_para(tf.paragraphs[0], "Thank you · 감사합니다", size=36,
                  bold=True, color=DARK, name=FONT_HEAD)
    else:
        _set_para(tf.paragraphs[0], "Questions and discussion",
                  size=18, italic=True, color=MUTED)

tb = add_textbox(s, 0.6, 5.5, 12.0, 1.5)
add_para(tb, "Jorge Adan Soriano Hernandez · 소리아노 에르난데스 호르헤 아단",
         size=14, color=MUTED, first=True)
add_para(tb, "adan_25@naver.com", size=13, italic=True, color=MUTED)
add_para(tb, "Hoseo University · 호서대학교 데이터사이언스학과",
         size=12, color=MUTED)

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(OUT)
print(f"Done: {len(p.slides)} slides written to {OUT}")
