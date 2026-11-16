# proposal/

LaTeX sources for the Naver Place study. Scope is Naver only — the
cross-cultural branch (Google Maps, foreign tourists, H1–H5) is paused and is
not described in any of these documents.

## Layout

One folder per document — `.tex`, `.pdf` and the compiler's `.aux`/`.log`/`.out`
all stay together, the same way `slides/` already worked. Compiling from
inside a document's own folder needs no `-output-directory` and nothing to
move afterward: the PDF lands right next to its source.

```
proposal/
  tables_naver.tex      shared, generated table fragment -- not a document, see below
  abstract_reviews/      abstract_reviews.tex + .pdf
  preliminary_report/    preliminary_report.tex + .pdf
  report_naver/          report_naver.tex + .pdf + .aux/.log/.out
  resumen_proyecto/       resumen_proyecto.tex + .pdf + .aux/.log
  synopsis_reviews/       synopsis_reviews.tex + .pdf
  slides/                 presentacion.tex + .pdf + the UBI beamer theme files
  drawio/                 diagram sources
  archive/                superseded drafts
```

## Documents

| Folder | What it is | Engine |
|---|---|---|
| `report_naver/` | Full bilingual EN/KO academic report, following 이민영 외 (2026)'s own section format (I–V) | `xelatex` ×2 |
| `resumen_proyecto/` | 4-page bilingual EN/KO project summary, same reference format | `xelatex` ×2 |
| `slides/` | 14-slide bilingual deck on the UBI beamer theme | `lualatex` ×2 |
| `abstract_reviews/` | Conference abstract | `xelatex` |
| `preliminary_report/` | Longer preliminary report | `xelatex` |
| `synopsis_reviews/` | Short synopsis | `xelatex` |

Compile twice — cross-references (`report_naver`, `resumen_proyecto`) and the
deck's frame count (`presentacion`) both need a second pass.

```powershell
cd proposal/resumen_proyecto
xelatex resumen_proyecto.tex ; xelatex resumen_proyecto.tex

cd ../report_naver
xelatex report_naver.tex ; xelatex report_naver.tex

cd ../slides
lualatex presentacion.tex ; lualatex presentacion.tex
```

The same pattern applies to `abstract_reviews/`, `preliminary_report/` and
`synopsis_reviews/` — `cd` into the folder, run `xelatex <name>.tex`.

## Generated tables

`tables_naver.tex`, at the `proposal/` root, is **generated** — do not edit it
by hand. It is written by `10_01_descriptive_tables.py` in the project root
(`TEX = ROOT / "proposal" / "tables_naver.tex"`) and defines four reusable
macros:

| Macro | Table |
|---|---|
| `\tblVariables` | 표 1 변수요약 |
| `\tblDescriptives` | 표 2 기술통계표 |
| `\tblCorrelations` | 표 3 상관분석표 |
| `\tblVIF` | 표 4 분산팽창계수 |

It sits at the `proposal/` root rather than inside any one document's folder
because three different documents pull it in: `report_naver/report_naver.tex`
and `resumen_proyecto/resumen_proyecto.tex` each via `\input{../tables_naver}`,
and `slides/presentacion.tex` the same way. They are macros rather than plain
content because `resumen_proyecto.tex` and `report_naver.tex` each print every
table twice — once in their English half, once in their Korean half — and
duplicate `\label` keys would clash.

To refresh the numbers after a pipeline run:

```powershell
python 10_01_descriptive_tables.py      # from the project root; writes proposal/tables_naver.tex
cd proposal/resumen_proyecto ; xelatex resumen_proyecto.tex ; xelatex resumen_proyecto.tex
cd ../report_naver           ; xelatex report_naver.tex     ; xelatex report_naver.tex
cd ../slides                 ; lualatex presentacion.tex    ; lualatex presentacion.tex
```

Everything else in the documents — the model results, the AUC and RMSE
figures, the odds ratios — is written by hand and has to be updated manually
if the models change.

## Two traps worth knowing

**The deck needs LuaLaTeX, not XeLaTeX.** Under XeLaTeX the UBI theme renders
only its first two frames; every later one comes out blank. Its README says it
was written for LuaLaTeX, and that is correct. Korean therefore comes from a
luaotfload font fallback (Georgia for Latin, Malgun Gothic for Hangul) rather
than from `xeCJK`.

**The theme's body text is invisible by default.** It sets `normal text` to
UBIgrey (RGB 191,191,191), which reads on the dark title slide but not on the
light content frames. `presentacion.tex` overrides it.

## Folders

- `slides/` — the deck plus the UBI theme files. The theme's background PDFs are
  loaded by relative name, so compile from inside this directory.
- `drawio/` — diagram sources.
- `archive/` — superseded drafts: the cross-cultural version of the summary, the
  appendix-style version, the original pptxgenjs deck generator, and the UBI
  theme's own example.
