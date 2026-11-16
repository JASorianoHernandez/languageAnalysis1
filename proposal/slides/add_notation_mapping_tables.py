"""
add_notation_mapping_tables.py
Append two new slides AFTER Models (slide 14) with the two reference tables
from the paper (Table 5 Model Notation + Table 6 Variable-to-Model Mapping),
then move them to positions 15 and 16 so existing slides 15-20 shift to 17-22.

IMPORTANT: this script only appends and moves. It does NOT delete, modify,
or re-create any existing slide. Manual edits are preserved.

Run (base env):  python add_notation_mapping_tables.py
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
HEADER_GREY = RGBColor(0xE8, 0xE8, 0xE8)
ALT_GREY    = RGBColor(0xF8, 0xF8, 0xF8)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
SECTION_BG  = RGBColor(0xDE, 0xDE, 0xDE)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None):
    run.font.name = name
    if size is not None:  run.font.size = Pt(size)
    if bold is not None:  run.font.bold = bold
    if italic is not None: run.font.italic = italic


def _remove_ph(slide, idx):
    for shape in list(slide.shapes):
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == idx:
                shape._element.getparent().remove(shape._element)
        except Exception:
            pass


def _set_title_top(slide, en, ko):
    title = slide.shapes.title
    title.left = Inches(0.45); title.top = Inches(0.40)
    title.width = Inches(11.5); title.height = Inches(0.95)
    tf = title.text_frame
    tf.clear()
    p_en = tf.paragraphs[0]; p_en.text = en; p_en.alignment = PP_ALIGN.LEFT
    for run in p_en.runs: _font(run, FONT_HEAD)
    p_ko = tf.add_paragraph(); p_ko.text = ko; p_ko.alignment = PP_ALIGN.LEFT
    for run in p_ko.runs: _font(run, FONT_HEAD, 20)


def _add_slide_number(slide):
    sn = slide.shapes.add_textbox(Inches(9.33), Inches(6.69), Inches(3.0), Inches(0.40))
    sn.text_frame.paragraphs[0].text = ""


def _cell(cell, text, bold=False, size=10, align_left=True, fill=None, italic=False):
    cell.margin_left = Inches(0.08)
    cell.margin_right = Inches(0.08)
    cell.margin_top = Inches(0.02)
    cell.margin_bottom = Inches(0.02)
    tf = cell.text_frame
    tf.word_wrap = True
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.LEFT if align_left else PP_ALIGN.CENTER
    for run in p.runs:
        _font(run, FONT_BODY, size, bold=bold, italic=italic)
    if fill is not None:
        cell.fill.solid()
        cell.fill.fore_color.rgb = fill


# ─── Slide 15: Model Notation (Table 5) ───────────────────────────────────
def build_notation_slide(prs):
    layout = prs.slide_masters[0].slide_layouts[3]
    slide = prs.slides.add_slide(layout)
    _remove_ph(slide, 10)
    _remove_ph(slide, 11)
    _set_title_top(slide, "Model Notation", "모형 표기")
    _add_slide_number(slide)

    # Rows: (Model_group, Symbol, Description, is_header, section_header)
    rows = [
        ("Model",     "Symbol",         "Description", True,  False),
        # M1
        ("M1",        "i, j",            "Review i at place j", False, False),
        ("",          "β₀",              "Intercept", False, False),
        ("",          "xᵢⱼ′ β",          "Vector of regressors (visit context + controls) and their coefficients", False, False),
        ("",          "δⱼ",              "Place fixed effect (one per attraction)", False, False),
        # M2, M3
        ("M2, M3",    "i, j",            "Review i at place j", False, False),
        ("",          "β₀",              "Intercept", False, False),
        ("",          "xᵢⱼ′ β",          "Vector of regressors and their coefficients", False, False),
        ("",          "δⱼ",              "Place fixed effect", False, False),
        ("",          "τₖ",              "Ordered logit threshold for category k", False, False),
        ("",          "k",               "Outcome category (M2: 0 … 4; M3: 1 … 4)", False, False),
        # M4
        ("M4",        "i, j",            "Review i at place j", False, False),
        ("",          "β₀",              "Intercept", False, False),
        ("",          "xᵢⱼ′ β",          "Vector of regressors and their coefficients", False, False),
        ("",          "δⱼ",              "Place fixed effect", False, False),
        ("",          "μᵢⱼ",             "Expected reaction count", False, False),
        ("",          "γ",               "Log-age elasticity (offset for review age)", False, False),
        ("",          "α",               "Negative binomial dispersion (α̂ = 2.44; variance ≈ 37×mean)", False, False),
    ]
    n_rows = len(rows)
    tbl_shape = slide.shapes.add_table(n_rows, 3,
                                        Inches(0.60), Inches(1.60),
                                        Inches(12.1), Inches(5.0))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(1.4)
    tbl.columns[1].width = Inches(2.1)
    tbl.columns[2].width = Inches(8.6)

    for i, (model, symbol, desc, is_header, _sect) in enumerate(rows):
        fill = HEADER_GREY if is_header else (WHITE if i % 2 == 1 else ALT_GREY)
        _cell(tbl.cell(i, 0), model, bold=is_header or (model != ""), size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 1), symbol, bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 2), desc, bold=is_header, size=11 if is_header else 10, fill=fill)

    return slide


# ─── Slide 16: Variable-to-Model Mapping (Table 6) ────────────────────────
def build_mapping_slide(prs):
    layout = prs.slide_masters[0].slide_layouts[3]
    slide = prs.slides.add_slide(layout)
    _remove_ph(slide, 10)
    _remove_ph(slide, 11)
    _set_title_top(slide, "Variable-to-Model Mapping", "변수-모형 매핑")
    _add_slide_number(slide)

    # (Type, Concept, Column, Scale, M1, M2, M3, M4, is_header, is_section)
    rows = [
        ("Type", "Concept (Table 2)", "Dataset column(s)", "Scale",
         "M1", "M2", "M3", "M4", True, False),
        # DV section
        ("Dependent variables / 종속변수", "", "", "", "", "", "", "", False, True),
        ("DV", "Revisit", "revisit",   "bin.",      "Yᵢⱼ", "βₖ", "βₖ", "βₖ", False, False),
        ("DV", "Keyword Count", "n_tags", "ord. 0–5", "βₖ", "Yᵢⱼ", "βₖ", "βₖ", False, False),
        ("DV", "Rating", "rating",      "ord. 1–5",  "–",   "–",   "Yᵢⱼ", "–",  False, False),
        ("DV", "Reactions", "reactions", "count",    "–",   "–",   "–",   "Yᵢⱼ", False, False),
        # IV section
        ("Independent variables / 독립변수", "", "", "", "", "", "", "", False, True),
        ("IV", "Companion", "comp_* (×6)", "bin.",    "βₖ×6", "βₖ×6", "βₖ×4ᵃ", "βₖ×6", False, False),
        ("IV", "Purpose",   "purp_* (×5)", "bin.",    "βₖ×5", "βₖ×5", "βₖ×2ᵃ", "βₖ×5", False, False),
        ("IV", "Waited",    "waited",      "bin.",    "βₖ",   "βₖ",   "–",     "βₖ",   False, False),
        ("IV", "Reserved",  "reserved",    "bin.",    "βₖ",   "βₖ",   "βₖ",    "βₖ",   False, False),
        ("IV", "Sentiment", "sentiment",   "cont.",   "βₖ",   "–",    "–ᵇ",    "βₖ",   False, False),
        ("IV", "Tag themes","tag_* (×10)", "bin.",    "–",    "–",    "–",     "–ᶜ",   False, False),
        ("IV", "Has text",  "has_text",    "bin.",    "–",    "βₖ",   "βₖ",    "–",    False, False),
        ("IV", "Visit info","has_visit_info", "bin.", "βₖ",   "βₖ",   "–",     "βₖ",   False, False),
        # Control section
        ("Control variables / 통제변수", "", "", "", "", "", "", "", False, True),
        ("Ctrl", "Text Length",      "ln_length",         "cont.",  "βₖ", "–",  "βₖ", "βₖ",   False, False),
        ("Ctrl", "User Reviews",     "ln_user_reviews",   "cont.",  "βₖ", "βₖ", "βₖ", "βₖ",   False, False),
        ("Ctrl", "User Followers",   "ln_user_followers", "cont.",  "–",  "–",  "–",  "βₖ",   False, False),
        ("Ctrl", "Review Age",       "ln_review_age",     "cont.",  "–",  "–",  "–",  "γ",    False, False),
        ("Ctrl", "Season",           "season_* (×3)",     "bin.",   "–",  "–",  "–",  "βₖ×3", False, False),
        ("Ctrl", "Weekend",          "visit_weekend",     "bin.",   "–",  "–",  "–",  "βₖ",   False, False),
        ("Ctrl", "Verification",     "verif_receipt",     "bin.",   "–",  "–",  "–",  "βₖ",   False, False),
        ("Ctrl", "Place FE",         "(absorbed)",        "categ.", "δⱼ", "δⱼ", "δⱼ", "δⱼ",   False, False),
    ]
    n_rows = len(rows)
    tbl_shape = slide.shapes.add_table(n_rows, 8,
                                        Inches(0.30), Inches(1.60),
                                        Inches(12.7), Inches(4.6))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(0.95)   # Type
    tbl.columns[1].width = Inches(2.00)   # Concept
    tbl.columns[2].width = Inches(2.60)   # Column
    tbl.columns[3].width = Inches(1.00)   # Scale
    tbl.columns[4].width = Inches(1.55)   # M1
    tbl.columns[5].width = Inches(1.55)   # M2
    tbl.columns[6].width = Inches(1.55)   # M3
    tbl.columns[7].width = Inches(1.50)   # M4

    for i, row in enumerate(rows):
        is_header = row[8]
        is_section = row[9]
        if is_header:
            fill = HEADER_GREY
        elif is_section:
            fill = SECTION_BG
        else:
            fill = WHITE if i % 2 == 1 else ALT_GREY
        # Section rows: merge columns and show label
        if is_section:
            # Fill all cells in this row with section color and bold label
            label = row[0]
            # Merge not fully supported; just put label in cell 0 and empty in others
            for j in range(8):
                _cell(tbl.cell(i, j), label if j == 0 else "", bold=True, size=10, fill=fill, italic=True)
            continue
        _cell(tbl.cell(i, 0), row[0], bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 1), row[1], bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 2), row[2], bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 3), row[3], bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 4), row[4], bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 5), row[5], bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 6), row[6], bold=is_header, size=11 if is_header else 10, fill=fill)
        _cell(tbl.cell(i, 7), row[7], bold=is_header, size=11 if is_header else 10, fill=fill)

    # Legend / notes at the bottom
    note = slide.shapes.add_textbox(Inches(0.30), Inches(6.25), Inches(12.7), Inches(0.60))
    ntf = note.text_frame
    ntf.word_wrap = True
    np = ntf.paragraphs[0]
    np.text = ("Scale: bin. = binary (0/1); ord. = ordinal; cont. = continuous "
               "(log-transformed); count = non-negative integer.")
    for run in np.runs: _font(run, FONT_BODY, 9, italic=True)
    np2 = ntf.add_paragraph()
    np2.text = ("Notation: βₖ = enters xᵢⱼ′ β with coefficient βₖ ; Yᵢⱼ = outcome "
                "(left-hand side); δⱼ = place fixed effect ; γ = ln_review_age "
                "as exposure offset in M4 ; βₖ×N = N dummies each with their own βₖ .")
    for run in np2.runs: _font(run, FONT_BODY, 9, italic=True)
    np3 = ntf.add_paragraph()
    np3.text = ("ᵃ Partial dummies in M3 (only 32% of reviews have a rating).   "
                "ᵇ Excluded from M3: r = 0.51 with rating; VIF risk.   "
                "ᶜ Tag themes only in extended models M1b, M1x.")
    for run in np3.runs: _font(run, FONT_BODY, 9, italic=True)

    return slide


# ─── Apply ────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
total_before = len(p.slides)
print(f"Before: {total_before} slides")

build_notation_slide(p)   # appended at end
build_mapping_slide(p)    # appended at end

# Move them to positions 15 and 16 (0-indexed 14 and 15), i.e. right after Models.
xml_slides = p.slides._sldIdLst
slides_list = list(xml_slides)
new_notation = slides_list[-2]
new_mapping  = slides_list[-1]
xml_slides.remove(new_notation)
xml_slides.remove(new_mapping)
xml_slides.insert(14, new_notation)   # becomes slide 15
xml_slides.insert(15, new_mapping)    # becomes slide 16

p.save(PPTX)
print(f"After:  {len(p.slides)} slides")
print("  Slide 15 (NEW): Model Notation / 모형 표기")
print("  Slide 16 (NEW): Variable-to-Model Mapping / 변수-모형 매핑")
print("  (Previous slides 15-20 shift to 17-22)")
