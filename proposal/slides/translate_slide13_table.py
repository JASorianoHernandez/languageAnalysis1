"""
translate_slide13_table.py

Slide 13 is a duplicate of Slide 12 (Models & Variables). The user wants
Slide 13 to serve as the Korean-language mirror of the same table.

Only the TABLE on slide 13 is modified. Title stays. Row 1 (the variable
names: sentiment, waited, ln(1+followers), is_tourist, comp_alone,
ln(1+reviews), ln(1+photos), season_autumn, plus Revisit and Rating)
stays untouched because the user said "a excepción de los nombres de las
variables".

Everything else in the table is translated to Korean while preserving the
reference format (Source Sans Pro Light, 11 pt, bold, no fill — per
reference_pptx_formats memory).
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX = "presentation_v2.pptx"

FONT_BODY = "Source Sans Pro Light"
DARK = RGBColor(0x22, 0x22, 0x22)


def _font(run, name=FONT_BODY, size=11, bold=True, color=DARK):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def set_cell(cell, text, align=PP_ALIGN.CENTER, size=11):
    """Overwrite a table cell preserving the reference table format."""
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    p.text = text
    p.alignment = align
    for run in p.runs:
        _font(run, FONT_BODY, size, bold=True, color=DARK)


# ─── Load ──────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
slide = p.slides[12]   # Slide 13, 0-indexed
tbl = None
for sh in slide.shapes:
    if sh.has_table:
        tbl = sh.table
        break
assert tbl is not None, "No table found on slide 13."
assert len(tbl.rows) == 5 and len(tbl.columns) == 11, \
    f"Unexpected table shape {len(tbl.rows)}x{len(tbl.columns)}"

# ─── Row 0 — merged headers over DV and IV blocks ─────────────────────────
# Columns 1-2 are DV, columns 3-10 are IV. Translate the two header labels.
set_cell(tbl.cell(0, 1), "종속변수", size=12)        # Dependent Variables
set_cell(tbl.cell(0, 3), "독립변수", size=12)        # Independent Variables

# ─── Row 1 — variable names: KEEP AS IS, only translate the row label ────
set_cell(tbl.cell(1, 0), "변수명", align=PP_ALIGN.LEFT)   # Variable Name
# cols 1-10 stay untouched (Revisit, Rating, sentiment, waited, ...)

# ─── Row 2 — Description ─────────────────────────────────────────────────
set_cell(tbl.cell(2, 0), "설명", align=PP_ALIGN.LEFT)              # Description
set_cell(tbl.cell(2, 1), "두 번 이상 방문")                        # Revisit
set_cell(tbl.cell(2, 2), "0-5점 별점 리뷰")                        # Rating
set_cell(tbl.cell(2, 3), "텍스트의 BERT 감성 점수")                 # sentiment
set_cell(tbl.cell(2, 4), "입구에서 대기 여부")                      # waited
set_cell(tbl.cell(2, 5), "리뷰어의 팔로워 수")                      # ln(1+followers)
set_cell(tbl.cell(2, 6), "방문 목적이 '여행'")                      # is_tourist
set_cell(tbl.cell(2, 7), "혼자 방문")                              # comp_alone
set_cell(tbl.cell(2, 8), "리뷰어의 기존 리뷰 수")                   # ln(1+reviews)
set_cell(tbl.cell(2, 9), "리뷰에 첨부된 사진 수")                   # ln(1+photos)
set_cell(tbl.cell(2, 10), "가을에 방문")                           # season_autumn

# ─── Row 3 — Type ────────────────────────────────────────────────────────
set_cell(tbl.cell(3, 0), "유형", align=PP_ALIGN.LEFT)              # Type
set_cell(tbl.cell(3, 1), "이항")                                   # Binary
set_cell(tbl.cell(3, 2), "범주형 (3개 범주)")                      # Categorical (3-class)
set_cell(tbl.cell(3, 3), "연속형 [-1, 1]")                         # Continuous [-1, 1]
set_cell(tbl.cell(3, 4), "이항 {0, 1}")                            # Binary {0, 1}
set_cell(tbl.cell(3, 5), "연속형 (로그)")                          # Continuous (log)
set_cell(tbl.cell(3, 6), "이항 {0, 1}")                            # Binary {0, 1}
set_cell(tbl.cell(3, 7), "이항 {0, 1}")                            # Binary {0, 1}
set_cell(tbl.cell(3, 8), "연속형 (로그)")                          # Continuous (log)
set_cell(tbl.cell(3, 9), "연속형 (로그)")                          # Continuous (log)
set_cell(tbl.cell(3, 10), "이항 {0, 1}")                           # Binary {0, 1}

# ─── Row 4 — Model Used (M1/M2 technical labels kept) ────────────────────
set_cell(tbl.cell(4, 0), "사용된 모형", align=PP_ALIGN.LEFT)       # Model Used
set_cell(tbl.cell(4, 1), "M1")
set_cell(tbl.cell(4, 2), "M2")
set_cell(tbl.cell(4, 3), "M1 및 M2")
set_cell(tbl.cell(4, 4), "M1 및 M2")
set_cell(tbl.cell(4, 5), "M1 및 M2")
set_cell(tbl.cell(4, 6), "M1만")
set_cell(tbl.cell(4, 7), "M1만")
set_cell(tbl.cell(4, 8), "M1만")
set_cell(tbl.cell(4, 9), "M2만")
set_cell(tbl.cell(4, 10), "M2만")

p.save(PPTX)
print(f"Slide 13 table translated to Korean (variable names row untouched).")
print(f"Saved to: {PPTX}")
