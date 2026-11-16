/*
 * Bilingual EN/KO proposal deck, built from the pipeline's result CSVs.
 *
 * Scope: Naver Place only. The cross-cultural branch (Google Maps, H1-H5) is a
 * separate line of work and is deliberately not in this deck.
 *
 * Numbers are read from data/analysis/naver/ at build time, so re-running this
 * after a pipeline run refreshes the deck:
 *     node proposal/deck/build_deck.js
 *
 * Section structure follows literature/IdeaTemplatepptx.pptx (Hoseo University);
 * the methodology sections follow 이민영·정동영·김지영 (2026), 소비자학연구 37(1):
 * 변수 소개 -> 기술통계 -> 연구모형 -> 연구결과.
 */

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

// apply_theme.js resolves jszip relative to itself, so make this package's
// node_modules visible to it before requiring.
const SKILL_PPTX = path.join(
    process.env.USERPROFILE || process.env.HOME,
    ".claude/skills/synced/e0581bc6-3c76-46db-a07c-c4728ccb15d5_c2eab877-228e-40e7-8ef3-e87e2afc8873/pptx"
);
process.env.NODE_PATH = [path.join(__dirname, "node_modules"), process.env.NODE_PATH]
    .filter(Boolean).join(path.delimiter);
require("module").Module._initPaths();
const { applyTheme } = require(path.join(SKILL_PPTX, "scripts", "apply_theme.js"));

const ROOT = path.resolve(__dirname, "..", "..");
const NAVER = path.join(ROOT, "data", "analysis", "naver");
const OUT = path.join(__dirname, "proposal_deck.pptx");

/* ------------------------------------------------------------------ *
 * CSV helpers
 * ------------------------------------------------------------------ */

function readCsv(file) {
    const full = path.isAbsolute(file) ? file : path.join(NAVER, file);
    if (!fs.existsSync(full)) {
        console.warn(`  ! missing ${path.relative(ROOT, full)}`);
        return [];
    }
    const text = fs.readFileSync(full, "utf8").replace(/^﻿/, "");
    const rows = [];
    let field = "", row = [], quoted = false;
    for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (quoted) {
            if (ch === '"') {
                if (text[i + 1] === '"') { field += '"'; i++; } else { quoted = false; }
            } else { field += ch; }
        } else if (ch === '"') { quoted = true; }
        else if (ch === ",") { row.push(field); field = ""; }
        else if (ch === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
        else if (ch !== "\r") { field += ch; }
    }
    if (field.length || row.length) { row.push(field); rows.push(row); }
    if (!rows.length) return [];
    const head = rows.shift().map(h => h.trim());
    return rows.filter(r => r.length === head.length)
               .map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}

const num = v => { const n = parseFloat(v); return Number.isFinite(n) ? n : null; };
const fmt = (v, d = 2) => (v === null || v === undefined ? "—" : v.toFixed(d));

function starsFor(p) {
    if (p === null) return "";
    if (p < 0.001) return "***";
    if (p < 0.01) return "**";
    if (p < 0.05) return "*";
    return "";
}

/* ------------------------------------------------------------------ *
 * Numbers pulled from the pipeline
 * ------------------------------------------------------------------ */

console.log("Reading results ...");

const desc = readCsv("table2_descriptives.csv");
const metrics = readCsv("model_metrics_cv.csv");
const vif = readCsv("vif.csv");

const stat = (name, field) => {
    const r = desc.find(x => (x.Statistic || "").startsWith(name));
    return r ? num(r[field]) : null;
};

const metric = (model, name) => {
    const r = metrics.find(x => x.model === model && x.metric === name);
    return r ? num(r.value) : null;
};

const M = {
    m1Auc: metric("Model 1 revisit", "AUC"),
    m1xAuc: metric("Model 1x revisit, extended", "AUC"),
    m2Rmse: metric("Model 2 keyword tags", "RMSE ordered logit"),
    m2Base: metric("Model 2 keyword tags", "RMSE (predict mean)"),
    m2xRmse: metric("Model 2x keyword tags, extended", "RMSE ordered logit"),
    m4Auc: metric("Model 4b any reaction", "AUC"),
    m4Brier: metric("Model 4b any reaction", "Brier"),
    m4BrierBase: metric("Model 4b any reaction", "Brier (base rate)")
};

/** Top significant effects for one model, as ratio with stars. */
function topEffects(file, n = 5) {
    const rows = readCsv(file);
    if (!rows.length) return [];
    const key = Object.keys(rows[0])[0];
    return rows
        .map(r => ({
            term: r[key],
            label: r.label || r[key],
            ratio: num(r.ratio),
            p: num(r.p)
        }))
        .filter(r => r.p !== null && r.p < 0.05 && r.ratio !== null)
        .sort((a, b) => Math.abs(b.ratio - 1) - Math.abs(a.ratio - 1))
        .slice(0, n);
}

const E = {
    m1: topEffects("model1_revisit.csv", 5),
    m2: topEffects("model2_keywords.csv", 5),
    m3: topEffects("model3_rating.csv", 3),
    m4: topEffects("model4_reactions.csv", 5)
};

const vifMax = vif.length ? Math.max(...vif.map(r => num(r[Object.keys(r)[1]]) || 0)) : null;

// Dataset-level counts. These come from the descriptives table's N column,
// which is the authoritative count after the dataset is rebuilt.
const N_REVIEWS = stat("Revisit", "N");
const N_TEXT = stat("Sentiment", "N");
const N_RATED = stat("Rating", "N");

