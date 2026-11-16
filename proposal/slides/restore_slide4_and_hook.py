"""
restore_slide4_and_hook.py

Recovers slide 4 to the state it was in before my previous edit and then
adds the news hook as a NEW block below the existing intro, keeping
everything that was there intact.

Steps:
  1. Extract image1/image2/image3 from the pptx archive to temp files.
  2. Delete the two news-hook textboxes I added with the wrong red colour.
  3. Restore the intro textboxes to their original height (4.38 in).
  4. Re-add the 3 pictures at their original positions (right side).
  5. Add a new bilingual news-hook block at the bottom of the slide
     (full width, EN left column + KO right column), using the project's
     standard HEAD green colour (no red/orange).
  6. Footer "[Lee et al., 2026]" is left untouched.
"""
import os, sys, zipfile, tempfile, shutil
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
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
HEAD  = RGBColor(0x23, 0x31, 0x2D)   # dark forest green per reference_pptx_formats


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


# ── 1. Extract the 3 images from the pptx ──────────────────────────────────
tmpdir = tempfile.mkdtemp(prefix="slide4_imgs_")
img_paths = []
with zipfile.ZipFile(PPTX) as z:
    for name in ("ppt/media/image1.png", "ppt/media/image2.png",
                 "ppt/media/image3.png"):
        out = os.path.join(tmpdir, os.path.basename(name))
        with z.open(name) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)
        img_paths.append(out)
print(f"Extracted images to {tmpdir}")

# ── 2. Load and clean up slide 4 ───────────────────────────────────────────
p = Presentation(PPTX)
slide = p.slides[3]
print(f"\nSlide 4 shapes before cleanup: {len(slide.shapes)}")

# Delete all textboxes except Title and the footer (TextBox 13)
# and both intro textboxes (TextBox 11, TextBox 12).
# My wrongly-coloured news hook was added as new textboxes with
# unnamed/auto names different from "TextBox 11/12/13" and "Title 2".
KEEP = {"Title 2", "TextBox 11", "TextBox 12", "TextBox 13"}
for sh in list(slide.shapes):
    if sh.has_text_frame and sh.name not in KEEP:
        print(f"  Removing added textbox: {sh.name}")
        sh._element.getparent().remove(sh._element)

# ── 3. Restore intro textbox heights ───────────────────────────────────────
en_intro = next(s for s in slide.shapes if s.name == "TextBox 11")
ko_intro = next(s for s in slide.shapes if s.name == "TextBox 12")
en_intro.top = Inches(1.50)
en_intro.height = Inches(4.38)
ko_intro.top = Inches(1.50)
ko_intro.height = Inches(4.38)
print("  Restored intro textbox heights to 4.38 in.")

# ── 4. Re-add the 3 pictures at original positions ─────────────────────────
positions = [(5.97, 0.77, 2.14, 4.77),
             (8.21, 0.77, 2.14, 4.77),
             (10.45, 0.77, 2.14, 4.77)]
for img_path, (L, T, W, H) in zip(img_paths, positions):
    slide.shapes.add_picture(img_path, Inches(L), Inches(T),
                              width=Inches(W), height=Inches(H))
print("  Re-added 3 pictures at original positions.")

# ── 5. Add bilingual news hook at bottom, 2 columns, HEAD green ────────────
# Available strip: y = 5.95 to 6.80 (above footer at 6.90).
# Full width ≈ 12.5 in. Two columns: EN left, KO right.
hook_en = slide.shapes.add_textbox(
    Inches(0.40), Inches(5.95), Inches(6.00), Inches(0.90))
tf = hook_en.text_frame
tf.word_wrap = True
add_para(tf, "A real-world paradox",
         size=11, bold=True, color=HEAD, first=True)
add_para(tf,
         "Incheon, 2026: one reviewer visited a restaurant 43 times. "
         "Each review praised the staff ('good, friendly'); each rating "
         "was 1 star. Rating fell to 2.9. The owner closed. In our data: "
         "r(rating, revisit) = 0.08.",
         size=9, color=DARK, space_before=3)

hook_ko = slide.shapes.add_textbox(
    Inches(6.50), Inches(5.95), Inches(6.10), Inches(0.90))
tf = hook_ko.text_frame
tf.word_wrap = True
add_para(tf, "현실의 역설",
         size=11, bold=True, color=HEAD, first=True)
add_para(tf,
         "2026년 인천: 한 리뷰어가 어느 횟집을 43번 방문. 매번 '굿, "
         "친절해요'라고 썼지만 매번 별점은 1점. 평점은 2.9까지 하락, "
         "사장님 폐업. 저희 데이터: r(별점, 재방문) = 0.08.",
         size=9, color=DARK, space_before=3)
print("  Added bilingual news hook at bottom (HEAD green, no red).")

# ── Save ───────────────────────────────────────────────────────────────────
p.save(PPTX)
print(f"\nSlide 4 shapes after: {len(slide.shapes)}")
print(f"Saved to: {PPTX}")

# cleanup temp images
shutil.rmtree(tmpdir, ignore_errors=True)
