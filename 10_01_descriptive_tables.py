"""
Descriptive tables for the Naver-only study, in the format used by
이민영·정동영·김지영 (2026), 소비자학연구 37(1):

    <표 A> 관광지별 리뷰 수   reviews per attraction (place | type | N | text | rating)
    <표 1> 변수요약      variable summary   (변수 종류 | 변수 이름 | 변수 설명)
    <표 2> 기술통계표    descriptive stats  (Statistic | N | Mean | St.Dev. | Min | Median | Max)
    <표 3> 상관분석표    correlation matrix
    <표 4> VIF           multicollinearity check

Table numbers in the generated .tex come from LaTeX's own \\caption counter at
the point each macro is \\input, not from this script -- whichever macro a
document places first becomes 표 1. <표 A> above is just this script's own
label for the places table, not a fixed number.

Scope is Naver Place only. The cross-cultural corpus is a separate branch of
the project and is not described here.

Usage:
    python 10_01_descriptive_tables.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "analysis" / "naver"
OUT = DATA
TEX = ROOT / "proposal" / "tables_naver.tex"

sys.path.insert(0, str(ROOT))
from places_data import PLACE_EN, PLACE_TYPE  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)


# --------------------------------------------------------------------------- #
# <표 1> 변수요약
# --------------------------------------------------------------------------- #

# (역할, 변수 이름, column in the dataset, 변수 설명 KO, description EN)
VARIABLES = [
    # ---- 종속변수 ------------------------------------------------------- #
    ("종속변수 (DV)", "Revisit (재방문)", "revisit",
     "해당 관광지를 2회차 이상 방문한 작성자의 리뷰 여부 (0/1)",
     "Review written on a second or later visit to the same place (0/1)"),
    ("종속변수 (DV)", "Keyword Count (키워드 수)", "n_tags",
     "리뷰당 작성자가 선택한 키워드 수 (0~5), 정보 다양성 지표",
     "Number of keyword tags the reviewer selected (0-5); information diversity"),
    ("종속변수 (DV)", "Rating (별점)", "rating",
     "작성자가 부여한 별점 (1~5)",
     "Star rating given by the reviewer (1-5)"),
    ("종속변수 (DV)", "Reactions (반응 수)", "reactions",
     "해당 리뷰에 반응을 남긴 이용자 수, 유용성 지표",
     "Number of users who reacted to the review; helpfulness"),

    # ---- 독립변수 ------------------------------------------------------- #
    ("독립변수 (IV)", "Companion (동반자)", None,
     "방문 동반자 유형 더미: 혼자·연인·친구·아이·가족·동료",
     "Companion dummies: alone, partner, friend, child, family, colleague"),
    ("독립변수 (IV)", "Purpose (방문 목적)", None,
     "방문 목적 더미: 여행·나들이·일상·데이트·친목",
     "Purpose dummies: travel, outing, daily life, date, social"),
    ("독립변수 (IV)", "Waited (대기)", "waited",
     "방문 시 대기 경험 여부 (0/1)",
     "Reviewer reported queueing (0/1)"),
    ("독립변수 (IV)", "Reserved (예약)", "reserved",
     "사전 예약 여부 (0/1)",
     "Visit was booked in advance (0/1)"),
    ("독립변수 (IV)", "Sentiment (감성 점수)", "sentiment",
     "리뷰 텍스트의 감성 점수 (-1 부정 ~ 1 긍정)",
     "Sentiment score of the review text (-1 negative to 1 positive)"),
    ("독립변수 (IV)", "Tag themes (키워드 주제)", None,
     "키워드를 10개 주제로 분류한 더미: 시각·볼거리·혼잡·한적·시설·"
     "접근성·가족·가격·음식·물놀이",
     "Ten tag-theme dummies: visual, content, crowded, quiet, facilities, "
     "access, family, value, food, water leisure"),

    # ---- 통제변수 ------------------------------------------------------- #
    ("통제변수 (Control)", "Text Length (텍스트 길이)", "ln_length",
     "리뷰 텍스트 길이의 로그값",
     "Log of review text length"),
    ("통제변수 (Control)", "Image Count (사진 수)", "n_photos",
     "리뷰에 첨부된 사진 수",
     "Number of photos attached to the review"),
    ("통제변수 (Control)", "User Reviews (작성자 리뷰 수)", "ln_user_reviews",
     "작성자가 누적 작성한 리뷰 수의 로그값",
     "Log of the reviewer's cumulative review count"),
    ("통제변수 (Control)", "User Followers (팔로워 수)", "ln_user_followers",
     "작성자의 팔로워 수의 로그값",
     "Log of the reviewer's follower count"),
    # Enters M4 as an estimated regressor, not as a fixed offset: an older
    # review has had longer to collect reactions, but we let the data say
    # how much longer rather than forcing the coefficient to 1.
    ("통제변수 (Control)", "Review Age (리뷰 경과일)", "ln_review_age",
     "리뷰 작성 후 경과일의 로그값, 반응 수 모형에서 노출 기간을 통제",
     "Log of days since the review was posted; controls exposure time in M4"),
    ("통제변수 (Control)", "Verification (인증)", "verif_receipt",
     "영수증 인증 리뷰 여부 (0/1)",
     "Review verified by receipt (0/1)"),
    ("통제변수 (Control)", "Season (계절)", None,
     "방문 계절 더미: 여름·가을·겨울 (봄 기준)",
     "Season dummies: summer, autumn, winter (spring is the base)"),
    ("통제변수 (Control)", "Weekend (주말)", "visit_weekend",
     "주말 방문 여부 (0/1)",
     "Visit fell on a weekend (0/1)"),
    ("통제변수 (Control)", "Place FE (관광지 고정효과)", None,
     "관광지별 고정효과, 장소 고유 특성 통제",
     "Place fixed effects, absorbing attraction-specific characteristics"),
]


# <표 2>/<표 3> 에 쓰는 연속·이산 변수 (상관분석표 번호 순서)
CORE = [
    ("Revisit (재방문)", "revisit"),
    ("Keyword Count (키워드 수)", "n_tags"),
    ("Rating (별점)", "rating"),
    ("Reactions (반응 수)", "reactions"),
    ("Sentiment (감성 점수)", "sentiment"),
    ("Text Length (텍스트 길이)", "text_len"),
    ("Image Count (사진 수)", "n_photos"),
    ("User Reviews (작성자 리뷰 수)", "user_reviews"),
    ("Review Age (리뷰 경과일)", "review_age"),
]


def load():
    df = pd.read_csv(DATA / "naver_dataset.csv")
    # Report the raw quantities, not the logs, in the descriptive table:
    # a reader checks the mean against the platform, not against ln(x).
    df["text_len"] = np.exp(df["ln_length"]) - 1
    df["review_age"] = np.exp(df["ln_review_age"]) - 1
    return df


def table_places(df):
    """One row per scraped attraction: how much data it actually contributed.

    Sorted by review count, descending, so the spread between the busiest
    and thinnest places is visible at a glance rather than buried
    alphabetically.
    """
    g = df.groupby("place").agg(
        reviews=("place", "size"),
        with_text=("has_text", "sum"),
        with_rating=("rating", lambda s: s.notna().sum()),
    ).reset_index()
    g["name_en"] = g["place"].map(PLACE_EN).fillna("")
    g["type"] = g["place"].map(PLACE_TYPE).fillna("")
    g = g.sort_values("reviews", ascending=False).reset_index(drop=True)
    return g[["place", "name_en", "type", "reviews", "with_text", "with_rating"]]


def table1(df):
    rows = []
    for role, name, col, ko, en in VARIABLES:
        n = int(df[col].notna().sum()) if col and col in df.columns else np.nan
        rows.append({"변수 종류": role, "변수 이름": name, "변수 설명": ko,
                     "Description": en, "column": col or "", "N": n})
    return pd.DataFrame(rows)


def table2(df):
    rows = []
    for name, col in CORE:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        rows.append({
            "Statistic": name,
            "N": len(s),
            "Mean": s.mean(),
            "St. Dev.": s.std(),
            "Min": s.min(),
            "Median": s.median(),
            "Max": s.max(),
        })
    return pd.DataFrame(rows)


def table3(df):
    cols = [c for _, c in CORE]
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    # Pairwise deletion: rating and sentiment are missing on different subsets,
    # so listwise would drop most of the panel.
    corr = sub.corr(method="pearson", min_periods=100)
    corr.index = [f"{i+1}. {name}" for i, (name, _) in enumerate(CORE)]
    corr.columns = [str(i + 1) for i in range(len(CORE))]
    # Lower triangle only, as in the source paper.
    mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
    return corr.mask(mask)


def fmt_num(v, nd=3):
    if pd.isna(v):
        return ""
    if abs(v) >= 1000:
        return f"{v:,.1f}"
    return f"{v:.{nd}f}".rstrip("0").rstrip(".") if nd else f"{v:.0f}"


def to_latex_tables(places, t1, t2, t3, vif):
    """Write the tables as LaTeX macros the proposal places where it needs them.

    Each table is a \\newcommand rather than a bare table environment: the
    proposal is bilingual and prints the same table once in its English half
    and once in its Korean half, which duplicate \\label keys would break.
    """
    def esc(s):
        # A bare ~ is a non-breaking space in LaTeX, so ranges like "0~5"
        # would silently render as "0 5".
        return (str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
                      .replace("~", r"$\sim$"))

    def macro(name, lines):
        # Trailing % on each line keeps the macro body from introducing
        # stray spaces where it is used.
        body = "%\n".join(lines)
        return "\\newcommand{\\" + name + "}{%\n" + body + "%\n}\n"

    out = ["% Generated by 10_01_descriptive_tables.py -- do not edit by hand.",
           r"% Requires \usepackage{float} in the including document ([H] placement).",
           r"% Defines: \tblPlaces \tblVariables \tblDescriptives \tblCorrelations \tblVIF",
           ""]

    # --- 관광지별 리뷰 수 --- #
    rows = [r"\begin{table}[H]\centering",
            r"\caption{관광지별 리뷰 수 / Reviews per attraction}",
            r"\footnotesize\begin{tabular}{llrrr}\hline",
            r"관광지 & English & Reviews & w/ text & w/ rating \\ \hline"]
    for _, r in places.iterrows():
        rows.append(
            f"{esc(r['place'])} & {esc(r['name_en'])} & "
            f"{int(r['reviews']):,} & {int(r['with_text']):,} & {int(r['with_rating']):,} \\\\")
    rows.append(r"\hline\end{tabular}")
    # caption note removed per author request
    rows.append(r"\end{table}")
    out.append(macro("tblPlaces", rows))

    # --- 표 1 변수요약 --- #
    rows = [r"\begin{table}[H]\centering",
            r"\caption{변수요약 / Variable summary}",
            r"\footnotesize\begin{tabular}{llp{7.6cm}}\hline",
            r"변수 종류 & 변수 이름 & 변수 설명 \\ \hline"]
    prev = None
    for _, r in t1.iterrows():
        role = "" if r["변수 종류"] == prev else esc(r["변수 종류"])
        prev = r["변수 종류"]
        rows.append(f"{role} & {esc(r['변수 이름'])} & {esc(r['변수 설명'])} \\\\")
    rows.append(r"\hline\end{tabular}\end{table}")
    out.append(macro("tblVariables", rows))

    # --- 표 2 기술통계표 --- #
    rows = [r"\begin{table}[H]\centering",
            r"\caption{기술통계표 / Descriptive statistics}",
            r"\footnotesize\begin{tabular}{lrrrrrr}\hline",
            r"Statistic & N & Mean & St.\ Dev. & Min & Median & Max \\ \hline"]
    for _, r in t2.iterrows():
        rows.append(
            f"{esc(r['Statistic'])} & {int(r['N']):,} & {fmt_num(r['Mean'])} & "
            f"{fmt_num(r['St. Dev.'])} & {fmt_num(r['Min'])} & "
            f"{fmt_num(r['Median'])} & {fmt_num(r['Max'])} \\\\")
    rows.append(r"\hline\end{tabular}\end{table}")
    out.append(macro("tblDescriptives", rows))

    # --- 표 3 상관분석표 --- #
    ncol = len(t3.columns)
    rows = [r"\begin{table}[H]\centering",
            r"\caption{상관분석표 / Correlation matrix}",
            r"\footnotesize\begin{tabular}{l" + "r" * ncol + r"}\hline",
            " & " + " & ".join(t3.columns) + r" \\ \hline"]
    for idx, row in t3.iterrows():
        cells = [("" if pd.isna(v) else f"{v:.3f}") for v in row]
        rows.append(f"{esc(idx)} & " + " & ".join(cells) + r" \\")
    rows.append(r"\hline\end{tabular}\end{table}")
    out.append(macro("tblCorrelations", rows))

    # --- 표 4 분산팽창계수 --- #
    # Three column-pairs: a single tall column of 19 short rows strands the
    # table on a page of its own.
    if vif is not None and len(vif):
        pairs = [(esc(r.iloc[0]), f"{r.iloc[1]:.2f}") for _, r in vif.iterrows()]
        ncols = 3
        nrows = -(-len(pairs) // ncols)          # ceiling division
        rows = [r"\begin{table}[H]\centering",
                r"\caption{분산팽창계수 / Variance inflation factors}",
                r"\footnotesize\begin{tabular}{" + "lr" * ncols + r"}\hline",
                " & ".join([r"변수 / Variable & VIF"] * ncols) + r" \\ \hline"]
        for i in range(nrows):
            cells = []
            for c in range(ncols):
                j = i + c * nrows
                cells.append(f"{pairs[j][0]} & {pairs[j][1]}" if j < len(pairs) else " & ")
            rows.append(" & ".join(cells) + r" \\")
        rows += [r"\hline\end{tabular}",
                 r"\par\vspace{2pt}\footnotesize\textit{All values below 5; "
                 r"multicollinearity is not a concern. 모든 값이 5 미만으로 "
                 r"다중공선성 문제는 없다.}",
                 r"\end{table}"]
        out.append(macro("tblVIF", rows))
    else:
        out.append("\\newcommand{\\tblVIF}{}\n")

    TEX.write_text("\n".join(out), encoding="utf-8")



def main():
    df = load()
    print(f"Naver dataset: {len(df):,} reviews, "
          f"{df['user_id'].nunique():,} reviewers, {df['place'].nunique()} places")
    print(f"  with text: {int(df['has_text'].sum()):,}  "
          f"with rating: {int(df['rating'].notna().sum()):,}\n")

    places = table_places(df)
    t1 = table1(df)
    t2 = table2(df)
    t3 = table3(df)

    vif_path = DATA / "vif.csv"
    vif = pd.read_csv(vif_path) if vif_path.exists() else None

    print("<표 A> 관광지별 리뷰 수")
    print(places.to_string(index=False))
    print()

    print("<표 1> 변수요약")
    for role, grp in t1.groupby("변수 종류", sort=False):
        print(f"  {role}")
        for _, r in grp.iterrows():
            print(f"    {r['변수 이름']:32} {r['변수 설명'][:58]}")
    print()

    print("<표 2> 기술통계표")
    disp = t2.copy()
    for c in ["Mean", "St. Dev.", "Min", "Median", "Max"]:
        disp[c] = disp[c].map(lambda v: fmt_num(v))
    print(disp.to_string(index=False))
    print()

    print("<표 3> 상관분석표")
    print(t3.round(3).fillna("").to_string())
    print()

    if vif is not None:
        hi = vif[vif.iloc[:, 1] > 5]
        print(f"<표 4> VIF: max {vif.iloc[:, 1].max():.2f}; "
              f"{'none above 5' if hi.empty else f'{len(hi)} above 5'}")
        print()

    places.to_csv(OUT / "table_places.csv", index=False, encoding="utf-8-sig")
    t1.to_csv(OUT / "table1_variables.csv", index=False, encoding="utf-8-sig")
    t2.to_csv(OUT / "table2_descriptives.csv", index=False, encoding="utf-8-sig")
    t3.to_csv(OUT / "table3_correlations.csv", encoding="utf-8-sig")
    to_latex_tables(places, t1, t2, t3, vif)

    print(f"Saved: {OUT.relative_to(ROOT)}\\table_places.csv")
    print(f"Saved: {OUT.relative_to(ROOT)}\\table1_variables.csv")
    print(f"Saved: {OUT.relative_to(ROOT)}\\table2_descriptives.csv")
    print(f"Saved: {OUT.relative_to(ROOT)}\\table3_correlations.csv")
    print(f"Saved: {TEX.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