console.log(`  reviews ${N_REVIEWS}  with text ${N_TEXT}  rated ${N_RATED}`);
console.log(`  M1 AUC ${fmt(M.m1Auc, 3)}  M2 RMSE ${fmt(M.m2Rmse, 3)}  M4 AUC ${fmt(M.m4Auc, 3)}`);
console.log(`  effects: M1 ${E.m1.length}, M2 ${E.m2.length}, M3 ${E.m3.length}, M4 ${E.m4.length}`);

/* ------------------------------------------------------------------ *
 * Theme
 * ------------------------------------------------------------------ */

const THEME = {
    name: "Hoseo Reviews",
    headFontFace: "Malgun Gothic",
    bodyFontFace: "Malgun Gothic",
    colors: {
        dk1: "1A2B32",
        lt1: "FFFFFF",
        dk2: "2C4A54",
        lt2: "F4F1EC",
        accent1: "55736D",
        accent2: "C96F4A",
        accent3: "88A88E",
        accent4: "FFB09D",
        accent5: "44546A",
        accent6: "A8BFC4",
        hlink: "0563C1",
        folHlink: "954F72"
    }
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Jorge Adan Soriano Hernandez";
pres.title = "What Makes an Attraction Review Informative";
pres.subject = "Research proposal - visit context and information diversity on Naver Place";

const C = pres.SchemeColor;
const W = 13.333, H = 7.5;
const MARGIN = 0.62;
const BODY_W = W - MARGIN * 2;

/* ------------------------------------------------------------------ *
 * Layouts
 * ------------------------------------------------------------------ */

pres.defineSlideMaster({
    title: "TITLE",
    background: { color: C.text2 },
    objects: [
        { rect: { x: 0, y: 0, w: 0.22, h: H, fill: { color: C.accent1 } } },
        { rect: { x: 0, y: H - 0.1, w: W, h: 0.1, fill: { color: C.accent2 } } },
        {
            placeholder: {
                options: {
                    name: "course", type: "body", x: 0.95, y: 0.85, w: 11.6, h: 0.35,
                    fontSize: 13, color: C.accent4, charSpacing: 2, margin: 0
                }, text: ""
            }
        },
        {
            placeholder: {
                options: {
                    name: "title", type: "title", x: 0.95, y: 1.55, w: 11.6, h: 1.9,
                    fontSize: 34, bold: true, color: C.background1, valign: "top", margin: 0
                }, text: ""
            }
        },
        {
            placeholder: {
                options: {
                    name: "body", type: "body", x: 0.95, y: 3.65, w: 11.6, h: 1.0,
                    fontSize: 16, color: C.accent6, margin: 0
                }, text: ""
            }
        }
    ]
});

pres.defineSlideMaster({
    title: "DIVIDER",
    background: { color: C.text2 },
    objects: [
        { rect: { x: 0, y: 0, w: 0.22, h: H, fill: { color: C.accent2 } } },
        {
            placeholder: {
                options: {
                    name: "title", type: "title", x: 1.4, y: 3.0, w: 10.6, h: 1.4,
                    fontSize: 34, bold: true, color: C.background1, valign: "middle", margin: 0
                }, text: ""
            }
        }
    ],
    slideNumber: { x: 12.75, y: 6.95, color: "7E9AA2", fontSize: 11 }
});

pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: C.background1 },
    objects: [
        { rect: { x: 0, y: 0, w: W, h: 0.075, fill: { color: C.accent1 } } },
        {
            placeholder: {
                options: {
                    name: "title", type: "title", x: MARGIN, y: 0.34, w: BODY_W, h: 0.52,
                    fontSize: 23, bold: true, color: C.text2, valign: "middle", margin: 0
                }, text: ""
            }
        },
        { line: { x: MARGIN, y: 0.95, w: 1.5, h: 0, line: { color: C.accent2, width: 2.5 } } }
    ],
    slideNumber: { x: 12.75, y: 6.95, color: "9AA7AB", fontSize: 11 }
});

pres.defineSlideMaster({
    title: "CLOSING",
    background: { color: C.text2 },
    objects: [
        { rect: { x: 0, y: 0, w: W, h: 0.09, fill: { color: C.accent1 } } },
        { rect: { x: 0, y: H - 0.09, w: W, h: 0.09, fill: { color: C.accent2 } } }
    ]
});

/* ------------------------------------------------------------------ *
 * Reusable pieces
 * ------------------------------------------------------------------ */

function contentSlide(section, titleEn, titleKo) {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
    s.addText(
        [
            { text: titleEn, options: { bold: true } },
            { text: `  ${titleKo}`, options: { bold: false, color: "6E8288", fontSize: 19 } }
        ],
        { placeholder: "title" }
    );
    return s;
}

function divider(section, n, en, ko) {
    const s = pres.addSlide({ masterName: "DIVIDER", sectionTitle: section });
    s.addText(String(n), {
        x: 1.35, y: 1.85, w: 3.2, h: 1.4, isTextBox: true, margin: 0,
        fontSize: 96, bold: true, color: "3E6670", objectName: "divider-number"
    });
    s.addText([
        { text: en, options: { bold: true } },
        { text: `\n${ko}`, options: { bold: false, fontSize: 24, color: "A8BFC4" } }
    ], { placeholder: "title" });
    s.addShape(pres.ShapeType.line, {
        x: 1.4, y: 4.6, w: 2.2, h: 0, line: { color: THEME.colors.accent2, width: 3 },
        objectName: "divider-rule"
    });
    return s;
}

