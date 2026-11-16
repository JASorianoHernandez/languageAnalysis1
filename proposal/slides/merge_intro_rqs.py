"""
merge_intro_rqs.py
Merge slides 4+5 into a single Introduction slide, and slides 6+7 into a
single Research Questions slide. Preserves the coffee-shop image on the
Introduction slide. Applies the user's standard title format
(Source Sans, 28pt, Bold, #222222, Left) per reference_pptx_formats memory.

Only slides 4, 5, 6, 7 are touched. All other slides are preserved.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from copy import deepcopy
from lxml import etree

from pptx import Presentation
from pptx.util import Pt, Inches, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE_TYPE

PPTX = "presentation_v2.pptx"

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


def set_title(slide, title_text):
    """Apply the reference title format: Source Sans 28pt bold #222222 LEFT."""
    for shape in slide.shapes:
        if shape.name.startswith("Title"):
            tf = shape.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = title_text
            p.alignment = PP_ALIGN.LEFT
            for run in p.runs:
                _font(run, FONT_HEAD, 28, bold=True, color=DARK)
            return


def strip_body_shapes(slide, keep_names=("Title", "Picture")):
    """Remove all shapes whose name does NOT start with one of keep_names."""
    for shape in list(slide.shapes):
        if any(shape.name.startswith(k) for k in keep_names):
            continue
        shape._element.getparent().remove(shape._element)


def add_textbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top),
                                   Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def add_para(tf, text, size=14, bold=False, italic=False, color=DARK,
             bullet=False, space_before=4, first=False,
             name=FONT_BODY, align=PP_ALIGN.LEFT):
    if first:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.space_before = Pt(space_before)
    p.text = ("•  " + text) if bullet else text
    p.alignment = align
    for run in p.runs:
        _font(run, name, size, bold=bold, italic=italic, color=color)


def delete_slide_by_index(p, idx):
    """Delete the slide at 0-indexed idx from the presentation."""
    xml_slides = p.slides._sldIdLst
    slides = list(xml_slides)
    if idx >= len(slides):
        return
    xml_slides.remove(slides[idx])


# ─── Load ───────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
print(f"Loaded. Current slide count: {len(p.slides)}")

# Index 3 = slide 4 (Introduction bilingual + image)
# Index 4 = slide 5 (Introduction English, to delete)
# Index 5 = slide 6 (Research Questions English, to delete)
# Index 6 = slide 7 (Research Questions bilingual)

# ═══════════════════════════════════════════════════════════════════════════
# 1. REWORK SLIDE 4 (index 3) — Merged Introduction
# ═══════════════════════════════════════════════════════════════════════════
slide = p.slides[3]
print(f"\nWorking on slide 4: {slide.slide_layout.name}")

