"""
build_section1.py (v2)
Section 1 (Introduction) of the Naver Place proposal deck.
Modifies presentation_build.pptx only (never templateppt.pptx).

v2 changes based on manual feedback:
  - Cite Lee et al. (2026) inline as [1] and put full ref in a footnote text box
    (mirrors the existing "* Screenshot images from..." pattern)
  - Rebuild Slide 5 with the title at the TOP of the slide (same position as
    Slide 4) using Layout 3 "Title text and image"; remove its picture
    placeholder; widen content to full width; add slide-number text box
  - Explicit fonts: Source Sans (headings), Source Sans Pro Light (body)

Run (base env):  python build_section1.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from copy import deepcopy
from pptx import Presentation
from pptx.util import Pt, Inches, Emu

PPTX = "presentation_build.pptx"
FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"

p = Presentation(PPTX)

# ─── Slide 4: Introduction / Motivation ───────────────────────────────────
MOTIVATION = [
    ("Online reviews drive travel decisions.", True),
    ("온라인 리뷰는 여행 결정을 좌우한다.", False),
    ("", True),
    ("Information diversity in reviews predicts business performance [1], "
     "but who writes diverse reviews stays unobserved.", True),
    ("리뷰의 정보 다양성은 사업체 성과를 예측하나 [1], 작성자 측 요인은 "
     "관찰되지 않는다.", False),
    ("", True),
    ("This study takes the construct to the individual review, combined "
     "with Naver's structured visit context: companion, purpose, wait, "
     "reservation.", True),
    ("본 연구는 이 개념을 개별 리뷰 수준으로 확장하고, 네이버의 구조화된 "
     "방문 맥락(동반자, 목적, 대기, 예약)과 결합한다.", False),
]
REF_1 = ("[1] Lee, M., Jeong, D., & Kim, A. J. (2026). The impact of "
         "information diversity on online reviews and business performance. "
         "Journal of Consumer Studies, 37.")

slide4 = p.slides[3]
body_shape = next((s for s in slide4.shapes if s.name == "Content Placeholder 6"), None)
if body_shape is None:
    raise RuntimeError("Content Placeholder 6 not found on slide 4")

tf = body_shape.text_frame
tf.clear()
for i, (text, is_en) in enumerate(MOTIVATION):
    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    para.text = text
    for run in para.runs:
        run.font.name = FONT_BODY  # Source Sans Pro Light

# Add [1] footnote text box, same style as the "* Screenshot ..." line
# Existing: "* Screenshot" at (0.45, 6.80) size 7.65x0.30
# Place [1] above it at (0.45, 6.50) size 10.0x0.28
from pptx.util import Inches as _In
tb = slide4.shapes.add_textbox(_In(0.45), _In(6.50), _In(10.0), _In(0.28))
# Remove duplicate footnote if we are re-running the script
# (identify by starting with "[1] Lee, M., Jeong")
for existing in list(slide4.shapes):
    if existing is tb:
        continue
    if existing.has_text_frame and existing.text_frame.text.startswith("[1] Lee, M., Jeong"):
        sp = existing._element
        sp.getparent().remove(sp)
rtf = tb.text_frame
rtf.word_wrap = True
rtf.paragraphs[0].text = REF_1
for run in rtf.paragraphs[0].runs:
    run.font.name = FONT_BODY
    run.font.size = Pt(10)

# ─── Delete the current Slide 5 (RQs built incorrectly) ───────────────────
xml_slides = p.slides._sldIdLst
slides_list = list(xml_slides)
if len(slides_list) >= 5:
    xml_slides.remove(slides_list[4])  # 0-index 4 = slide 5

# ─── Build NEW Slide 5 with title at TOP (match Slide 4 pattern) ──────────
RQS = [
    ("1. Which visit contexts predict returning to the same attraction?",
     "   어떤 방문 맥락이 재방문과 연관되는가?"),
    ("2. Which reviewers and visit contexts produce more diverse keywords?",
     "   어떤 작성자와 방문 맥락이 더 많은 키워드를 생성하는가?"),
    ("3. Which reviews receive reactions? Does sentiment help?",
     "   어떤 리뷰가 반응을 받는가? 감성은 도움이 되는가?"),
    ("4. Which aspects do reviewer groups discuss, and does content "
     "predict engagement beyond sentiment?",
     "   어떤 방문 측면을 작성자 그룹이 언급하며, 내용이 감성 이상의 "
     "몰입을 예측하는가?"),
]

layout = p.slide_masters[0].slide_layouts[3]  # "Title text and image"
new_slide = p.slides.add_slide(layout)

# Remove the Picture placeholder from the new slide (we don't use it)
for shape in list(new_slide.shapes):
    if shape.has_text_frame:
        continue
    try:
        if shape.placeholder_format is not None and shape.placeholder_format.idx == 10:
            sp = shape._element
            sp.getparent().remove(sp)
    except Exception:
        pass

# Reposition the title to match Slide 4 top-of-slide position
title_shape = new_slide.shapes.title
title_shape.left = _In(0.45)
title_shape.top = _In(0.40)
title_shape.width = _In(6.89)
title_shape.height = _In(0.95)
title_tf = title_shape.text_frame
title_tf.clear()
p_en = title_tf.paragraphs[0]
p_en.text = "Research Questions"
for run in p_en.runs:
    run.font.name = FONT_HEAD
p_ko = title_tf.add_paragraph()
p_ko.text = "연구 질문"
for run in p_ko.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(20)

# Reposition and widen the content placeholder: below title, full page width
content_shape = None
for shape in new_slide.shapes:
    if shape is title_shape:
        continue
    if shape.has_text_frame:
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == 11:
                content_shape = shape
                break
        except Exception:
            pass

if content_shape is None:
    # Fallback: add a text box
    content_shape = new_slide.shapes.add_textbox(_In(0.45), _In(1.50), _In(12.4), _In(5.0))
else:
    content_shape.left = _In(0.45)
    content_shape.top = _In(1.50)
    content_shape.width = _In(12.4)
    content_shape.height = _In(5.0)

ctf = content_shape.text_frame
ctf.word_wrap = True
ctf.clear()
first = True
for i, (en, ko) in enumerate(RQS):
    pe = ctf.paragraphs[0] if first else ctf.add_paragraph()
    first = False
    pe.text = en
    for run in pe.runs:
        run.font.name = FONT_BODY
    pk = ctf.add_paragraph()
    pk.text = ko
    for run in pk.runs:
        run.font.name = FONT_BODY
        run.font.size = Pt(12)
    if i < len(RQS) - 1:
        ctf.add_paragraph().text = ""

# Add slide-number text box at the standard position (match other slides)
sn = new_slide.shapes.add_textbox(_In(9.33), _In(6.69), _In(3.0), _In(0.40))
sn.text_frame.paragraphs[0].text = "5"
for run in sn.text_frame.paragraphs[0].runs:
    run.font.name = FONT_BODY
    run.font.size = Pt(11)

# Move the new slide (currently at end) to position 5 (index 4)
xml_slides = p.slides._sldIdLst
slides_list = list(xml_slides)
new_elem = slides_list[-1]
xml_slides.remove(new_elem)
xml_slides.insert(4, new_elem)

p.save(PPTX)
print(f"OK. Updated {PPTX}:")
print("  - Slide 4: body text replaced with [1] inline + Lee et al. footnote added")
print("  - Slide 5 (RQs): rebuilt with title at TOP, full-width content, Source Sans Pro Light")
print(f"\nTotal slides now: {len(p.slides)}")