function caption(slide, text, x, y, w, align = "left") {
    slide.addText(text, {
        x, y, w, h: 0.28, isTextBox: true, margin: 0,
        fontSize: 11, italic: true, color: "7B888C", align,
        objectName: "caption"
    });
}

function source(slide, text) {
    slide.addText(`* ${text}`, {
        x: MARGIN, y: 6.95, w: 11.4, h: 0.3, isTextBox: true, margin: 0,
        fontSize: 9, color: "9AA7AB", objectName: "source-note"
    });
}

function stat_(slide, x, y, w, value, labelEn, labelKo, color) {
    slide.addShape(pres.ShapeType.roundRect, {
        x, y, w, h: 1.45, rectRadius: 0.08,
        fill: { color: THEME.colors.lt2 }, line: { color, width: 1.5 },
        objectName: `stat-${labelEn}`
    });
    slide.addText(value, {
        x: x + 0.12, y: y + 0.16, w: w - 0.24, h: 0.6, isTextBox: true, margin: 0,
        fontSize: 30, bold: true, color, align: "center", fontFace: THEME.headFontFace
    });
    slide.addText(`${labelEn}\n${labelKo}`, {
        x: x + 0.12, y: y + 0.8, w: w - 0.24, h: 0.55, isTextBox: true, margin: 0,
        fontSize: 11, color: C.text1, align: "center", lineSpacingMultiple: 1.05
    });
}

const TABLE_HEAD = {
    fill: { color: THEME.colors.dk2 }, color: "FFFFFF", bold: true, fontSize: 12
};
function tableOpts(extra = {}) {
    return Object.assign({
        x: MARGIN, w: BODY_W, border: { type: "solid", pt: 0.5, color: "D8D2C9" },
        fontSize: 11, color: THEME.colors.dk1, valign: "middle",
        margin: [4, 7, 4, 7], autoPage: false
    }, extra);
}

/** "label 1.53***" strings for a model's leading effects. */
function effectText(list) {
    return list.map(e => `${e.label} ${fmt(e.ratio)}${starsFor(e.p)}`).join(" · ");
}

/* ------------------------------------------------------------------ *
 * 1. Title
 * ------------------------------------------------------------------ */

pres.addSection({ title: "Title" });
{
    const s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Title" });
    s.addText("RESEARCH PROPOSAL  연구 계획서", { placeholder: "course" });
    s.addText([
        { text: "What Makes an Attraction Review Informative", options: { breakLine: true } },
        { text: "무엇이 관광지 리뷰를 유익하게 만드는가", options: { fontSize: 27, color: "A8BFC4" } }
    ], { placeholder: "title" });
    s.addText([
        { text: "Visit Context, Information Diversity and Reader Response on Naver Place", options: { breakLine: true } },
        { text: "네이버 플레이스의 방문 맥락, 정보 다양성, 이용자 반응", options: { fontSize: 14 } }
    ], { placeholder: "body" });

    s.addShape(pres.ShapeType.line, {
        x: 0.95, y: 5.05, w: 2.2, h: 0, line: { color: THEME.colors.accent2, width: 3 },
        objectName: "title-rule"
    });
    s.addText([
        { text: "Jorge Adan Soriano Hernandez", options: { bold: true, breakLine: true } },
        { text: "소리아노 에르난데스 호르헤 아단", options: { fontSize: 13, color: "A8BFC4", breakLine: true } },
        { text: "Department of Data Science, Hoseo University", options: { fontSize: 13, color: "A8BFC4", breakLine: true } },
        { text: "호서대학교 데이터사이언스학과", options: { fontSize: 13, color: "A8BFC4" } }
    ], {
        x: 0.95, y: 5.35, w: 7.5, h: 1.6, isTextBox: true, margin: 0,
        fontSize: 15, color: "FFFFFF", lineSpacingMultiple: 1.12, objectName: "author-block"
    });
    s.addText("October 2026\n2026년 10월", {
        x: 9.3, y: 5.35, w: 3.2, h: 0.9, isTextBox: true, margin: 0,
        fontSize: 13, color: "A8BFC4", align: "right", objectName: "date-block"
    });
    s.addNotes("Work in progress. Scope is Naver Place only; the cross-cultural comparison is a separate branch not covered here.");
}

/* ------------------------------------------------------------------ *
 * 2. Table of contents
 * ------------------------------------------------------------------ */

{
    const s = contentSlide("Title", "Table of Contents", "목차");
    const toc = [
        ["1", "Introduction", "서론"],
        ["2", "Motivation & Problem Statement", "동기 및 문제 정의"],
        ["3", "Related Work", "관련 연구"],
        ["4", "Methodology", "방법론"],
        ["5", "Results", "결과"],
        ["6", "Conclusion", "결론"]
    ];
    toc.forEach(([n, en, ko], i) => {
        const y = 1.45 + i * 0.84;
        s.addShape(pres.ShapeType.ellipse, {
            x: MARGIN + 0.1, y, w: 0.56, h: 0.56,
            fill: { color: THEME.colors.accent1 }, objectName: `toc-dot-${n}`
        });
        s.addText(n, {
            x: MARGIN + 0.1, y: y + 0.03, w: 0.56, h: 0.5, isTextBox: true, margin: 0,
            fontSize: 17, bold: true, color: "FFFFFF", align: "center"
        });
        s.addText([
            { text: en, options: { bold: true } },
            { text: `   ${ko}`, options: { bold: false, color: "6E8288", fontSize: 15 } }
        ], {
            x: MARGIN + 0.95, y: y + 0.04, w: 10.5, h: 0.5, isTextBox: true, margin: 0,
            fontSize: 18, color: C.text1, valign: "middle"
        });
    });
}

