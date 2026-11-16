"""
expand_intro_and_rqs.py

Two changes:

1. Slide 4 (Introduction): expand the problem statement.
   - Keep: title, 3 pictures, footer citation.
   - Rewrite: English textbox and Korean textbox with 3 bullets each
     (Naver uniqueness, two-level prior work, gap).
   - No em-dashes.

2. Slide 5 (Research Questions): add a "Contribution" block.
   - Compress RQ1 and RQ2 boxes slightly.
   - Add a third textbox with twofold contribution.
   - No em-dashes.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE_TYPE

PPTX = "presentation_v2.pptx"

FONT_BODY = "Source Sans Pro Light"
DARK  = RGBColor(0x22, 0x22, 0x22)
MUTED = RGBColor(0x55, 0x55, 0x55)
HEAD  = RGBColor(0x23, 0x31, 0x2D)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


def add_para(tf, text, size, bold=False, italic=False, color=DARK,
             space_before=4, first=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_before = Pt(space_before)
    p.text = text
    p.alignment = PP_ALIGN.LEFT
    for run in p.runs:
        _font(run, FONT_BODY, size, bold=bold, italic=italic, color=color)


# ─── Load ──────────────────────────────────────────────────────────────────
p = Presentation(PPTX)

# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Introduction
# ═══════════════════════════════════════════════════════════════════════════
slide = p.slides[3]
print(f"Slide 4 shapes: {len(slide.shapes)}")

en_box = next(s for s in slide.shapes if s.name == "TextBox 11")
ko_box = next(s for s in slide.shapes if s.name == "TextBox 12")

# ── English column ─────────────────────────────────────────────────────────
tf = en_box.text_frame
tf.word_wrap = True
tf.clear()
add_para(tf, "Online reviews drive travel decisions.",
         size=16, bold=True, color=HEAD, first=True)
add_para(tf, "", size=4, space_before=2)
add_para(tf,
         "•  Naver Place uniquely records visit context (companion, "
         "purpose, wait, reservation).",
         size=12, color=DARK, space_before=8)
add_para(tf, "", size=3, space_before=2)
add_para(tf,
         "•  Prior work analyses text alone or aggregates to business "
         "level, missing individual context.",
         size=12, color=DARK, space_before=6)
add_para(tf, "", size=3, space_before=2)
add_para(tf,
         "•  How specific context shapes a specific review has not "
         "been addressed.",
         size=12, color=DARK, space_before=6)

# ── Korean column ──────────────────────────────────────────────────────────
tf = ko_box.text_frame
tf.word_wrap = True
tf.clear()
add_para(tf, "온라인 리뷰는 여행 결정을 좌우한다.",
         size=16, bold=True, color=HEAD, first=True)
add_para(tf, "", size=4, space_before=2)
add_para(tf,
         "•  네이버 플레이스는 방문 맥락(동반자, 목적, 대기, 예약)을 "
         "기록한다.",
         size=12, color=DARK, space_before=8)
add_para(tf, "", size=3, space_before=2)
add_para(tf,
         "•  기존 연구는 텍스트만 분석하거나 업체 단위로 집계하여 개별 "
         "맥락을 놓친다.",
         size=12, color=DARK, space_before=6)
add_para(tf, "", size=3, space_before=2)
add_para(tf,
         "•  특정 방문 맥락이 특정 리뷰를 어떻게 좌우하는지는 "
         "다루지 않았다.",
         size=12, color=DARK, space_before=6)

print("  Slide 4 text updated (3 bullets each column, no em-dashes).")


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Research Questions + Contribution
# ═══════════════════════════════════════════════════════════════════════════
slide = p.slides[4]
print(f"\nSlide 5 shapes: {len(slide.shapes)}")

# Reposition and compress RQ1, RQ2 to make room for Contribution box
rq1 = next(s for s in slide.shapes if s.name == "TextBox 2")
rq2 = next(s for s in slide.shapes if s.name == "TextBox 3")

rq1.top = Inches(1.40)
rq1.height = Inches(1.45)
rq2.top = Inches(2.95)
rq2.height = Inches(1.45)

# Add Contribution box
cb = slide.shapes.add_textbox(Inches(0.60), Inches(4.55),
                                Inches(12.00), Inches(2.60))
tf = cb.text_frame
tf.word_wrap = True
add_para(tf, "Our Contribution  저희의 기여",
         size=20, bold=True, color=HEAD, first=True)
add_para(tf, "", size=4, space_before=2)
add_para(tf,
         "(1)  First study to exploit Naver Place visit context at the "
         "individual-review level.",
         size=14, color=DARK, space_before=6)
add_para(tf,
         "       네이버 플레이스의 방문 맥락을 개별 리뷰 수준에서 "
         "활용한 최초의 연구.",
         size=12, italic=True, color=MUTED, space_before=2)
add_para(tf,
         "(2)  Both outcomes modelled in parallel: declared and "
         "behavioural satisfaction are related but distinct traces of a "
         "latent construct.",
         size=14, color=DARK, space_before=6)
add_para(tf,
         "       두 결과를 병렬 모델링하여, 선언된 만족도와 행동적 "
         "만족도가 관련은 있지만 잠재적 구성개념의 서로 다른 흔적임을 "
         "보여준다.",
         size=12, italic=True, color=MUTED, space_before=2)

print("  Slide 5 updated (RQ1/RQ2 compressed; Contribution box added).")

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"\nSaved to: {PPTX}")
