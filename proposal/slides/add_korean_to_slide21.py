"""
add_korean_to_slide21.py
Rebuild slide 21 adding Korean (glosa) under each RQ finding.
Only slide 21 is touched. All other slides are preserved.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

PPTX = "presentation_build.pptx"
SLIDE_IDX = 20
FONT_HEAD = "Source Sans"
FONT_BODY = "Source Sans Pro Light"
DARK   = RGBColor(0x22, 0x22, 0x22)
MUTED  = RGBColor(0x55, 0x55, 0x55)
ACCENT = RGBColor(0x40, 0x55, 0x70)


def _font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    if size is not None: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color is not None: run.font.color.rgb = color


p = Presentation(PPTX)
slide = p.slides[SLIDE_IDX]

# Scrub body (keep title + slide-number)
removed = 0
for shape in list(slide.shapes):
    try:
        pf = shape.placeholder_format
        if pf is not None and pf.idx in (0, 4):
            continue
    except Exception:
        pass
    shape._element.getparent().remove(shape._element)
    removed += 1
print(f"  Slide 21: removed {removed} old body shapes")

# Title (reassert)
title = slide.shapes.title
title.left = Inches(0.45); title.top = Inches(0.40)
title.width = Inches(11.5); title.height = Inches(0.95)
ttf = title.text_frame; ttf.clear()
p_en = ttf.paragraphs[0]
p_en.text = "Conclusions, Implications and Limitations"
p_en.alignment = PP_ALIGN.LEFT
for run in p_en.runs: _font(run, FONT_HEAD)
p_ko = ttf.add_paragraph()
p_ko.text = "결론, 시사점, 한계"
p_ko.alignment = PP_ALIGN.LEFT
for run in p_ko.runs: _font(run, FONT_HEAD, 20)


# ─── Left column: Findings by RQ (EN + KO) + Three contributions ──────────
left_tb = slide.shapes.add_textbox(Inches(0.45), Inches(1.50),
                                    Inches(6.30), Inches(5.20))
ltf = left_tb.text_frame
ltf.word_wrap = True


def _addL(text, size=10, bold=False, italic=False, color=None,
          space_before=0, idx=None):
    if idx == 0:
        para = ltf.paragraphs[0]
    else:
        para = ltf.add_paragraph()
    if space_before:
        para.space_before = Pt(space_before)
    para.text = text
    para.alignment = PP_ALIGN.LEFT
    for run in para.runs:
        _font(run, FONT_BODY, size, bold=bold, italic=italic,
              color=color if color else DARK)


_addL("Key findings by research question", bold=True, size=12, color=ACCENT, idx=0)
_addL("연구 질문별 주요 결과", italic=True, size=10, color=MUTED)
_addL("", size=4)

# RQ1
_addL("RQ1  Revisit — Queueing is the single strongest negative signal for "
      "return (OR 0.51) and the only one directly actionable for managers.",
      size=10, space_before=4)
_addL("재방문 — 대기 경험은 재방문의 가장 강한 부정 신호(OR 0.51)이며, "
      "운영자가 직접 조치 가능한 유일한 변수.",
      size=9, italic=True, color=MUTED, space_before=1)

# RQ2
_addL("RQ2  Keyword diversity — Driven by reviewer engagement with the "
      "platform (writing text ×4, visit info ×2.5), not by visit type.",
      size=10, space_before=5)
_addL("키워드 다양성 — 방문 유형이 아닌 작성자의 플랫폼 참여도가 핵심 "
      "(텍스트 ×4, 방문 정보 ×2.5).",
      size=9, italic=True, color=MUTED, space_before=1)

# RQ3
_addL("RQ3  Reactions — Higher sentiment reduces reactions (IRR 0.77); "
      "engagement is driven by follower count and text length. Effusive "
      "praise is not what readers respond to.",
      size=10, space_before=5)
_addL("반응 — 긍정 감성은 반응을 줄인다(IRR 0.77). 몰입은 팔로워 수와 "
      "텍스트 길이가 좌우; 과한 칭찬은 독자의 선택 기준이 아님.",
      size=9, italic=True, color=MUTED, space_before=1)

# RQ4
_addL("RQ4  Aspects — Different visitor groups mention different aspects "
      "(children drive 3; waited → crowding; reserved → service). But what "
      "a review talks about does not predict reactions once reviewer "
      "identity is controlled.",
      size=10, space_before=5)
_addL("측면 — 방문자별로 언급 측면이 다름(아이→역사·접근성·서비스, "
      "대기→혼잡, 예약→서비스). 그러나 작성자 특성 통제 후, 리뷰 내용은 "
      "반응을 예측하지 않음.",
      size=9, italic=True, color=MUTED, space_before=1)

# Contributions
_addL("Three contributions", bold=True, size=12, color=ACCENT, space_before=10)
_addL("세 가지 기여", italic=True, size=10, color=MUTED)
_addL("", size=4)
_addL("(i)   Review-level replication of the diversity–performance link "
      "Lee et al. establish at the business-week level.", size=10, space_before=2)
_addL("(ii)  Platform-structured visit context (companion · purpose · wait "
      "· reservation) as a joint predictor set.", size=10, space_before=3)
_addL("(iii) Aspect-level analysis cross-cut by visit context — a "
      "combination the reference studies cannot build.", size=10, space_before=3)


# ─── Right column: Implications + Limitations ────────────────────────────
right_tb = slide.shapes.add_textbox(Inches(7.00), Inches(1.50),
                                     Inches(6.00), Inches(5.20))
rtf = right_tb.text_frame
rtf.word_wrap = True


def _addR(text, size=10, bold=False, italic=False, color=None,
          space_before=0, idx=None):
    if idx == 0:
        para = rtf.paragraphs[0]
    else:
        para = rtf.add_paragraph()
    if space_before:
        para.space_before = Pt(space_before)
    para.text = text
    para.alignment = PP_ALIGN.LEFT
    for run in para.runs:
        _font(run, FONT_BODY, size, bold=bold, italic=italic,
              color=color if color else DARK)


_addR("Implications", bold=True, size=12, color=ACCENT, idx=0)
_addR("시사점", italic=True, size=10, color=MUTED)
_addR("", size=4)
_addR("For platforms — engagement is reviewer-identity driven. Reviewer "
      "retention and reviewer-experience investments likely outperform "
      "content-side nudges.",
      size=10, space_before=2)
_addR("플랫폼: 몰입은 작성자 정체성 중심이다. 작성자 유지와 경험 투자가 "
      "콘텐츠 유도보다 효과적일 가능성이 높다.",
      size=9, italic=True, color=MUTED, space_before=1)
_addR("For attraction managers — reduce wait times. Queueing is the only "
      "lever in this report that directly affects return odds.",
      size=10, space_before=5)
_addR("운영자: 대기 시간을 줄여라. 재방문에 직접적으로 영향을 미치는 "
      "유일한 레버다.",
      size=9, italic=True, color=MUTED, space_before=1)

_addR("Limitations and future work", bold=True, size=12, color=ACCENT, space_before=10)
_addR("한계 및 향후 과제", italic=True, size=10, color=MUTED)
_addR("", size=4)
_addR("Associations only. Design is cross-sectional; Lee et al. use a "
      "keyword-expansion event as a natural experiment, we do not.",
      size=10, space_before=2)
_addR("Model 1 predicts a visit that already happened — profiles returning "
      "visitors, does not explain why anyone returns.",
      size=10, space_before=3)
_addR("A single platform; Naver reviewers may differ systematically from "
      "Korean reviewers at large.",
      size=10, space_before=3)
_addR("Roadmap: place + time fixed effects · Hausman test · inductive "
      "validation of the six aspects.",
      size=10, italic=True, color=MUTED, space_before=4)


p.save(PPTX)
print(f"OK. Slide {SLIDE_IDX + 1} rebuilt with Korean glosas under each RQ.")
print(f"Total slides: {len(p.slides)} (unchanged).")