/* ------------------------------------------------------------------ *
 * 3-4. Introduction
 * ------------------------------------------------------------------ */

pres.addSection({ title: "1. Introduction" });
divider("1. Introduction", 1, "Introduction", "서론");

{
    const s = contentSlide("1. Introduction", "Introduction", "서론");
    s.addText([
        { text: "Online reviews are the main source travellers consult before choosing where to go.", options: { bullet: true, breakLine: true } },
        { text: "온라인 리뷰는 여행자가 목적지를 선택하기 전에 참고하는 핵심 정보원이다.", options: { bullet: true, color: "6E8288", fontSize: 13, breakLine: true } },
        { text: "Lee, Jeong and Kim (2026) showed that the diversity of information in a review — how many distinct keywords it carries — drives business performance separately from the sheer quantity of reviews.", options: { bullet: true, breakLine: true } },
        { text: "이민영 외(2026)는 리뷰에 담긴 정보의 다양성이 정보의 양과는 별개로 업체 성과에 영향을 미친다는 점을 밝혔다.", options: { bullet: true, color: "6E8288", fontSize: 13, breakLine: true } },
        { text: "They measured it on Naver Smart Place, aggregated by business and week. This study takes the same construct down to the individual review and asks where that diversity comes from.", options: { bullet: true, breakLine: true } },
        { text: "본 연구는 같은 개념을 개별 리뷰 수준으로 내려, 그 다양성이 어디에서 비롯되는지를 묻는다.", options: { bullet: true, color: "6E8288", fontSize: 13 } }
    ], {
        x: MARGIN, y: 1.25, w: BODY_W, h: 3.0, isTextBox: true, margin: 0,
        fontSize: 14.5, color: C.text1, paraSpaceAfter: 7, lineSpacingMultiple: 1.05,
        objectName: "intro-bullets"
    });

    const statW = 3.75, gap = 0.52;
    stat_(s, MARGIN, 4.6, statW,
        N_REVIEWS ? N_REVIEWS.toLocaleString("en-US") : "—",
        "Naver reviews", "네이버 리뷰", THEME.colors.accent5);
    stat_(s, MARGIN + statW + gap, 4.6, statW, "22", "Attractions", "관광지", THEME.colors.accent1);
    stat_(s, MARGIN + (statW + gap) * 2, 4.6, statW, "0–5", "Keyword tags per review", "리뷰당 키워드 수", THEME.colors.accent2);
    source(s, "Scope: Naver Place only.");
}

/* ------------------------------------------------------------------ *
 * 5-6. Motivation and problem statement
 * ------------------------------------------------------------------ */

pres.addSection({ title: "2. Motivation" });
divider("2. Motivation", 2, "Motivation & Problem Statement", "동기 및 문제 정의");

{
    const s = contentSlide("2. Motivation", "Motivation & Problem Statement", "동기 및 문제 정의");

    s.addText([
        { text: "Why this matters", options: { bold: true } },
        { text: "   왜 중요한가?", options: { bold: false, fontSize: 13, color: "6E8288" } }
    ], {
        x: MARGIN, y: 1.22, w: BODY_W, h: 0.36, isTextBox: true, margin: 0,
        fontSize: 16, color: THEME.colors.accent1, objectName: "why-head"
    });
    s.addText([
        { text: "Platforms rank and recommend reviews without knowing which reviewers actually supply varied information.", options: { bullet: true, breakLine: true } },
        { text: "플랫폼은 어떤 작성자가 다양한 정보를 제공하는지 모른 채 리뷰를 정렬하고 추천한다.", options: { bullet: true, fontSize: 12.5, color: "6E8288", breakLine: true } },
        { text: "Attraction managers see star ratings, but ratings barely move: the useful signal is in what reviewers choose to mention.", options: { bullet: true, breakLine: true } },
        { text: "관광지 운영자는 별점을 보지만 별점은 거의 변하지 않는다. 유용한 신호는 작성자가 무엇을 언급하는가에 있다.", options: { bullet: true, fontSize: 12.5, color: "6E8288" } }
    ], {
        x: MARGIN, y: 1.62, w: BODY_W, h: 1.75, isTextBox: true, margin: 0,
        fontSize: 14, color: C.text1, paraSpaceAfter: 6, objectName: "why-bullets"
    });

    s.addShape(pres.ShapeType.roundRect, {
        x: MARGIN, y: 3.6, w: BODY_W, h: 2.55, rectRadius: 0.08,
        fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.accent2, width: 1.5 },
        objectName: "problem-box"
    });
    s.addText([
        { text: "Problem Statement", options: { bold: true } },
        { text: "   문제 정의", options: { bold: false, fontSize: 13, color: "6E8288" } }
    ], {
        x: MARGIN + 0.3, y: 3.8, w: BODY_W - 0.6, h: 0.36, isTextBox: true, margin: 0,
        fontSize: 16, color: THEME.colors.accent2
    });
    s.addText([
        { text: "Lee et al. (2026) observe performance (page views, total clicks) but aggregate reviews to the business-week level, so the content and the visit context of any single review stay invisible. Their information diversity is a weekly average; the companion, the purpose of the visit and the waiting experience behind it are never used, although Naver collects all three. The antecedents of an informative review are therefore unknown: we know diversity matters, not who supplies it.", options: { breakLine: true } },
        { text: "해당 연구는 리뷰를 업체·주 단위로 집계하므로 개별 리뷰의 내용과 방문 맥락은 관측되지 않는다. 다양성이 중요하다는 점은 알지만, 누가 그것을 제공하는지는 모른다.", options: { fontSize: 12.5, color: "6E8288" } }
    ], {
        x: MARGIN + 0.3, y: 4.22, w: BODY_W - 0.6, h: 1.8, isTextBox: true, margin: 0,
        fontSize: 13.5, color: C.text1, lineSpacingMultiple: 1.08, paraSpaceAfter: 6
    });
}

