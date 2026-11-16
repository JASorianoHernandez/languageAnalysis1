"""
fix_closing_slide.py
Repair the deck after build_methodology_split.py caused a duplicate-name
collision that overwrote the Closing (Thank you) slide:
  - Slide 20 is currently a duplicate of the Framework slide.
  - Delete slide 20 PROPERLY (drop_rel, not just _sldIdLst remove).
  - Append a fresh Closing (Thank you) slide using the Closing layout.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches

PPTX = "presentation_build.pptx"
FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"


def delete_slide_properly(prs, index):
    """Remove the slide at given index AND drop its underlying part."""
    slide_id_lst = prs.slides._sldIdLst
    sld_id = slide_id_lst[index]
    rId = sld_id.rId
    # Drop the relationship first (removes the part from the package)
    prs.part.drop_rel(rId)
    # Then remove the reference from the slide list
    slide_id_lst.remove(sld_id)


p = Presentation(PPTX)
total_before = len(p.slides)

# Delete slide 20 (0-indexed 19) which is the Framework duplicate
delete_slide_properly(p, 19)

# Build a fresh Closing slide using the Closing layout
layout = p.slide_masters[0].slide_layouts[12]  # Closing
slide = p.slides.add_slide(layout)

title_ph = slide.shapes.title
ttf = title_ph.text_frame
ttf.clear()
p_en = ttf.paragraphs[0]
p_en.text = "Thank you"
for run in p_en.runs:
    run.font.name = FONT_HEAD
p_ko = ttf.add_paragraph()
p_ko.text = "감사합니다"
for run in p_ko.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(24)

# Fill the content/contact box
body_lines = [
    ("Jorge Adan Soriano Hernandez", True),
    ("Department of Data Science, Hoseo University", True),
    ("호서대학교 데이터사이언스학과", False),
    ("", True),
    ("Full report, data and scripts available in the project repository.", True),
    ("전체 보고서, 데이터, 스크립트는 프로젝트 저장소에서 열람 가능.", False),
    ("", True),
    ("Questions and discussion / 질문 및 토론", True),
]

for shape in slide.shapes:
    if shape is title_ph:
        continue
    if shape.has_text_frame:
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == 10:
                tf = shape.text_frame
                tf.clear()
                for i, (text, is_en) in enumerate(body_lines):
                    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    para.text = text
                    for run in para.runs:
                        run.font.name = FONT_BODY
                        if not is_en and text.strip():
                            run.font.size = Pt(12)
                break
        except Exception:
            pass

p.save(PPTX)
print(f"Slides: {total_before} -> {len(p.slides)}")
print("  Slide 20: Thank you / 감사합니다 (Closing layout) — restored")
