"""
rewrite_talk.py
Replace the talk portion of script1014.tex (lines 55-224) with 15 sections
aligned to the current 22-slide presentation. Keeps preamble (lines 1-54)
and glossary + Q&A (line 225 onward) intact.

Run (base env):  python rewrite_talk.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

PATH = "script1014.tex"

NEW_TALK = r"""% Slide-by-slide talk script v3, aligned with presentation_build.pptx (22 slides).
% Target duration: ~15 minutes. Section N below = what to say while slide S is on screen.

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 4 — Introduction / Motivation
% ─────────────────────────────────────────────────────────────────────────────
\sechead{1. Introduction (Slide 4)}{1. 서론 (슬라이드 4)}
\bilingual{%
  \sent{Online reviews drive travel decisions. Before visiting an attraction, Korean travelers routinely check Naver Place for reviews, photos and reactions.}
  \sent{Lee et al.\ (2026) show that information diversity---how distinct the words across reviews are---predicts business performance separately from review volume, at the business-week level.}
  \sent{But at that aggregate level, we don't see \textbf{who} supplies diversity or under \textbf{what conditions}. This study takes the construct down to the individual review, combined with Naver's structured visit context: companion, purpose, wait, reservation.}
}{%
  \sent{온라인 리뷰는 여행 결정을 좌우한다. 관광지 방문 전 한국인들은 네이버 플레이스의 리뷰·사진·반응을 확인한다.}
  \sent{이민영 외(2026)는 리뷰 정보 다양성이 리뷰 양과 독립적으로 사업체 성과를 예측함을 사업체-주 단위에서 입증했다.}
  \sent{하지만 그 집계 수준에서는 다양성을 \textbf{누가}, \textbf{어떤 조건에서} 만드는지 보이지 않는다. 본 연구는 이를 개별 리뷰 수준으로 가져오고, 네이버의 구조화된 방문 맥락(동반자·목적·대기·예약)과 결합한다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 5 — Research Questions
% ─────────────────────────────────────────────────────────────────────────────
\sechead{2. Research Questions (Slide 5)}{2. 연구 질문 (슬라이드 5)}
\bilingual{%
  \sent{We ask four questions. First: which visit contexts predict returning to the same attraction? Second: which reviewers and visit contexts produce more diverse keywords?}
  \sent{Third: which reviews receive reader reactions, and does sentiment help or hurt? Fourth: which aspects of the visit do different reviewer groups discuss, and does content predict engagement beyond overall sentiment?}
}{%
  \sent{네 가지 질문을 제기한다. 첫째, 어떤 방문 맥락이 재방문을 예측하는가? 둘째, 어떤 작성자와 방문 맥락이 더 많은 키워드를 생성하는가?}
  \sent{셋째, 어떤 리뷰가 반응을 받으며 감성은 도움이 되는가? 넷째, 어떤 방문 측면을 작성자 그룹별로 언급하며, 내용이 전반 감성 이상의 몰입을 예측하는가?}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 7 — Information Diversity (Lee et al. 2026)
% ─────────────────────────────────────────────────────────────────────────────
\sechead{3. Information Diversity (Slide 7)}{3. 정보 다양성 (슬라이드 7)}
\bilingual{%
  \sent{Information diversity measures how many distinct keywords a review carries, independent of its length or sentiment. It captures variety, not volume.}
  \sent{Lee et al.\ show that higher diversity predicts business performance separately from review quantity. Their 0--5 keyword scale matches Naver's cap, so we use exactly the same instrument but at the review level.}
}{%
  \sent{정보 다양성은 리뷰 길이나 감성과 무관하게 리뷰가 담은 서로 다른 키워드 수를 측정한다. 양이 아닌 다양성을 포착한다.}
  \sent{이민영 외는 다양성이 리뷰 양과 독립적으로 사업체 성과를 예측함을 보였다. 그들의 0--5 키워드 척도는 네이버의 상한과 일치하므로, 동일 도구를 리뷰 수준에서 사용한다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 8 — Review Helpfulness (Wang et al. 2025)
% ─────────────────────────────────────────────────────────────────────────────
\sechead{4. Review Helpfulness (Slide 8)}{4. 리뷰 유용성 (슬라이드 8)}
\bilingual{%
  \sent{A related strand asks what makes a single review useful to readers. Wang et al.\ (2025) measure helpfulness through content dissimilarity---how distinct a review's wording is from surrounding reviews---on 1.6 million Amazon reviews.}
  \sent{Their framing treats a review as a single bag of words. The visit context and specific aspects it discusses are not observed. We use reader reactions as a behavioural proxy for helpfulness: a review enough people clicked a reaction on.}
}{%
  \sent{관련 연구는 개별 리뷰의 유용성을 묻는다. 왕 외(2025)는 유용성을 콘텐츠 비유사성---어휘가 주변 리뷰와 얼마나 다른가---으로 측정했다.}
  \sent{이들은 리뷰를 단어의 집합으로 다룬다. 방문 맥락이나 측면은 관찰되지 않는다. 본 연구는 이용자 반응을 유용성의 행동적 대리 지표로 사용한다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 9 — Research Gap + 3 Contributions
% ─────────────────────────────────────────────────────────────────────────────
\sechead{5. Research Gap and Contributions (Slide 9)}{5. 연구 공백 및 기여 (슬라이드 9)}
\bilingual{%
  \sent{Prior work observes performance at the aggregate level but doesn't see what each review discusses or the visit context behind it.}
  \sent{We make three contributions. First, review-level replication of the diversity--performance link Lee et al.\ establish at the business-week level.}
  \sent{Second, platform-structured visit context---companion, purpose, wait, reservation---as a joint predictor set that few other review ecosystems record.}
  \sent{Third, aspect-level analysis cross-cut with visit context---a combination the reference studies cannot build because they lack one or both data types.}
}{%
  \sent{선행 연구는 집계 수준에서 성과를 관찰하지만 각 리뷰 내용과 방문 맥락은 보지 못한다.}
  \sent{세 가지 기여를 한다. 첫째, 이민영 외가 사업체-주 단위에서 입증한 다양성-성과 관계의 리뷰 수준 재현.}
  \sent{둘째, 네이버의 구조화된 방문 맥락(동반자·목적·대기·예약)의 통합 예측 변수 세트 활용.}
  \sent{셋째, 방문 맥락과 교차한 측면 수준 분석---참조 연구가 구성할 수 없는 조합.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 11 — Data
% ─────────────────────────────────────────────────────────────────────────────
\sechead{6. Data (Slide 11)}{6. 데이터 (슬라이드 11)}
\bilingual{%
  \sent{The dataset has 14,401 Naver Place reviews from 29 Korean tourist attractions, written by 8,276 reviewers; 11,165 include text.}
  \sent{We selected attractions by crossing Yanolja's \textit{Korea's Top 500} ranking with Korea Tourism Organization visitor volume, inside typological strata: palaces, hanok villages, markets, parks, museums, modern landmarks.}
  \sent{Seoul has 25 attractions, Busan has 4. The unit of analysis is a review \textit{i} at place \textit{j}, not the business-week.}
}{%
  \sent{데이터셋은 한국 관광지 29곳의 네이버 플레이스 리뷰 14,401건이며, 작성자 8,276명이다. 11,165건에 텍스트가 포함된다.}
  \sent{관광지는 야놀자 \textit{대한민국 Top 500}과 한국관광공사 방문자 지표를 교차하여 유형별 층위(궁궐·한옥마을·시장·공원·박물관·현대 랜드마크)에서 선정했다.}
  \sent{서울 25곳, 부산 4곳. 분석 단위는 관광지 \textit{j}의 리뷰 \textit{i}이며, 사업체-주 단위가 아니다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 12 — Research Framework
% ─────────────────────────────────────────────────────────────────────────────
\sechead{7. Research Framework (Slide 12)}{7. 연구 프레임워크 (슬라이드 12)}
\bilingual{%
  \sent{This slide gives a visual overview of the pipeline: data acquisition feeds variable construction, which feeds the four models.}
  \sent{The three blocks---data, variables, models---are the structure of the methodology section. Everything that follows plugs into this flow.}
}{%
  \sent{이 슬라이드는 파이프라인의 시각적 개요다: 데이터 수집이 변수 구축으로 이어지고, 네 가지 모형으로 연결된다.}
  \sent{세 블록---데이터·변수·모형---은 방법론 섹션의 구조다. 이후의 모든 내용이 이 흐름에 연결된다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 13 — Variables
% ─────────────────────────────────────────────────────────────────────────────
\sechead{8. Variables (Slide 13)}{8. 변수 (슬라이드 13)}
\bilingual{%
  \sent{Four dependent variables: Revisit (binary), Keyword Count (ordinal 0--5), Rating (ordinal 1--5, exploratory), and Reactions (count, the helpfulness proxy).}
  \sent{Independent variables are the four visit-context dimensions plus sentiment, and---in the aspect-level analysis only---the six aspect dummies.}
  \sent{Controls separate behavioural effects from reviewer-identity artefacts: text length, image count, reviewer history, follower count, review age, verification, season, weekend, and place fixed effects.}
}{%
  \sent{네 가지 종속변수: 재방문(이진), 키워드 수(순서형 0--5), 별점(순서형 1--5, 탐색적), 반응 수(계수, 유용성 대리 지표).}
  \sent{독립변수는 네 가지 방문 맥락 차원과 감성, 그리고 측면 수준 분석에서는 여섯 가지 측면 더미.}
  \sent{통제변수는 텍스트 길이, 사진 수, 작성자 리뷰 수, 팔로워 수, 리뷰 경과일, 인증, 계절, 주말, 그리고 관광지 고정효과.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 14 — Models (equations)
% ─────────────────────────────────────────────────────────────────────────────
\sechead{9. Models (Slide 14)}{9. 모형 (슬라이드 14)}
\bilingual{%
  \sent{We estimate four models, each matching the measurement scale of its outcome.}
  \sent{M1 is logistic on binary revisit. M2 is ordered logistic on keyword count. M3 is ordered logistic on rating, reported as exploratory. M4 is negative binomial on reactions with log review-age as an offset.}
  \sent{Keyword Count is modelled as ordinal, not count: its range is capped at five by Naver's design, not generated by a Poisson process. All models include place fixed effects and standard errors clustered by reviewer.}
}{%
  \sent{종속변수의 측정 척도에 맞춰 네 가지 모형을 추정한다.}
  \sent{M1은 이진 재방문에 대한 로지스틱. M2는 키워드 수에 대한 순서형 로지스틱. M3은 별점에 대한 순서형 로지스틱(탐색적). M4는 반응 수에 대한 음이항, 로그 리뷰 경과일을 오프셋으로 사용.}
  \sent{키워드 수는 \textbf{순서형}으로 모델링한다. 상한이 플랫폼 설계상 5로 고정되어 있어 포아송 과정이 아니다. 모든 모형은 관광지 고정효과를 포함하며, 표준오차는 작성자 단위로 클러스터링한다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 15 — Variable-to-Model Mapping
% ─────────────────────────────────────────────────────────────────────────────
\sechead{10. Variable-to-Model Mapping (Slide 15)}{10. 변수-모형 매핑 (슬라이드 15)}
\bilingual{%
  \sent{This table shows how each variable enters each model. Rows are variables, columns are the four models.}
  \sent{Y marks the dependent variable in that model. $\beta_k$ denotes a coefficient in the regressor vector. $\delta_j$ denotes place fixed effects. $\gamma$ marks the exposure offset in M4.}
  \sent{Reading across any row answers: in which models does this variable appear, and with what role?}
}{%
  \sent{이 표는 각 변수가 각 모형에 어떻게 들어가는지 보여준다. 행은 변수, 열은 네 가지 모형.}
  \sent{Y는 해당 모형의 종속변수. $\beta_k$는 회귀변수 벡터의 계수. $\delta_j$는 관광지 고정효과. $\gamma$는 M4의 노출 오프셋.}
  \sent{행을 따라 읽으면: 이 변수가 어떤 모형에, 어떤 역할로 포함되는가?}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 17 — Main findings M1-M4
% ─────────────────────────────────────────────────────────────────────────────
\sechead{11. Main findings M1--M4 (Slide 17)}{11. 주요 결과 M1--M4 (슬라이드 17)}
\bilingual{%
  \sent{In M1, the strongest predictors of revisit are reviewer history (OR 1.52) and visiting alone (OR 1.68). Queueing cuts the odds by half (OR 0.51), and visiting on a travel-purpose trip reduces them (OR 0.56).}
  \sent{In M2, writing text quadruples keyword count odds (OR 4.02); providing visit info multiplies by 2.5; revisitors tag more. Diversity comes from reviewer engagement with the platform, not from visit type.}
  \sent{M3 on rating is exploratory because ratings barely vary (74\% five-star). In M4, follower count nearly doubles reaction incidence (IRR 1.97), text length multiplies by 1.64, and sentiment enters \textbf{negatively} (IRR 0.77)---more positive text receives fewer reactions, replicating Lee et al.\ at the review level.}
}{%
  \sent{M1에서 재방문의 가장 강한 예측 변수는 작성자 리뷰 이력(OR 1.52)과 혼자 방문(OR 1.68)이다. 대기는 승산을 절반으로(OR 0.51), 여행 목적 방문은 OR 0.56.}
  \sent{M2에서 텍스트 작성은 키워드 수 승산을 4배로(OR 4.02); 방문 정보 제공은 2.5배. 재방문자도 더 많은 키워드를 선택한다. 다양성은 방문 유형이 아닌 작성자의 플랫폼 참여에서 나온다.}
  \sent{M3(별점)은 변동이 작아 탐색적으로만 보고한다(74\%가 5점). M4에서 팔로워 수는 반응 발생률을 거의 2배로(IRR 1.97), 텍스트 길이는 1.64배 높인다. 감성은 \textbf{부정적으로} 작용한다(IRR 0.77)---긍정적 텍스트일수록 반응이 적다. 이는 이민영 외의 결과를 리뷰 수준에서 재현한다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 18 — Aspect Based Sentiment Analysis pipeline
% ─────────────────────────────────────────────────────────────────────────────
\sechead{12. Aspect Based Sentiment Analysis pipeline (Slide 18)}{12. ABSA 파이프라인 (슬라이드 18)}
\bilingual{%
  \sent{For the aspect-level analysis, we first defined \textbf{what to measure} before measuring. From tourism and hospitality literature---SERVQUAL (Parasuraman et al.\ 1988), Chang (2021), Ko et al.\ (2018)---we proposed six aspects a priori.}
  \sent{To ground that choice empirically, we ran two unsupervised topic methods on the corpus: LDA at optimal $K = 6$ and BERTopic with $K = 15$. Five of six aspects emerge as distinct topics; crowding is kept because it is a polarity-dominated dimension (18\% of mentions are negative, the highest).}
  \sent{With the aspects validated, we used an LLM---Qwen2.5-7B in 4-bit quantization---to label each of 11,164 reviews on the six axes with polarity. Then six logistic regressions: mentions-aspect as a function of visit context, controls, and place fixed effects.}
}{%
  \sent{측면 수준 분석을 위해, 측정 전에 \textbf{무엇을 측정할지}부터 정의했다. 관광·호텔 문헌(SERVQUAL---Parasuraman 외 1988; Chang 2021; Ko 외 2018)에서 여섯 측면을 사전 지정했다.}
  \sent{이 선택을 경험적으로 검증하기 위해 코퍼스에 두 가지 비지도 토픽 방법을 적용했다: LDA(최적 $K = 6$), BERTopic($K = 15$). 여섯 측면 중 다섯이 뚜렷한 토픽으로 나타난다. 혼잡은 극성 중심 차원이므로 유지(언급의 18\%가 부정, 모든 측면 중 최고).}
  \sent{검증된 여섯 측면으로 LLM(Qwen2.5-7B 4-bit)을 사용해 11,164건 각각을 여섯 축에 극성으로 라벨링. 이후 측면 언급을 종속변수로 하는 여섯 로지스틱 회귀를 실행했다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 19 — Aspect-level results
% ─────────────────────────────────────────────────────────────────────────────
\sechead{13. Aspect-level analysis (Slide 19)}{13. 측면 수준 분석 결과 (슬라이드 19)}
\bilingual{%
  \sent{The bar chart on the right shows how often each aspect is mentioned: visual leads at 64\%, historical at 50\%, service at 27\%, down to food at 7\%.}
  \sent{The matrix on the left shows \textbf{who mentions what}. Four patterns stand out. First, visits with children raise mentions in three aspects---historical, accessibility, service---so children anchor narrative-rich reviews.}
  \sent{Second, service friction splits two ways: queueing more than doubles crowding mentions (OR 2.13), while reservations cut crowding (OR 0.69) and more than double service mentions (OR 2.39). Third, date-purpose visits raise food mentions by 51\%; alone visits lower them.}
  \sent{On engagement, no aspect dummy reaches $p<.05$ after reviewer controls. Reader reactions on Naver Place are driven by \textbf{who writes}---follower count, revisitor status, text length---not by \textbf{what the review talks about}.}
}{%
  \sent{오른쪽 막대 차트는 각 측면이 얼마나 자주 언급되는지 보여준다: 시각 64\%, 역사 50\%, 서비스 27\%, 음식은 7\%.}
  \sent{왼쪽 매트릭스는 \textbf{누가 무엇을 언급하는지} 보여준다. 네 가지 패턴. 첫째, 아이와 방문은 세 측면(역사·접근성·서비스)에서 언급을 늘린다.}
  \sent{둘째, 서비스 마찰은 두 방향으로 분기한다: 대기는 혼잡 언급을 두 배 이상(OR 2.13), 예약은 혼잡을 줄이고(OR 0.69) 서비스 언급을 두 배 이상 높인다(OR 2.39). 셋째, 데이트 방문은 음식 언급을 51\% 상승시키고, 혼자 방문은 감소시킨다.}
  \sent{몰입에 대해서는 작성자 통제 후 어떠한 측면도 $p<.05$에 도달하지 않는다. 네이버 플레이스의 반응은 \textbf{누가 쓰는가}---팔로워 수, 재방문 여부, 텍스트 길이---에 의해 좌우되지, \textbf{리뷰 내용}에 의해 좌우되지 않는다.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 21 — Conclusions, Implications and Limitations
% ─────────────────────────────────────────────────────────────────────────────
\sechead{14. Conclusions, Implications and Limitations (Slide 21)}{14. 결론, 시사점, 한계 (슬라이드 21)}
\bilingual{%
  \sent{To summarize. RQ1: queueing is the single strongest negative signal for return and the only one directly actionable for managers. RQ2: keyword diversity is driven by reviewer engagement with the platform, not by visit type.}
  \sent{RQ3: higher sentiment reduces reactions---effusive praise is not what readers respond to. RQ4: different visitor groups mention different aspects, but what a review discusses does not predict reactions once reviewer identity is controlled.}
  \sent{Three contributions: review-level replication of Lee et al.; platform-structured visit context as a joint predictor set; aspect-level analysis cross-cut by visit context.}
  \sent{Limitations: associations only, no causal event; Model 1 profiles returning visitors but doesn't explain why anyone returns; a single platform. Roadmap: place-and-time fixed effects, Hausman test, and inductive aspect validation.}
}{%
  \sent{요약하면. RQ1: 대기는 재방문의 가장 강한 부정 신호이며 운영자가 직접 조치 가능한 유일한 변수. RQ2: 키워드 다양성은 작성자의 플랫폼 참여도에 의해 좌우되며, 방문 유형에 의한 것이 아니다.}
  \sent{RQ3: 긍정 감성은 반응을 줄인다---과한 칭찬은 독자의 선택 기준이 아니다. RQ4: 방문자별로 언급 측면이 다르지만, 작성자 특성 통제 후 리뷰 내용은 반응을 예측하지 않는다.}
  \sent{세 가지 기여: 이민영 외의 리뷰 수준 재현; 플랫폼 구조화 방문 맥락의 통합 예측 변수 세트 활용; 방문 맥락과 교차한 측면 수준 분석.}
  \sent{한계: 연관성만 다루며 인과 이벤트 없음; 모형 1은 재방문자를 특성화할 뿐 재방문 원인을 설명하지 않음; 단일 플랫폼. 향후: 관광지-시간 고정효과, Hausman 검정, 측면의 귀납적 검증.}
}

% ─────────────────────────────────────────────────────────────────────────────
% SLIDE 22 — Closing / Thank you
% ─────────────────────────────────────────────────────────────────────────────
\sechead{15. Closing (Slide 22)}{15. 마무리 (슬라이드 22)}
\bilingual{%
  \sent{Thank you for your attention. The full report, dataset documentation, and analysis scripts are available in the project repository. I welcome questions and discussion.}
}{%
  \sent{경청해 주셔서 감사합니다. 전체 보고서, 데이터셋 문서, 분석 스크립트는 프로젝트 저장소에서 열람할 수 있습니다. 질문과 논의를 환영합니다.}
}

\vspace{4pt}
\noindent\rule{\linewidth}{0.8pt}
"""

# Load, replace lines 55-224 inclusive (0-indexed 54..223), save.
with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()
print(f"Lines before: {len(lines)}")

head = lines[:54]           # lines 1..54
tail = lines[224:]          # lines 225 onward
new_lines = head + [NEW_TALK + "\n"] + tail
with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print(f"Lines after:  {len(new_lines)}")
print("OK. Talk portion rewritten (15 sections, aligned to 22-slide deck).")