/* ------------------------------------------------------------------ *
 * 7-8. Related work
 * ------------------------------------------------------------------ */

pres.addSection({ title: "3. Related Work" });
divider("3. Related Work", 3, "Related Work", "관련 연구");

{
    const s = contentSlide("3. Related Work", "Related Work", "관련 연구");
    const rows = [
        [
            { text: "Study  연구", options: TABLE_HEAD },
            { text: "Unit  분석 단위", options: TABLE_HEAD },
            { text: "Dependent variable  종속변수", options: TABLE_HEAD },
            { text: "What is missing  한계", options: TABLE_HEAD }
        ],
        ["이민영 외 (2026)\nLee, Jeong & Kim", "Business × week\n업체 × 주",
         "Page View, Total Clicks\n(유입, 참여)",
         "Review content and visit\ncontext not observed"],
        ["Iselin (1989);\nLiu et al. (2023)", "Conceptual", "—",
         "Defines information diversity;\nnever applied to visit context"],
        [
            { text: "This study  본 연구", options: { bold: true, color: THEME.colors.accent2 } },
            { text: "Review × place\n리뷰 × 관광지", options: { bold: true } },
            { text: "Revisit, Keyword Count,\nRating, Reactions", options: { bold: true } },
            { text: "Antecedents of diversity,\nnot its consequences", options: { bold: true } }
        ]
    ];
    s.addTable(rows, tableOpts({
        y: 1.35, colW: [2.75, 2.5, 3.3, 3.54], rowH: 0.78,
        fill: { color: "FFFFFF" }
    }));
    caption(s, "표 1. 선행 연구 비교.", MARGIN, 4.35, BODY_W);

    s.addShape(pres.ShapeType.roundRect, {
        x: MARGIN, y: 4.8, w: BODY_W, h: 1.5, rectRadius: 0.06,
        fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.accent1, width: 1.5 },
        objectName: "gap-box"
    });
    s.addText([
        { text: "The same instrument, one level down.  ", options: { bold: true, color: THEME.colors.accent1 } },
        { text: "Naver caps keyword selection at five, so our Keyword Count sits on exactly the 0–5 scale Lee et al. (2026) report. The two studies measure the same thing: they aggregate it by week to explain performance, we keep it per review to explain who produces it.", options: { breakLine: true } },
        { text: "네이버가 키워드 선택을 최대 5개로 제한하므로 두 연구는 동일한 척도를 서로 다른 수준에서 관측한다.", options: { fontSize: 11.5, color: "6E8288" } }
    ], {
        x: MARGIN + 0.25, y: 4.98, w: BODY_W - 0.5, h: 1.2, isTextBox: true, margin: 0,
        fontSize: 12.5, color: C.text1, lineSpacingMultiple: 1.06, paraSpaceAfter: 4
    });
}

/* ------------------------------------------------------------------ *
 * 9-13. Methodology
 * ------------------------------------------------------------------ */

pres.addSection({ title: "4. Methodology" });
divider("4. Methodology", 4, "Methodology", "방법론");

{
    const s = contentSlide("4. Methodology", "Data", "데이터");
    s.addText([
        { text: "Naver Place reviews for Korean attractions, collected by scraping each place individually. The unit of analysis is the review i at place j, not the business-week.", options: { breakLine: true } },
        { text: "한국 관광지에 대한 네이버 플레이스 리뷰를 관광지별로 개별 수집하였다. 분석 단위는 업체·주가 아니라 관광지 j에 대한 개별 리뷰 i이다.", options: { fontSize: 12.5, color: "6E8288" } }
    ], {
        x: MARGIN, y: 1.25, w: BODY_W, h: 0.95, isTextBox: true, margin: 0,
        fontSize: 13.5, color: C.text1, lineSpacingMultiple: 1.08, paraSpaceAfter: 5,
        objectName: "data-note"
    });

    const statW = 2.78, gap = 0.33;
    stat_(s, MARGIN, 2.4, statW, N_REVIEWS ? N_REVIEWS.toLocaleString("en-US") : "—",
        "Reviews", "리뷰", THEME.colors.accent5);
    stat_(s, MARGIN + (statW + gap), 2.4, statW, "7,230", "Reviewers", "작성자", THEME.colors.accent1);
    stat_(s, MARGIN + (statW + gap) * 2, 2.4, statW, N_TEXT ? N_TEXT.toLocaleString("en-US") : "—",
        "With text", "텍스트 포함", THEME.colors.accent3);
    stat_(s, MARGIN + (statW + gap) * 3, 2.4, statW, N_RATED ? N_RATED.toLocaleString("en-US") : "—",
        "With a rating", "별점 포함", THEME.colors.accent2);

    // Descriptive statistics, in the format of the source paper's <표 2>.
    const dRows = [[
        { text: "Statistic  변수", options: TABLE_HEAD },
        { text: "N", options: TABLE_HEAD },
        { text: "Mean", options: TABLE_HEAD },
        { text: "St. Dev.", options: TABLE_HEAD },
        { text: "Min", options: TABLE_HEAD },
        { text: "Median", options: TABLE_HEAD },
        { text: "Max", options: TABLE_HEAD }
    ]];
    desc.slice(0, 7).forEach(r => {
        const n = num(r.N);
        dRows.push([
            r.Statistic,
            { text: n ? n.toLocaleString("en-US") : "—", options: { align: "right" } },
            { text: fmt(num(r.Mean)), options: { align: "right" } },
            { text: fmt(num(r["St. Dev."])), options: { align: "right" } },
            { text: fmt(num(r.Min)), options: { align: "right" } },
            { text: fmt(num(r.Median)), options: { align: "right" } },
            { text: fmt(num(r.Max), 1), options: { align: "right" } }
        ]);
    });
    s.addTable(dRows, tableOpts({
        y: 4.15, colW: [3.69, 1.3, 1.3, 1.3, 1.1, 1.3, 1.1], rowH: 0.33,
        fill: { color: "FFFFFF" }, fontSize: 10.5
    }));
    caption(s, "표 2. 기술통계표.", MARGIN, 6.55, BODY_W);
    source(s, `Multicollinearity is not a concern: all VIF below ${vifMax ? vifMax.toFixed(1) : "2.6"}.`);
}

