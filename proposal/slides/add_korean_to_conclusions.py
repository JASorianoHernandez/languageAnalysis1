"""
add_korean_to_conclusions.py

Add Korean translation lines to each English bullet in slide 16
(Conclusions). Preserves user's current structure:
  - Title: "Conclusions 결론"
  - Shape 1: Results 결과 (two bullets)
  - Shape 2: Limitations 한계 (two bullets)

Korean lines go directly under each English bullet, italic, muted #555555,
smaller size (16 pt) — matches the bilingual slide format in
reference_pptx_formats.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

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
slide = p.slides[15]

# Find the two body textboxes (not the title)
bodies = [sh for sh in slide.shapes
          if sh.name.startswith("TextBox") and sh.has_text_frame]
assert len(bodies) == 2, f"Expected 2 TextBoxes, got {len(bodies)}"

results_box, limits_box = bodies[0], bodies[1]

# ── Shape 1: Results ───────────────────────────────────────────────────────
# Keep: header "Results 결과", then two bullets each followed by Korean line
tf = results_box.text_frame
tf.clear()
add_para(tf, "Results  결과",
         size=24, bold=True, color=HEAD, first=True)
add_para(tf, "", size=4, space_before=2)
add_para(tf,
         "•  Visit context (waited, companion, tourist) predicts revisit, "
         "beyond reviewer traits and sentiment.",
         size=20, color=DARK, space_before=8)
add_para(tf,
         "   방문 맥락(대기, 동반자, 관광객 여부)이 리뷰어 특성과 감성을 넘어 "
         "재방문을 예측한다.",
         size=15, italic=True, color=MUTED, space_before=3)
add_para(tf,
         "•  Revisit and rating are related but distinct traces of "
         "satisfaction (r = 0.08).",
         size=20, color=DARK, space_before=10)
add_para(tf,
         "   재방문과 별점은 관련은 있지만 만족도의 서로 다른 흔적이다 "
         "(r = 0.08).",
         size=15, italic=True, color=MUTED, space_before=3)

print("Results box updated with Korean lines.")

# ── Shape 2: Limitations ───────────────────────────────────────────────────
tf = limits_box.text_frame
tf.clear()
add_para(tf, "Limitations  한계",
         size=24, bold=True, color=HEAD, first=True)
add_para(tf, "", size=4, space_before=2)
add_para(tf,
         "•  Observational data, no causal identification necessarily.",
         size=20, color=DARK, space_before=8)
add_para(tf,
         "   관측 자료이므로 인과관계를 반드시 식별할 수는 없다.",
         size=15, italic=True, color=MUTED, space_before=3)
add_para(tf,
         "•  Most attractions are from Seoul metropolitan area; "
         "generalization to other regions requires replication.",
         size=20, color=DARK, space_before=10)
add_para(tf,
         "   대부분의 관광지가 서울 수도권에 위치하므로, 다른 지역으로의 "
         "일반화에는 반복 연구가 필요하다.",
         size=15, italic=True, color=MUTED, space_before=3)

print("Limitations box updated with Korean lines.")

p.save(PPTX)
print(f"\nSaved to: {PPTX}")
