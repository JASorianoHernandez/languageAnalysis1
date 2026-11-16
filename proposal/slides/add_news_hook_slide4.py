"""
add_news_hook_slide4.py

Slide 4 (Introduction) update:
  - Delete the 3 placeholder pictures on the right.
  - Compress the existing intro textboxes (keep text verbatim; just shorten
    their vertical extent).
  - Add a bilingual news-hook block below the intro referencing the Incheon
    43-visit case (JTBC 사건반장 report, 2026-07-27).
  - Right half (5.9-12.6 inches wide, 0.8-6.8 tall) left EMPTY for the user
    to drop images of the news afterwards.
  - Footer "[Lee et al., 2026]" is preserved.

No em-dashes. Korean numbers written phonetically.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE_TYPE

PPTX = "presentation_v2.pptx"

FONT_BODY = "Source Sans Pro Light"
DARK  = RGBColor(0x22, 0x22, 0x22)
MUTED = RGBColor(0x55, 0x55, 0x55)
HEAD  = RGBColor(0x23, 0x31, 0x2D)
ACCENT = RGBColor(0x8B, 0x1A, 0x1A)   # muted dark red for the paradox header


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
slide = p.slides[3]
print(f"Slide 4 shapes before: {len(slide.shapes)}")

# ── Delete the three pictures ──────────────────────────────────────────────
pictures = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
print(f"Pictures to delete: {len(pictures)}")
for pic in pictures:
    pic._element.getparent().remove(pic._element)

# ── Compress the intro textboxes (keep text; just move/resize) ─────────────
en_intro = next(s for s in slide.shapes if s.name == "TextBox 11")
ko_intro = next(s for s in slide.shapes if s.name == "TextBox 12")
en_intro.top = Inches(1.40)
en_intro.height = Inches(2.70)
ko_intro.top = Inches(1.40)
ko_intro.height = Inches(2.70)

# ── News hook: bilingual, left half only, stacked EN then KO ───────────────
# Left half: 0.40 to 5.73 wide. Vertical area: 4.20 to 6.80.
hook_en = slide.shapes.add_textbox(
    Inches(0.40), Inches(4.20), Inches(5.33), Inches(1.30))
tf = hook_en.text_frame
tf.word_wrap = True
add_para(tf, "A real-world paradox",
         size=14, bold=True, color=ACCENT, first=True)
add_para(tf,
         "Incheon, 2026: one reviewer visited a restaurant 43 times. "
         "Every review text praised the staff ('good, friendly'). "
         "Every rating was 1 star. The rating fell to 2.9. "
         "The owner closed the shop.",
         size=10, color=DARK, space_before=4)
add_para(tf,
         "Our data: r(rating, revisit) = 0.08.",
         size=10, italic=True, color=MUTED, space_before=4)

hook_ko = slide.shapes.add_textbox(
    Inches(0.40), Inches(5.60), Inches(5.33), Inches(1.30))
tf = hook_ko.text_frame
tf.word_wrap = True
add_para(tf, "현실의 역설",
         size=13, bold=True, color=ACCENT, first=True)
add_para(tf,
         "2026년 인천: 한 리뷰어가 어느 횟집을 43번 방문. 매번 리뷰 "
         "텍스트는 '굿, 친절해요'. 매번 별점은 1점. 평점은 2.9까지 하락. "
         "사장님 폐업.",
         size=10, color=DARK, space_before=4)
add_para(tf,
         "저희 데이터: r(별점, 재방문) = 0.08.",
         size=10, italic=True, color=MUTED, space_before=4)

print(f"Slide 4 shapes after:  {len(slide.shapes)}")
print("  Deleted 3 pictures.")
print("  Compressed intro textboxes (text unchanged).")
print("  Added bilingual news-hook EN + KO (left half, stacked).")
print("  Right half (5.90-12.60 x 0.80-6.80) is empty for user images.")

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"\nSaved to: {PPTX}")
