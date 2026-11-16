# Section 1 — Introduction

**Target file:** `presentation_build.pptx` (copia del template, no se modifica `templateppt.pptx`).
**Slides covered:** 3, 4, 5 (section title + motivation + research questions).
**Section talk time:** ~1.5–2 min (section title 10s, motivation 50s, RQs 40s).

---

## Slide 3 — Section separator (sin cambios)

Esta slide ya existe en el template y no se tocó. Contiene:

- **Title:** `1. Introduction / 서론`
- **Layout:** Section Title 1
- **Picture:** la imagen full-left del template se mantiene.

**Speaker notes:** "We begin with the motivation for this study. 본 연구의 동기부터 시작합니다."

---

## Slide 4 — Introduction / Motivation

- **Layout:** Title text and image (sin cambios en layout)
- **Title (sin cambios):** `Introduction 서론`
- **Image column (sin cambios):** 3 screenshots de low/high-review coffee shops. Si quieres cambiarlas por capturas de attractions reales, hazlo manualmente desde PowerPoint.
- **Caption y footnotes (sin cambios):** `Figure 1. Comparasion between low and high review coffee shops.` y `* Screenshot images from https://map.naver.com/p/`

### Body text (reemplazado)

```
Online reviews drive travel decisions.
온라인 리뷰는 여행 결정을 좌우한다.

Lee et al. (2026) link information diversity to business performance
at the business-week level, but who writes diverse reviews stays
unobserved.
이민영 외 (2026)는 리뷰 다양성이 사업체-주 단위 성과를 예측함을
보였으나, 작성자 측 요인은 관찰되지 않는다.

This study takes the construct to the individual review, combined
with Naver's structured visit context: companion, purpose, wait,
reservation.
본 연구는 이 개념을 개별 리뷰 수준으로 확장하고, 네이버의 구조화된
방문 맥락(동반자, 목적, 대기, 예약)과 결합한다.
```

### Speaker notes (ES para que te sirvan a ti al preparar)

> "Las reseñas online guían las decisiones de viaje. Lee et al. (2026) demostraron que la diversidad informativa en reseñas predice performance a nivel empresa-semana, pero no observan quién produce esa diversidad. Nosotros bajamos el constructo al nivel review individual, combinándolo con el contexto estructurado de visita que Naver captura: compañero, propósito, espera, reserva."

### Chequeo visual recomendado al abrir en PowerPoint

- [ ] El texto cabe en la columna izquierda sin desbordar
- [ ] Las 3 imágenes a la derecha siguen visibles
- [ ] El tamaño de las líneas KO (glosa) se ve razonable comparado con EN

Si el texto desborda, podemos acortar algún párrafo. Avísame.

---

## Slide 5 — Research Questions *(NUEVA)*

- **Layout:** Title and Content (mismo estilo que la Agenda — título izquierdo, contenido derecho)
- **Posición:** Insertada entre Introduction y Section 2 (ocupa posición 5)

### Title

```
Research Questions
연구 질문
```

### Content (4 RQs bilingües)

```
1. Which visit contexts predict returning to the same attraction?
    어떤 방문 맥락이 재방문과 연관되는가?

2. Which reviewers and visit contexts produce more diverse keywords?
    어떤 작성자와 방문 맥락이 더 많은 키워드를 생성하는가?

3. Which reviews receive reactions? Does sentiment help?
    어떤 리뷰가 반응을 받는가? 감성은 도움이 되는가?

4. Which aspects do reviewer groups discuss, and does content predict
   engagement beyond sentiment?
    어떤 방문 측면을 작성자 그룹이 언급하며, 내용이 감성 이상의
    몰입을 예측하는가?
```

### Speaker notes

> "Cuatro preguntas guían el estudio: RQ1 sobre antecedentes del revisit; RQ2 sobre antecedentes de diversidad informativa; RQ3 sobre engagement de lectura; y RQ4 — nueva en esta versión — sobre qué aspectos específicos del contenido predicen engagement más allá del sentimiento general."

### Chequeo visual recomendado

- [ ] Las 4 RQs caben en el área de contenido (5.25" × 5.5")
- [ ] La indentación de las líneas KO se nota
- [ ] El tamaño del título "Research Questions" + "연구 질문" se ve balanceado

---

## Cómo se mapea Section 1 al paper

| Slide | Elemento | Paper § | Resumen § |
|---|---|---|---|
| 3 | Section separator | — | — |
| 4 | Motivation + framing | §1.1 Research Background | §1 Topic + §2 Problem |
| 5 | 4 RQs incl. RQ4 (aspects) | §1.2 Research Questions | §3 Research questions |

Las 4 RQs del slide 5 coinciden **exactamente** con §1.2 del paper actualizado y con §3 del resumen.

---

## Cambios y archivos relacionados

| Archivo | Status |
|---|---|
| `templateppt.pptx` | **NO modificado** (preservado como base de referencia) |
| `presentation_build.pptx` | Modificado: slide 4 body replaced + slide 5 inserted |
| `build_section1.py` | Script que aplica los cambios (reproducible) |
| `section_01_introduction.md` | Este documento (specs + referencia textual) |

## Próximos pasos

1. **Tú abres** `presentation_build.pptx` en PowerPoint y revisas slides 3-5
2. **Me compartes feedback**:
   - ¿El texto cabe bien?
   - ¿Las imágenes de slide 4 las queremos cambiar o quitarse?
   - ¿La redacción EN/KO suena natural?
   - ¿Las 4 RQs se leen claras?
3. **Si OK**, pasamos a **Section 2 — Theoretical Background** (slides 6, 7, 8, 9)
4. **Si cambios**, los aplicamos antes de avanzar
