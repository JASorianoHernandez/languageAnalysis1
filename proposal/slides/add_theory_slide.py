"""
add_theory_slide.py
Insert a Theoretical Background content slide between the current
section-2 divider and the section-3 divider. Uses only references we
actually have in our bibliography: Lee 2026, Parasuraman 1988 (SERVQUAL),
Karabila 2024. Full paper titles listed at footer for traceability.
Applies the user's standard formats (reference_pptx_formats memory).
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from lxml import etree

PPTX = "presentation_v2.pptx"

FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
DARK   = RGBColor(0x22, 0x22, 0x22)
MUTED  = RGBColor(0x55, 0x55, 0x55)
HEAD   = RGBColor(0x23, 0x31, 0x2D)   # dark forest green (user preference)


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


def move_slide(p, old_index, new_index):
    """Move a slide from old_index to new_index (both 0-based)."""
    sldIdLst = p.slides._sldIdLst
    slides = list(sldIdLst)
    sldIdLst.remove(slides[old_index])
    sldIdLst.insert(new_index, slides[old_index])


# ─── Load ───────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
print(f"Loaded. Current slide count: {len(p.slides)}")

# Current layout:
#   index 5 (slide 6)  — Section Title "2. Theoretical Background"
#   index 6 (slide 7)  — Section Title "3. Methodology"
# We want to insert a new content slide between them (new index 6).

# Find the "Title and Content" layout
L_CONTENT = None
for layout in p.slide_layouts:
    if layout.name == "Title and Content":
        L_CONTENT = layout
        break
assert L_CONTENT is not None, "Title and Content layout not found."

# Add new slide (goes to end of deck first)
new_slide = p.slides.add_slide(L_CONTENT)
new_index = len(p.slides) - 1
target_index = 6  # between slide 6 (section divider) and slide 7

# Move the new slide into position
move_slide(p, new_index, target_index)
print(f"Inserted new slide at position {target_index + 1} (1-based).")

# Clear and populate
slide = p.slides[target_index]
strip_body_shapes(slide, keep_names=("Title",))

# Title
set_title(slide, "Theoretical Background / 이론적 배경")

# Three anchors, stacked vertically with bilingual content
# Anchor 1 — Information diversity (Lee)
a1 = add_textbox(slide, 0.5, 1.3, 12.3, 1.65)
add_para(a1, "1.  Information diversity in reviews drives performance",
         size=16, bold=True, color=HEAD, first=True, name=FONT_BODY)
add_para(a1, "리뷰의 정보 다양성이 성과를 좌우한다",
         size=13, italic=True, color=MUTED, space_before=2)
add_para(a1, "Business-week evidence that review diversity predicts "
             "platform performance (Lee et al., 2026). Our contribution: "
             "take the construct to the individual review.",
         size=12, color=DARK, space_before=6)
add_para(a1, "리뷰 다양성이 플랫폼 성과를 예측 (이민영 외, 2026). "
             "본 연구의 기여: 개별 리뷰 수준으로 확장.",
         size=11, italic=True, color=MUTED, space_before=3)

# Anchor 2 — SERVQUAL
a2 = add_textbox(slide, 0.5, 3.1, 12.3, 1.65)
add_para(a2, "2.  Service quality: waiting as responsiveness failure",
         size=16, bold=True, color=HEAD, first=True, name=FONT_BODY)
add_para(a2, "서비스 품질: 반응성 실패로서의 대기",
         size=13, italic=True, color=MUTED, space_before=2)
add_para(a2, "SERVQUAL identifies responsiveness as one of five service-"
             "quality dimensions (Parasuraman et al., 1988). Entrance "
             "waiting is a direct responsiveness failure.",
         size=12, color=DARK, space_before=6)
add_para(a2, "SERVQUAL은 반응성을 서비스 품질 5개 차원 중 하나로 식별 "
             "(Parasuraman 외, 1988). 입구 대기는 반응성의 직접적 위반.",
         size=11, italic=True, color=MUTED, space_before=3)

# Anchor 3 — Sentiment classification
a3 = add_textbox(slide, 0.5, 4.9, 12.3, 1.65)
add_para(a3, "3.  Sentiment classification for Korean review text",
         size=16, bold=True, color=HEAD, first=True, name=FONT_BODY)
add_para(a3, "한국어 리뷰 텍스트에 대한 감성 분류",
         size=13, italic=True, color=MUTED, space_before=2)
add_para(a3, "BERT-based sentiment models substantially outperform earlier "
             "approaches, reaching 91% accuracy in review contexts "
             "(Karabila et al., 2024). We use KLUE-BERT for Korean text.",
         size=12, color=DARK, space_before=6)
add_para(a3, "BERT 기반 감성 모델은 기존 방식 대비 크게 우수한 성능 "
             "(Karabila 외, 2024). 한국어 텍스트에는 KLUE-BERT를 사용.",
         size=11, italic=True, color=MUTED, space_before=3)

# Footer — full paper titles for traceability
foot = add_textbox(slide, 0.5, 6.75, 12.3, 0.6)
add_para(foot, "References / 참고문헌",
         size=9, bold=True, color=MUTED, first=True)
add_para(foot,
         "[1] Lee, Jeong & Kim (2026). The Impact of Information Diversity on Online Reviews and Business Performance. "
         "J. of Consumer Studies 37(1).",
         size=8, color=MUTED, space_before=1)
add_para(foot,
         "[2] Parasuraman, Zeithaml & Berry (1988). SERVQUAL: A Multiple-Item Scale for Measuring Consumer Perceptions "
         "of Service Quality. J. of Retailing 64(1), 12–40.",
         size=8, color=MUTED, space_before=1)
add_para(foot,
         "[3] Karabila, Darraz, EL-Ansari, Alami & EL Mallahi (2024). BERT-enhanced sentiment analysis for personalized "
         "e-commerce recommendations. Multimedia Tools and Applications 83, 56463–56488.",
         size=8, color=MUTED, space_before=1)

# ─── Save ──────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"Final slide count: {len(p.slides)}")
print(f"Saved to: {PPTX}")