# Find the picture (coffee shop) if present
picture_shapes = [s for s in slide.shapes
                  if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
print(f"  Pictures found: {len(picture_shapes)}")

# Strip text content but KEEP title and pictures
strip_body_shapes(slide, keep_names=("Title", "Picture"))

# Apply title format
set_title(slide, "Introduction / 서론")

# Compute picture position to decide layout
if picture_shapes:
    pic = picture_shapes[0]
    # Keep picture roughly where it is; text goes to its left
    pic_left_inch = pic.left / 914400
    print(f"  Picture at left={pic_left_inch:.2f}in, "
          f"width={pic.width/914400:.2f}in")
    text_width = max(5.0, pic_left_inch - 0.6)
else:
    text_width = 11.5

# Add text content on the left (bilingual two columns)
# Left column: English
en_tb = add_textbox(slide, 0.4, 1.5, text_width/2 - 0.1, 5.0)
add_para(en_tb, "Online reviews drive travel decisions.",
         size=18, bold=True, color=ACCENT, first=True)
add_para(en_tb, "", size=4, space_before=8)
add_para(en_tb, "Naver Place uniquely records visit context "
                "(companion · purpose · wait · reservation).",
         size=13, color=DARK, bullet=True, space_before=10)
add_para(en_tb, "Prior work misses this context at the "
                "individual-review level.",
         size=13, color=DARK, bullet=True, space_before=8)

# Right column: Korean
ko_tb = add_textbox(slide, 0.4 + text_width/2 + 0.1, 1.5,
                     text_width/2 - 0.1, 5.0)
add_para(ko_tb, "온라인 리뷰는 여행 결정을 좌우한다.",
         size=18, bold=True, color=ACCENT, first=True)
add_para(ko_tb, "", size=4, space_before=8)
add_para(ko_tb, "네이버 플레이스는 방문 맥락"
                "(동반자·목적·대기·예약)을 기록한다.",
         size=13, color=DARK, bullet=True, space_before=10)
add_para(ko_tb, "기존 연구는 개별 리뷰의 방문 맥락을 활용하지 않는다.",
         size=13, color=DARK, bullet=True, space_before=8)

# Footer citation
foot = add_textbox(slide, 0.4, 6.9, 10.0, 0.4)
add_para(foot, "[Lee et al., 2026]",
         size=10, italic=True, color=MUTED, first=True)

print("  Slide 4 updated.")

# ═══════════════════════════════════════════════════════════════════════════
# 2. REWORK SLIDE 7 (index 6) — Merged Research Questions
# (We rebuild slide 7 before deleting 5 and 6 so indices stay stable)
# ═══════════════════════════════════════════════════════════════════════════
slide = p.slides[6]
print(f"\nWorking on slide 7: {slide.slide_layout.name}")

# Strip body (keep title and page number only)
strip_body_shapes(slide, keep_names=("Title",))

# Apply title format
set_title(slide, "Research Questions / 연구 질문")

# RQ1 box
rq1_tb = add_textbox(slide, 0.6, 1.6, 12.0, 2.1)
add_para(rq1_tb, "RQ1 — Revisit / 재방문", size=16, bold=True,
         color=ACCENT, first=True)
add_para(rq1_tb, "", size=4, space_before=6)
add_para(rq1_tb, "What predicts a returning visitor?",
         size=15, color=DARK, space_before=8)
add_para(rq1_tb, "재방문자 리뷰를 예측하는 요인은?",
         size=14, italic=True, color=MUTED, space_before=4)

# RQ2 box
rq2_tb = add_textbox(slide, 0.6, 4.0, 12.0, 2.4)
add_para(rq2_tb, "RQ2 — Rating / 별점", size=16, bold=True,
         color=ACCENT, first=True)
add_para(rq2_tb, "", size=4, space_before=6)
add_para(rq2_tb, "What predicts each rating category?",
         size=15, color=DARK, space_before=8)
add_para(rq2_tb, "각 별점 범주를 예측하는 요인은?",
         size=14, italic=True, color=MUTED, space_before=4)
add_para(rq2_tb, "TOP 5★  ·  MID 4-4.5★  ·  LOW ≤3.5★",
         size=14, bold=True, color=ACCENT, space_before=8)

# Footer: predictor pool reminder
foot = add_textbox(slide, 0.6, 6.9, 12.0, 0.4)
add_para(foot, "Predictors: Visit context  +  Reviewer characteristics",
         size=11, italic=True, color=MUTED, first=True,
         align=PP_ALIGN.RIGHT)

print("  Slide 7 updated.")

# ═══════════════════════════════════════════════════════════════════════════
# 3. DELETE old duplicate slides (5 and 6)
# Delete in reverse order to keep indices consistent
# ═══════════════════════════════════════════════════════════════════════════
# Index 5 is slide 6, index 4 is slide 5. Delete 5 first (higher index).
delete_slide_by_index(p, 5)  # removes original slide 6 (English RQs)
print("\n  Deleted slide 6 (duplicate RQs in English only).")
delete_slide_by_index(p, 4)  # removes original slide 5 (English intro)
print("  Deleted slide 5 (duplicate Introduction in English only).")

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"\nFINAL slide count: {len(p.slides)}")
print(f"Saved to: {PPTX}")
