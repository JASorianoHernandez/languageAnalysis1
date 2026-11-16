"""
merge_conclusions_limitations.py

Replace slides 16 (Summary and implications) and 17 (Limitations and future
work) with a single combined slide:  "Conclusions and Limitations".
Two bullets per section (findings, limitations). No em-dashes. No
implications section.

Deck goes from 18 slides to 17.
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

FONT_HEAD = "Source Sans"
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


def set_title(slide, title_text):
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


def strip_body_shapes(slide, keep_names=("Title",)):
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


def add_para(tf, text, size=12, bold=False, italic=False, color=DARK,
             space_before=4, first=False, name=FONT_BODY,
             align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_before = Pt(space_before)
    p.text = text
    p.alignment = align
    for run in p.runs:
        _font(run, name, size, bold=bold, italic=italic, color=color)


def delete_slide_by_index(p, idx):
    xml_slides = p.slides._sldIdLst
    slides = list(xml_slides)
    if idx >= len(slides):
        return
    xml_slides.remove(slides[idx])


# ─── Load ──────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
print(f"Loaded. Slide count: {len(p.slides)}")

# ── 1. Rewrite slide 16 (index 15) ────────────────────────────────────────
slide = p.slides[15]
print(f"\nRewriting slide 16: {slide.slide_layout.name}")

strip_body_shapes(slide, keep_names=("Title",))
set_title(slide, "Conclusions and Limitations / 결론 및 한계")

# Key findings block
kf = add_textbox(slide, 0.6, 1.5, 12.1, 2.8)
add_para(kf, "Key findings / 주요 결과",
         size=18, bold=True, color=HEAD, first=True)
add_para(kf, "", size=4, space_before=4)
add_para(kf,
         "•  Visit context (waited, companion, is_tourist) predicts "
         "revisit, beyond reviewer traits and sentiment.",
         size=14, color=DARK, space_before=10)
add_para(kf,
         "•  Revisit and rating are related but distinct traces of "
         "satisfaction (r = 0.08).",
         size=14, color=DARK, space_before=8)

# Limitations block
lm = add_textbox(slide, 0.6, 4.5, 12.1, 2.5)
add_para(lm, "Limitations / 한계",
         size=18, bold=True, color=HEAD, first=True)
add_para(lm, "", size=4, space_before=4)
add_para(lm,
         "•  Observational data; no causal identification.",
         size=14, color=DARK, space_before=10)
add_para(lm,
         "•  29 attractions in Seoul (25) and Busan (4); generalisation "
         "to other regions requires replication.",
         size=14, color=DARK, space_before=8)

print("  Slide 16 rewritten.")

# ── 2. Delete slide 17 (index 16: "Limitations and future work") ─────────
delete_slide_by_index(p, 16)
print("  Slide 17 (Limitations and future work) deleted.")

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"\nFinal slide count: {len(p.slides)}")
print(f"Saved to: {PPTX}")
