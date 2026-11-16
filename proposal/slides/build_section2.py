"""
build_section2.py
Section 2 (Theoretical Background) of the Naver Place proposal deck.
Modifies presentation_build.pptx only (never templateppt.pptx).

Updates slides 7, 8, 9 bodies (keeps title, images, existing [1]/[2] footnote
text boxes, slide number). Slide 6 (section title) is untouched.

Conventions applied:
  - Direct statements, no "Author (year) states..." inline
  - Citations as [n] inline; full references already live in template footnote
    text boxes on slides 7 (Lee et al.) and 8 (Wang et al.)
  - Source Sans Pro Light for body
  - Slide 9 body expanded vertically (no image, has room for gap + contributions)

Run (base env):  python build_section2.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches

PPTX = "presentation_build.pptx"
FONT_BODY = "Source Sans Pro Light"

# ─── Content ──────────────────────────────────────────────────────────────
SLIDE7 = [  # (text, is_english). Blank text -> empty line.
    ("Information diversity measures how many distinct keywords a review "
     "carries, independent of its length or sentiment.", True),
    ("정보 다양성은 리뷰 길이나 감성과 무관하게 리뷰가 담은 서로 다른 키워드 "
     "수를 측정한다.", False),
    ("", True),
    ("Higher diversity predicts business performance separately from review "
     "volume [1].", True),
    ("리뷰 양과 독립적으로 사업체 성과를 예측한다 [1].", False),
]

SLIDE8 = [
    ("Review helpfulness captures how useful other viewers find a review.", True),
    ("리뷰 유용성은 다른 이용자가 리뷰를 얼마나 유용하게 느끼는지를 포착한다.", False),
    ("", True),
    ("Prior work operationalizes it through content dissimilarity in text [2]; "
     "this study uses reader reactions as a behavioural proxy.", True),
    ("선행 연구는 이를 텍스트 내용의 비유사성으로 조작화하며 [2], 본 연구는 "
     "이용자 반응을 행동적 대리 지표로 사용한다.", False),
]

SLIDE9 = [
    ("Research gap", True),
    ("연구 공백", False),
    ("Prior work observes performance at the aggregate level, but what each "
     "review discusses and the visit context behind it stay unobserved.", True),
    ("선행 연구는 집계 수준에서 성과를 관찰하지만, 각 리뷰가 다루는 내용과 "
     "그 방문 맥락은 관찰되지 않는다.", False),
    ("", True),
    ("This study contributes", True),
    ("본 연구의 기여", False),
    ("(i)   Review-level replication of the diversity–performance link.", True),
    ("        다양성–성과 관계의 리뷰 수준 재현.", False),
    ("(ii)  Platform-structured visit context (companion, purpose, wait, "
     "reservation) as a joint predictor set.", True),
    ("        플랫폼 구조화된 방문 맥락(동반자·목적·대기·예약)의 통합 예측 "
     "변수 세트.", False),
    ("(iii) Aspect-level analysis of what reviews discuss, cross-cut by "
     "visit context.", True),
    ("        리뷰 내용의 측면별 분석, 방문 맥락과 교차.", False),
]

# ─── Helpers ──────────────────────────────────────────────────────────────
def find_body(slide):
    """Return the primary Content Placeholder 6 (body text, upper position),
    not the one near the bottom (which holds [1]/[2] reference footnote)."""
    candidates = [s for s in slide.shapes
                  if s.has_text_frame and s.name == "Content Placeholder 6"]
    # Body is the one with the smaller top (higher on slide)
    if not candidates:
        return None
    return min(candidates, key=lambda s: s.top)

def set_body_text(shape, paragraphs):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.clear()
    for i, (text, is_en) in enumerate(paragraphs):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.text = text
        for run in para.runs:
            run.font.name = FONT_BODY
            if not is_en and text.strip():
                run.font.size = Pt(12)  # KO glosa smaller

# ─── Apply ────────────────────────────────────────────────────────────────
p = Presentation(PPTX)

# Slide 7 (index 6)
body7 = find_body(p.slides[6])
if body7 is None:
    raise RuntimeError("Body placeholder not found on slide 7")
set_body_text(body7, SLIDE7)

# Slide 8 (index 7)
body8 = find_body(p.slides[7])
if body8 is None:
    raise RuntimeError("Body placeholder not found on slide 8")
set_body_text(body8, SLIDE8)

# Slide 9 (index 8) — expand body vertically (no image competes)
body9 = find_body(p.slides[8])
if body9 is None:
    raise RuntimeError("Body placeholder not found on slide 9")
body9.top = Inches(1.85)
body9.height = Inches(4.5)  # extend down (was ~2.08)
set_body_text(body9, SLIDE9)

p.save(PPTX)
print(f"OK. Section 2 applied to {PPTX}:")
print("  - Slide 7 (Information Diversity): body text + KO glosa")
print("  - Slide 8 (Review Helpfulness): body text + KO glosa")
print("  - Slide 9 (Research Gap + 3 Contributions): body expanded + KO glosa")