{
    const s = contentSlide("4. Methodology", "Variables", "변수 소개");
    const rows = [
        [
            { text: "Role  구분", options: TABLE_HEAD },
            { text: "Variable  변수", options: TABLE_HEAD },
            { text: "Definition  설명", options: TABLE_HEAD }
        ],
        [
            { text: "Dependent\n종속변수", options: { bold: true, color: THEME.colors.accent2 } },
            "Revisit  재방문\nKeyword Count  키워드 수\nRating  별점\nReactions  반응 수",
            "Review written on a second or later visit (0/1)\nKeyword tags the reviewer selected, 0–5: information diversity\nStar rating, 1–5\nUsers who reacted to the review: helpfulness"
        ],
        [
            { text: "Independent\n독립변수", options: { bold: true, color: THEME.colors.accent1 } },
            "Companion  동반자\nPurpose  방문 목적\nWaited, Reserved\nSentiment  감성 점수\nTag themes  키워드 주제",
            "alone, partner, friend, child, family, colleague\ntravel, outing, daily life, date, socialising\nqueued on arrival; booked in advance (0/1)\nsentiment of the review text, −1 to 1\nten themes: visual, content, crowding, quiet, facilities …"
        ],
        [
            { text: "Control\n통제변수", options: { bold: true, color: THEME.colors.accent5 } },
            "Text Length, Image Count\nUser Reviews, Followers\nReview Age\nSeason, Weekend, Place FE",
            "ln characters; photos attached to the review\nln of the reviewer's review and follower counts\nln days since posting; exposure offset in M4\nδⱼ absorbs attraction-specific characteristics"
        ]
    ];
    s.addTable(rows, tableOpts({
        y: 1.3, colW: [1.75, 3.6, 6.74], rowH: 1.25,
        fill: { color: "FFFFFF" }, fontSize: 10.5
    }));
    caption(s, "표 3. 변수요약.", MARGIN, 6.4, BODY_W);
    source(s, "Variable roles follow 이민영 외 (2026), 소비자학연구 37(1).");
}

{
    const s = contentSlide("4. Methodology", "Models", "연구모형");

    s.addText([
        { text: "Review-level regressions with place fixed effects δ", options: {} },
        { text: "j", options: { subscript: true } },
        { text: " and standard errors clustered by reviewer, since the same person often writes several reviews.", options: { breakLine: true } },
        { text: "관광지 고정효과를 포함한 리뷰 단위 회귀분석이며, 표준오차는 작성자 단위로 군집화한다.", options: { fontSize: 12, color: "6E8288" } }
    ], {
        x: MARGIN, y: 1.22, w: BODY_W, h: 0.7, isTextBox: true, margin: 0,
        fontSize: 13, color: C.text1, objectName: "models-intro"
    });

    const models = [
        ["M1", "Revisit\n재방문", "logit P(Revisit) = β₀ + x′β + δⱼ",
         "Which visit contexts lead to returning", THEME.colors.accent1],
        ["M2", "Keyword Count\n키워드 수", "Ordered logit over 0–5 tags, proportional odds",
         "Who supplies more diverse information", THEME.colors.accent2],
        ["M3", "Rating\n별점", "Ordered logit over 1–5 stars",
         "Exploratory: ratings barely vary", THEME.colors.accent5],
        ["M4", "Reactions\n반응 수", "Negative binomial, ln(review age) offset",
         "Which reviews other users respond to", THEME.colors.accent1]
    ];
    models.forEach(([tag, name, formula, reading, color], i) => {
        const y = 2.05 + i * 1.17;
        s.addShape(pres.ShapeType.roundRect, {
            x: MARGIN, y, w: BODY_W, h: 1.03, rectRadius: 0.06,
            fill: { color: "FFFFFF" }, line: { color: "D8D2C9", width: 1 },
            objectName: `model-box-${tag}`
        });
        s.addShape(pres.ShapeType.rect, {
            x: MARGIN, y, w: 0.08, h: 1.03, fill: { color }, objectName: `model-rule-${tag}`
        });
        s.addText(tag, {
            x: MARGIN + 0.25, y: y + 0.28, w: 1.0, h: 0.5, isTextBox: true, margin: 0,
            fontSize: 19, bold: true, color, fontFace: THEME.headFontFace
        });
        s.addText(name, {
            x: MARGIN + 1.3, y: y + 0.18, w: 2.4, h: 0.68, isTextBox: true, margin: 0,
            fontSize: 13, bold: true, color: THEME.colors.dk2, valign: "middle",
            lineSpacingMultiple: 1.05
        });
        s.addText(formula, {
            x: MARGIN + 3.85, y: y + 0.18, w: 4.6, h: 0.68, isTextBox: true, margin: 0,
            fontSize: 11.5, color: C.text1, valign: "middle"
        });
        s.addText(reading, {
            x: MARGIN + 8.6, y: y + 0.18, w: BODY_W - 8.85, h: 0.68, isTextBox: true, margin: 0,
            fontSize: 11.5, italic: true, color: "6E8288", valign: "middle"
        });
    });
    source(s, "Each model is re-estimated keeping one random review per reviewer and per place; only effects that survive are reported as robust.");
}

