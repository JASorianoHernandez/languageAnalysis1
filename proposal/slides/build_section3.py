"""
build_section3.py
Section 3 (Methodology) of the Naver Place proposal deck.
Modifies presentation_build.pptx only (never templateppt.pptx).

Adds two new slides after Slide 10 (section title "3. Methodology"):
  - Slide 11: Data overview
  - Slide 12: Variables + Models (visit context, 4 DVs, 4 link functions)

Both slides mirror Slide 4's convention: title at top (0.45, 0.40), content
body spanning full width underneath. Source Sans / Source Sans Pro Light.

Run (base env):  python build_section3.py
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


SLIDE11_TITLE = ("Data", "데이터")
SLIDE11_BODY = [
    ("29 Korean tourist attractions · 14,401 reviews · 11,165 with text · 8,276 reviewers.", True),
    ("한국 관광지 29곳 · 리뷰 14,401건 · 텍스트 포함 11,165건 · 작성자 8,276명.", False),
    ("", True),
    ("Attractions selected by crossing Yanolja Research's \"Korea's Top 500\" "
     "ranking with Korea Tourism Organization visitor volume, inside "
     "typological strata (palaces, hanok villages, markets, parks, museums, "
     "modern landmarks).", True),
    ("관광지는 야놀자 리서치 「대한민국 Top 500」과 한국관광공사 방문자 "
     "지표를 교차하여, 유형별 층위(궁궐·한옥마을·시장·공원·박물관·현대 "
     "랜드마크)에서 선정.", False),
    ("", True),
    ("Cities: Seoul (25) and Busan (4). The unit of analysis is a review i at "
     "place j, not the business-week.", True),
    ("도시: 서울 25곳, 부산 4곳. 분석 단위는 관광지 j의 리뷰 i이며, "
     "사업체-주 단위가 아니다.", False),
]


SLIDE12_TITLE = ("Variables and Models", "변수와 모형")
SLIDE12_BODY = [
    ("Visit context = four Naver-reported dimensions:  companion · purpose · "
     "wait experience · advance reservation.", True),
    ("방문 맥락 = 네이버가 수집하는 네 가지 차원: 동반자 · 방문 목적 · 대기 "
     "경험 · 사전 예약.", False),
    ("", True),
    ("Four outcomes, four models (link function matches the measurement scale):", True),
    ("네 가지 종속변수, 네 가지 모형 (연결함수는 측정 척도에 따라 선택):", False),
    ("", True),
    ("M1  Revisit (binary)                 →  logistic regression", True),
    ("M2  Keyword Count (ordinal 0–5)      →  ordered logistic", True),
    ("M3  Rating (ordinal 1–5)              →  ordered logistic (exploratory)", True),
    ("M4  Reactions (overdispersed count) →  negative binomial", True),
    ("", True),
    ("Keyword Count is modelled as ordinal, not count: its range is "
     "platform-capped at five, not a Poisson-generated process.", True),
    ("키워드 수는 계수형이 아니라 순서형으로 모델링한다. 상한이 플랫폼 "
     "설계상 5로 고정되기 때문이며, 포아송 과정이 아니다.", False),
    ("", True),
    ("All models include place fixed effects δⱼ; standard errors clustered "
     "by reviewer.", True),
    ("모든 모형은 관광지 고정효과 δⱼ를 포함하며, 표준오차는 작성자 단위로 "
     "클러스터링한다.", False),
]


def add_content_slide(prs, title_en, title_ko, body_items):
    """Add a slide using Layout 3 'Title text and image', title at top,
    content body spanning full width. Removes picture placeholder."""
    layout = prs.slide_masters[0].slide_layouts[3]
    slide = prs.slides.add_slide(layout)

    # Remove the picture placeholder (we don't use it)
    for shape in list(slide.shapes):
        if shape.has_text_frame:
            continue
        try:
            if shape.placeholder_format is not None and shape.placeholder_format.idx == 10:
                sp = shape._element
                sp.getparent().remove(sp)
        except Exception:
            pass

    # Title at top-left, same geometry as Slide 4
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

    # Content: find the content placeholder (idx=11) and reposition to full width
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

    # Slide number text box at the standard position
    sn = slide.shapes.add_textbox(Inches(9.33), Inches(6.69), Inches(3.0), Inches(0.40))
    sn.text_frame.paragraphs[0].text = ""  # user will adjust / let PPT auto-number
    for run in sn.text_frame.paragraphs[0].runs:
        run.font.name = FONT_BODY
        run.font.size = Pt(11)
    return slide


p = Presentation(PPTX)
total_before = len(p.slides)

# Build the two new slides at the end...
add_content_slide(p, *SLIDE11_TITLE, SLIDE11_BODY)
add_content_slide(p, *SLIDE12_TITLE, SLIDE12_BODY)

# ...then move them to positions 11 and 12 (0-indexed 10 and 11),
# right after Slide 10 (section title "3. Methodology")
xml_slides = p.slides._sldIdLst
slides_list = list(xml_slides)
new_s11 = slides_list[-2]
new_s12 = slides_list[-1]
xml_slides.remove(new_s11)
xml_slides.remove(new_s12)
xml_slides.insert(10, new_s11)
xml_slides.insert(11, new_s12)

p.save(PPTX)
print(f"OK. Section 3 added to {PPTX}:")
print(f"  Total slides: {total_before} -> {len(p.slides)}")
print("  - Slide 11 (NEW): Data overview")
print("  - Slide 12 (NEW): Variables and Models")
