"""
fix_title.py
Replace the placeholder title ("Rotten and Fresh Fruits...") on Slide 1
with the real paper title.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Pt

PPTX = "presentation_build.pptx"
FONT_HEAD = "Source Sans"

TITLE_EN = "Visit Context, Information Diversity and Reader Response on Naver Place"
TITLE_KO = "네이버 플레이스의 방문 맥락, 정보 다양성, 이용자 반응"
AUTHOR_EN = "Jorge Adan Soriano Hernandez"
AUTHOR_KO = "소리아노 에르난데스 호르헤 아단"
AFFIL_EN  = "Department of Data Science, Hoseo University"
AFFIL_KO  = "호서대학교 데이터사이언스학과"
DATE_LINE = "October 2026  |  2026년 10월"

p = Presentation(PPTX)
slide1 = p.slides[0]

# Find the title placeholder (should be the only text shape with the old title)
title_shape = None
for shape in slide1.shapes:
    if shape.has_text_frame and "Rotten and Fresh" in shape.text_frame.text:
        title_shape = shape
        break

if title_shape is None:
    print("Could not find title shape; listing shapes:")
    for s in slide1.shapes:
        if s.has_text_frame:
            print(f"  [{s.name}] {s.text_frame.text[:80]}")
    raise RuntimeError("Title shape not found on slide 1")

tf = title_shape.text_frame
tf.word_wrap = True
tf.clear()

p1 = tf.paragraphs[0]
p1.text = TITLE_EN
for run in p1.runs:
    run.font.name = FONT_HEAD

p2 = tf.add_paragraph()
p2.text = TITLE_KO
for run in p2.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(22)

# Blank spacer
tf.add_paragraph().text = ""

p3 = tf.add_paragraph()
p3.text = AUTHOR_EN
for run in p3.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(16)

p4 = tf.add_paragraph()
p4.text = AUTHOR_KO
for run in p4.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(14)

p5 = tf.add_paragraph()
p5.text = AFFIL_EN
for run in p5.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(12)

p6 = tf.add_paragraph()
p6.text = AFFIL_KO
for run in p6.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(12)

p7 = tf.add_paragraph()
p7.text = DATE_LINE
for run in p7.runs:
    run.font.name = FONT_HEAD
    run.font.size = Pt(11)

p.save(PPTX)
print(f"OK. Title of {PPTX} replaced.")
print(f"  EN: {TITLE_EN}")
print(f"  KO: {TITLE_KO}")
