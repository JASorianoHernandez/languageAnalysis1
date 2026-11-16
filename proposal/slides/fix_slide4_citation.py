"""
fix_slide4_citation.py
Surgical fix only to Slide 4 of presentation_build.pptx:
  - Replace EN/KO sentence that mentions "Lee et al. (2026)" inline with a
    citation-free statement + [1] marker
  - Add a small text box at the bottom with the full Lee et al. reference,
    matching the "* Screenshot images from..." footnote pattern

Leaves everything else on slide 4 untouched: title, images, caption,
asterisk footnote, slide number. Does not touch other slides.

Run (base env):  python fix_slide4_citation.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches

PPTX = "presentation_build.pptx"
FONT_BODY = "Source Sans Pro Light"

NEW_EN = ("Information diversity in reviews predicts business performance [1], "
          "but who writes diverse reviews stays unobserved.")
NEW_KO = ("리뷰의 정보 다양성은 사업체 성과를 예측하나 [1], 작성자 측 요인은 "
          "관찰되지 않는다.")
REF_1 = ("[1] Lee, M., Jeong, D., & Kim, A. J. (2026). The impact of "
         "information diversity on online reviews and business performance. "
         "Journal of Consumer Studies, 37.")

p = Presentation(PPTX)
slide4 = p.slides[3]

# --- Replace EN and KO sentences in the body ------------------------------
body = next((s for s in slide4.shapes if s.name == "Content Placeholder 6"), None)
if body is None:
    raise RuntimeError("Content Placeholder 6 not found on slide 4")

tf = body.text_frame

def set_paragraph_text(para, text):
    para.text = text  # creates a single new run
    if para.runs:
        para.runs[0].font.name = FONT_BODY

# Paragraph indices from current state: 3 = EN sentence, 4 = KO sentence
set_paragraph_text(tf.paragraphs[3], NEW_EN)
set_paragraph_text(tf.paragraphs[4], NEW_KO)

# --- Add [1] footnote text box if not already present ---------------------
already = False
for shape in slide4.shapes:
    if shape.has_text_frame and shape.text_frame.text.startswith("[1] Lee, M., Jeong"):
        already = True
        break

if not already:
    tb = slide4.shapes.add_textbox(Inches(0.45), Inches(6.50), Inches(10.0), Inches(0.28))
    rtf = tb.text_frame
    rtf.word_wrap = True
    rtf.paragraphs[0].text = REF_1
    if rtf.paragraphs[0].runs:
        rtf.paragraphs[0].runs[0].font.name = FONT_BODY
        rtf.paragraphs[0].runs[0].font.size = Pt(10)
    print("  Added [1] footnote text box at (0.45, 6.50)")
else:
    print("  [1] footnote text box already present; skipped")

p.save(PPTX)
print(f"OK. Slide 4 of {PPTX} updated.")