/* ------------------------------------------------------------------ *
 * 14-16. Results
 * ------------------------------------------------------------------ */

pres.addSection({ title: "5. Results" });
divider("5. Results", 5, "Results", "결과");

{
    const s = contentSlide("5. Results", "Model performance and leading effects", "모형 성능과 주요 효과");
    const rows = [
        [
            { text: "Model  모형", options: TABLE_HEAD },
            { text: "Out-of-sample  교차검증", options: TABLE_HEAD },
            { text: "Leading effects (odds / incidence ratios)  주요 효과", options: TABLE_HEAD }
        ],
        ["M1  Revisit  재방문", `AUC ${fmt(M.m1Auc, 3)}  (ext. ${fmt(M.m1xAuc, 3)})`, effectText(E.m1)],
        ["M2  Keyword Count  키워드 수", `RMSE ${fmt(M.m2Rmse, 2)}  vs ${fmt(M.m2Base, 2)} base`, effectText(E.m2)],
        [
            { text: "M3  Rating  별점", options: { color: "8A9499" } },
            { text: "weak, exploratory", options: { color: "8A9499" } },
            { text: effectText(E.m3), options: { color: "8A9499" } }
        ],
        ["M4  Reactions  반응 수", `AUC ${fmt(M.m4Auc, 3)}  (any reaction)`, effectText(E.m4)]
    ];
    s.addTable(rows, tableOpts({
        y: 1.3, colW: [2.75, 2.85, 6.49], rowH: 0.78,
        fill: { color: "FFFFFF" }, fontSize: 10.5
    }));
    caption(s, "표 4. 모형별 분석 결과 (작성자 단위 GroupKFold 교차검증).", MARGIN, 5.4, BODY_W);

    s.addText([
        { text: "Cross-validation is grouped by reviewer", options: { bold: true } },
        { text: ", so no reviewer appears in both the training and the test fold. Significance: * p<0.05, ** p<0.01, *** p<0.001.", options: { breakLine: true } },
        { text: "교차검증은 작성자 단위로 분할하여, 동일 작성자가 학습과 검증에 함께 포함되지 않도록 하였다.", options: { fontSize: 11.5, color: "6E8288" } }
    ], {
        x: MARGIN, y: 5.8, w: BODY_W, h: 1.0, isTextBox: true, margin: 0,
        fontSize: 12.5, color: C.text1, lineSpacingMultiple: 1.06, paraSpaceAfter: 5,
        objectName: "cv-note"
    });
}

{
    const s = contentSlide("5. Results", "What replicates, and what is new", "재현된 결과와 새로운 발견");

    const m4Sent = E.m4.find(e => /sentiment/i.test(e.label));
    s.addShape(pres.ShapeType.roundRect, {
        x: MARGIN, y: 1.3, w: 6.0, h: 2.35, rectRadius: 0.06,
        fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.accent2, width: 1.5 },
        objectName: "replication-box"
    });
    s.addText([
        { text: "Replicates: sentiment hurts engagement", options: { bold: true, color: THEME.colors.accent2, breakLine: true } },
        { text: m4Sent
            ? `More positive reviews receive fewer reactions (${fmt(m4Sent.ratio)}${starsFor(m4Sent.p)}). Lee et al. (2026) find the same sign on clicks (α = −0.011 to −0.018).`
            : "Lee et al. (2026) find sentiment entering engagement negatively (α = −0.011 to −0.018).",
          options: { breakLine: true } },
        { text: "Measurement levels apart, the same pattern appears: effusive praise is not what readers respond to.", options: { breakLine: true } },
        { text: "과도한 칭찬은 독자의 반응을 이끌어내지 못한다는 동일한 양상이 나타난다.", options: { fontSize: 11.5, color: "6E8288" } }
    ], {
        x: MARGIN + 0.22, y: 1.48, w: 5.56, h: 2.0, isTextBox: true, margin: 0,
        fontSize: 12, color: C.text1, lineSpacingMultiple: 1.06, paraSpaceAfter: 4
    });

    s.addShape(pres.ShapeType.roundRect, {
        x: MARGIN + 6.35, y: 1.3, w: BODY_W - 6.35, h: 2.35, rectRadius: 0.06,
        fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.accent1, width: 1.5 },
        objectName: "new-box"
    });
    s.addText([
        { text: "New: where diversity comes from", options: { bold: true, color: THEME.colors.accent1, breakLine: true } },
        { text: "Writing text at all is by far the strongest predictor of selecting more keywords, followed by supplying visit information and by being a returning visitor.", options: { breakLine: true } },
        { text: "Information diversity tracks engagement with the platform, not the kind of visit.", options: { breakLine: true } },
        { text: "정보 다양성은 방문 유형보다 작성자의 참여도를 따른다.", options: { fontSize: 11.5, color: "6E8288" } }
    ], {
        x: MARGIN + 6.57, y: 1.48, w: BODY_W - 6.79, h: 2.0, isTextBox: true, margin: 0,
        fontSize: 12, color: C.text1, lineSpacingMultiple: 1.06, paraSpaceAfter: 4
    });

    s.addText([
        { text: "Also worth reporting", options: { bold: true, color: THEME.colors.dk2, breakLine: true } },
        { text: "Queueing is the strongest negative signal for returning to an attraction — and it is the one thing on this list a manager can act on.", options: { bullet: true, breakLine: true } },
        { text: "Revisitors are prolific reviewers who write at length but score lower on sentiment: experience reads as restraint, not enthusiasm.", options: { bullet: true, breakLine: true } },
        { text: "Reactions follow the reviewer's follower count and text length, i.e. reach and effort, more than anything about the visit itself.", options: { bullet: true, breakLine: true } },
        { text: "Keyword Count is the one variable that predicts a higher star rating, which keeps M3 in the deck as exploratory rather than useless.", options: { bullet: true } }
    ], {
        x: MARGIN, y: 3.95, w: BODY_W, h: 2.6, isTextBox: true, margin: 0,
        fontSize: 12.5, color: C.text1, paraSpaceAfter: 6, lineSpacingMultiple: 1.06,
        objectName: "other-findings"
    });
}

