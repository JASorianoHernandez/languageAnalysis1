"""
build_sections_4_5.py
Sections 4 (Results) and 5 (Conclusion) of the Naver Place proposal deck.
Modifies presentation_build.pptx only (never templateppt.pptx).

Adds the following slides at the end of the current deck (appended; order
preserved automatically because we build right after the existing slide 12):
  Slide 13 — Section Title "4. Results / 결과"
  Slide 14 — Main findings M1-M4
  Slide 15 — Aspect-level findings (6 aspects)
  Slide 16 — Section Title "5. Conclusion / 결론"
  Slide 17 — Implications + Limitations
  Slide 18 — Thanks / Q&A (uses the Closing layout)

Conventions: Source Sans / Source Sans Pro Light; title at top like Slide 4;
remove picture placeholder on content slides; add slide-number text box.

Run (base env):  python build_sections_4_5.py
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


def add_section_title(prs, en, ko, number):
    layout = prs.slide_masters[0].slide_layouts[2]  # Section Title 1
    slide = prs.slides.add_slide(layout)
    title_ph = slide.shapes.title
    tf = title_ph.text_frame
    tf.clear()
    p_en = tf.paragraphs[0]
    p_en.text = f"{number}. {en}"
    for run in p_en.runs:
        run.font.name = FONT_HEAD
    p_ko = tf.add_paragraph()
    p_ko.text = f"{number}. {ko}"
    for run in p_ko.runs:
        run.font.name = FONT_HEAD
        run.font.size = Pt(28)
    return slide


def add_content_slide(prs, title_en, title_ko, body_items):
    layout = prs.slide_masters[0].slide_layouts[3]  # Title text and image
    slide = prs.slides.add_slide(layout)
    # Remove picture placeholder
    for shape in list(slide.shapes):
        if shape.has_text_frame:
            continue
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == 10:
                sp = shape._element
                sp.getparent().remove(sp)
        except Exception:
            pass
    # Title at top-left
    title = slide.shapes.title
    title.left = Inches(0.45)
    title.top = Inches(0.40)
    title.width = Inches(11.5)
    title.height = Inches(0.95)
    ttf = title.text_frame
    ttf.clear()
    p_en = ttf.paragraphs[0]
    p_en.text = title_en
    for run in p_en.runs:
        run.font.name = FONT_HEAD
    p_ko = ttf.add_paragraph()
    p_ko.text = title_ko
    for run in p_ko.runs:
        run.font.name = FONT_HEAD
        run.font.size = Pt(20)
    # Content body (full width below title)
    body = None
    for shape in slide.shapes:
        if shape is title:
            continue
        if shape.has_text_frame:
            try:
                if shape.placeholder_format is not None and shape.placeholder_format.idx == 11:
                    body = shape
                    break
            except Exception:
                pass
    if body is None:
        body = slide.shapes.add_textbox(Inches(0.45), Inches(1.60), Inches(12.4), Inches(5.0))
    else:
        body.left = Inches(0.45)
        body.top = Inches(1.60)
        body.width = Inches(12.4)
        body.height = Inches(5.0)
    btf = body.text_frame
    btf.word_wrap = True
    btf.clear()
    for i, (text, is_en) in enumerate(body_items):
        para = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
        para.text = text
        for run in para.runs:
            run.font.name = FONT_BODY
            if not is_en and text.strip():
                run.font.size = Pt(12)
    # Slide number box
    sn = slide.shapes.add_textbox(Inches(9.33), Inches(6.69), Inches(3.0), Inches(0.40))
    sn.text_frame.paragraphs[0].text = ""
    return slide


def add_closing_slide(prs, title_en, title_ko, body_items):
    layout = prs.slide_masters[0].slide_layouts[12]  # Closing
    slide = prs.slides.add_slide(layout)
    # Fill title
    title_ph = slide.shapes.title
    ttf = title_ph.text_frame
    ttf.clear()
    p_en = ttf.paragraphs[0]
    p_en.text = title_en
    for run in p_en.runs:
        run.font.name = FONT_HEAD
    p_ko = ttf.add_paragraph()
    p_ko.text = title_ko
    for run in p_ko.runs:
        run.font.name = FONT_HEAD
        run.font.size = Pt(24)
    # Fill content (contact / message area)
    for shape in slide.shapes:
        if shape is title_ph:
            continue
        if shape.has_text_frame:
            try:
                if shape.placeholder_format is not None and shape.placeholder_format.idx == 10:
                    tf = shape.text_frame
                    tf.clear()
                    for i, (text, is_en) in enumerate(body_items):
                        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                        para.text = text
                        for run in para.runs:
                            run.font.name = FONT_BODY
                            if not is_en and text.strip():
                                run.font.size = Pt(12)
                    break
            except Exception:
                pass
    return slide


# ─── Content ──────────────────────────────────────────────────────────────

SLIDE14_TITLE = ("Main findings (M1–M4)", "주요 결과 (M1–M4)")
SLIDE14_BODY = [
    ("M1 Revisit  (logistic, AUC = 0.773)", True),
    ("  Reviewer history       OR = 1.52 ***    Visited alone     OR = 1.68 **", True),
    ("  Waited to enter        OR = 0.51 ***    Travel group      OR = 0.56 ***", True),
    ("  작성자 리뷰 이력과 혼자 방문은 재방문을 높인다; 대기와 여행 목적은 낮춘다.", False),
    ("", True),
    ("M2 Keyword Count  (ordered logistic, RMSE 1.37 vs 1.88 base)", True),
    ("  Wrote text             OR = 4.02 ***    Visit info given  OR = 2.53 ***", True),
    ("  Revisitor              OR = 1.60 ***    Purpose: outing   OR = 1.85 ***", True),
    ("  텍스트 작성 및 방문 정보 제공이 키워드 수를 크게 늘린다.", False),
    ("", True),
    ("M3 Rating  (exploratory – ratings move little, 73.9\\% five-star)", True),
    ("  Keyword count          OR = 1.56 ***    Revisitor         OR = 1.37 *", True),
    ("  별점은 변동이 작아 탐색적으로만 보고; 키워드 수가 가장 강한 예측 변수.", False),
    ("", True),
    ("M4 Reactions  (negative binomial, AUC any-reaction 0.815)", True),
    ("  ln(followers)          IRR = 1.97 ***   ln(text length)   IRR = 1.64 ***", True),
    ("  Sentiment (−1 to +1)   IRR = 0.77 **     Visit: autumn     IRR = 0.71 ***", True),
    ("  팔로워 수와 텍스트 길이가 반응을 늘리고, 긍정 감성과 가을 방문은 줄인다.", False),
]

SLIDE15_TITLE = ("Aspect-level analysis (6 aspects, N = 11,164)",
                 "측면 수준 분석 (6개 측면, N = 11,164)")
SLIDE15_BODY = [
    ("ABSA labels on six dimensions (LLM, 06_llm_analysis.py): historical/cultural "
     "(50.4\\%), visual (63.8\\%), service/experience (27.4\\%), accessibility "
     "(19.8\\%), crowding (16.3\\%), food (6.9\\%).", True),
    ("LLM 기반 분류기로 여섯 가지 측면 라벨링: 역사·문화 50.4\\%, 시각 63.8\\%, "
     "서비스·체험 27.4\\%, 접근성 19.8\\%, 혼잡 16.3\\%, 음식 6.9\\%.", False),
    ("", True),
    ("Six aspects were specified a priori and validated post-hoc against unsupervised "
     "topic extraction (LDA at optimal K = 6, BERTopic K = 15). All six except crowding "
     "emerge as distinct topics; crowding is retained as polarity-dominated (18.1\\% "
     "of mentions are negative, the highest).", True),
    ("여섯 측면은 사전 지정되었고, 비지도 토픽 추출(LDA 최적 K = 6, BERTopic K = 15)로 "
     "사후 검증되었다. 혼잡 외 다섯 측면은 뚜렷한 토픽으로 나타난다. 혼잡은 극성 중심의 "
     "차원이므로 유지한다.", False),
    ("", True),
    ("Four findings from the \"who mentions what\" regressions (ABSA-A):", True),
    ("  (1) Children drive narrative-rich reviews across historical, accessibility, "
     "and service/experience aspects (ORs 1.22–1.55).", True),
    ("  (2) Service friction splits two ways: waited  →  crowding (OR 2.13 ***); "
     "reserved  →  crowding ↓ 0.69 ** but service/experience  ↑ 2.39 ***.", True),
    ("  (3) Date-purpose visits raise food mentions by 51\\% (OR 1.51 *); alone "
     "visits lower them (OR 0.64 *).", True),
    ("  (4) Service/experience is empirically distinct from historical/cultural "
     "(pseudo-R² = 0.371, structurally different predictors).", True),
    ("  (1) 아이와 방문: 역사·접근성·서비스 측면에서 더 다양한 언급. "
     "(2) 대기 → 혼잡 ↑, 예약 → 서비스 ↑ 혼잡 ↓. "
     "(3) 데이트 → 음식 ↑, 혼자 → 음식 ↓. "
     "(4) 서비스·체험은 역사·문화와 구별되는 독립 차원.", False),
    ("", True),
    ("Reactions by aspect content (ABSA-B): no aspect dummy reaches p < .05 after "
     "controls. Engagement in this platform is driven by reviewer identity "
     "(follower count, revisitor status, text length), not by what the review "
     "specifically discusses.", True),
    ("아스펙트 내용에 따른 반응: 어떠한 측면 더미도 통제 후 p < .05에 도달하지 않는다. "
     "본 플랫폼의 몰입은 리뷰 \\emph{내용}이 아닌 \\emph{작성자 특성}(팔로워·재방문·길이)에 "
     "의해 좌우된다.", False),
]

SLIDE17_TITLE = ("Implications and Limitations", "시사점과 한계")
SLIDE17_BODY = [
    ("Implications / 시사점", True),
    ("  For platforms: engagement is reviewer-identity-driven. Promoting reviewer "
     "retention and reviewer experience may matter more than nudging keyword choice.", True),
    ("  For attraction managers: queueing is the single strongest negative signal for "
     "return, and the only one in this report that is directly actionable.", True),
    ("  플랫폼 입장: 몰입은 작성자 정체성에 의해 좌우된다. 작성자 유지와 경험을 늘리는 "
     "것이 키워드 선택을 유도하는 것보다 중요할 수 있다. "
     "운영자 입장: 대기 시간이 재방문의 가장 강한 부정 신호다.", False),
    ("", True),
    ("Limitations and future work / 한계 및 향후 과제", True),
    ("  Associations only — the design is cross-sectional, not causal. Lee et al. "
     "(2026) use a keyword-expansion event; we do not have an equivalent lag.", True),
    ("  Model 1 predicts a visit that already occurred — it profiles returning "
     "visitors rather than explaining why anyone returns.", True),
    ("  A single platform; Naver reviewers may differ from Korean reviewers at large. "
     "Place and time fixed effects + Hausman test are the next addition.", True),
    ("  연관성만 다룸; 횡단면 설계이며 인과적이지 않다. 모형 1은 이미 일어난 방문을 "
     "예측하므로 재방문자를 특성화할 뿐 재방문 원인을 설명하지는 않는다. 단일 플랫폼이며, "
     "시간 고정효과와 Hausman 검정이 다음 과제.", False),
]

SLIDE18_TITLE = ("Thank you", "감사합니다")
SLIDE18_BODY = [
    ("Jorge Adan Soriano Hernandez", True),
    ("Department of Data Science, Hoseo University", True),
    ("호서대학교 데이터사이언스학과", False),
    ("", True),
    ("Full report, data and scripts are available in the project repository.", True),
    ("전체 보고서, 데이터, 스크립트는 프로젝트 저장소에서 열람 가능.", False),
    ("", True),
    ("Questions and discussion / 질문 및 토론", True),
]


# ─── Apply ────────────────────────────────────────────────────────────────
p = Presentation(PPTX)
before = len(p.slides)
print(f"Slides before: {before}")

add_section_title(p, "Results", "결과", 4)             # Slide 13
add_content_slide(p, *SLIDE14_TITLE, SLIDE14_BODY)      # Slide 14 — M1-M4 findings
add_content_slide(p, *SLIDE15_TITLE, SLIDE15_BODY)      # Slide 15 — ABSA findings
add_section_title(p, "Conclusion and Implications",
                  "결론 및 시사점", 5)                   # Slide 16
add_content_slide(p, *SLIDE17_TITLE, SLIDE17_BODY)      # Slide 17 — Implications + Limitations
add_closing_slide(p, *SLIDE18_TITLE, SLIDE18_BODY)      # Slide 18 — Thanks / Q&A

p.save(PPTX)
print(f"Slides after:  {len(p.slides)} (added {len(p.slides)-before})")
print("  Slide 13: Section Title '4. Results / 결과'")
print("  Slide 14: Main findings M1–M4")
print("  Slide 15: Aspect-level analysis (6 aspects)")
print("  Slide 16: Section Title '5. Conclusion / 결론'")
print("  Slide 17: Implications and Limitations")
print("  Slide 18: Thank you / Q&A")