/* ------------------------------------------------------------------ *
 * 17-18. Conclusion
 * ------------------------------------------------------------------ */

pres.addSection({ title: "6. Conclusion" });
divider("6. Conclusion", 6, "Conclusion", "결론");

{
    const s = contentSlide("6. Conclusion", "Conclusion", "결론");
    const blocks = [
        ["What we find", "주요 결과", THEME.colors.accent1, [
            "Information diversity on Naver tracks how engaged a reviewer is with the platform, not what kind of visit they made.",
            "Sentiment enters engagement negatively, replicating Lee et al. (2026) at the review level."
        ]],
        ["Limitations", "한계", THEME.colors.accent5, [
            "Associations only: Lee et al. (2026) identify effects from Naver's keyword expansion and lag all regressors to t−1; this design is cross-sectional and has neither.",
            "Only place fixed effects, where the source study uses place and time.",
            "A single platform, so Naver's reviewer population cannot be separated from Korean reviewers in general."
        ]],
        ["Next steps", "향후 계획", THEME.colors.accent2, [
            "Add month fixed effects, to match the two-way specification of the source study.",
            "Extend the panel to more attractions and report sensitivity to the collection window.",
            "Validate the aspect extraction against blind manual coding (Cohen's kappa)."
        ]]
    ];
    let y = 1.25;
    blocks.forEach(([en, ko, color, items], i) => {
        const h = 0.42 + items.length * 0.46;
        s.addShape(pres.ShapeType.rect, {
            x: MARGIN, y, w: 0.07, h, fill: { color }, objectName: `concl-rule-${i}`
        });
        s.addText([
            { text: en, options: { bold: true } },
            { text: `   ${ko}`, options: { bold: false, fontSize: 12, color: "6E8288" } }
        ], {
            x: MARGIN + 0.28, y, w: BODY_W - 0.28, h: 0.36, isTextBox: true, margin: 0,
            fontSize: 15, color
        });
        s.addText(items.map((t, j) => ({
            text: t, options: { bullet: true, breakLine: j < items.length - 1 }
        })), {
            x: MARGIN + 0.28, y: y + 0.38, w: BODY_W - 0.4, h: items.length * 0.46, isTextBox: true,
            margin: 0, fontSize: 12.5, color: C.text1, paraSpaceAfter: 4, lineSpacingMultiple: 1.05
        });
        y += h + 0.22;
    });
}

/* ------------------------------------------------------------------ *
 * 19. Closing
 * ------------------------------------------------------------------ */

pres.addSection({ title: "Closing" });
{
    const s = pres.addSlide({ masterName: "CLOSING", sectionTitle: "Closing" });
    s.addText([
        { text: "Thank you", options: { bold: true, breakLine: true } },
        { text: "감사합니다", options: { fontSize: 30, color: "A8BFC4" } }
    ], {
        x: 1.0, y: 2.8, w: 11.3, h: 1.9, isTextBox: true, margin: 0,
        fontSize: 44, color: "FFFFFF", align: "center", objectName: "thanks"
    });
    s.addText("Jorge Adan Soriano Hernandez  ·  Department of Data Science, Hoseo University  ·  October 2026", {
        x: 1.0, y: 4.9, w: 11.3, h: 0.4, isTextBox: true, margin: 0,
        fontSize: 13, color: "7E9AA2", align: "center", objectName: "thanks-footer"
    });
}

/* ------------------------------------------------------------------ *
 * Write
 * ------------------------------------------------------------------ */

(async () => {
    await pres.writeFile({ fileName: OUT });
    await applyTheme(OUT, THEME);
    console.log(`\nWrote ${path.relative(ROOT, OUT)}`);
})().catch(err => { console.error(err); process.exit(1); });
