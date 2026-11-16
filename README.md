# Cross-Cultural Tourist Review Analysis

Comparative NLP analysis of domestic Korean and foreign tourist reviews
for major attractions in Seoul and Busan.

## Corpus

- 496 reviews across 8 places
- Korean-language (domestic) and English-language (foreign) reviews
- Balanced sampling (~30 per language per place)

## Pipeline

Stage numbers are shared between the two branches -- see `places.json`'s
header comment and `project-places-json` memory for the full stage catalog.
`06_llm_analysis.py` is the one script both branches call (no flag = cc,
`--naver` = Naver-only).

| Stage | Script | Description | Environment | Branch |
|-------|--------|-------------|-------------|--------|
| 01_01 | `01_01_scrape_naver.py` | Naver Place review scraper (Selenium) | base | both |
| 01_02 | `gmaps_scraper/scrape.js` | Google Maps review scraper | Node.js | cc |
| 01_03 | `01_03_export_flat.py` | Export raw JSON to flat CSV (manual inspection only) | base | both |
| 02_cc | `02_cc_build_corpus.py` | Build bilingual corpus from raw data | base | cc |
| 02_naver | `02_naver_build_dataset.py` | Korean-only dataset from all scraped reviews | base | naver |
| 03_01 | `03_01_analyze.py` | Sentiment, TF-IDF, TTR, LDA, cross-lingual similarity | base | cc |
| 03_02 | `03_02_lda_k_selection.py` | Coherence / perplexity by K | base | cc |
| 04_01 | `04_01_visualize.py` | Generate analysis figures | base | cc |
| 04_02 | `04_02_geo_bubble.py` | Geographic bubble map (folium + matplotlib) | base | cc |
| 05_01 | `05_01_advanced_nlp.py` | Multilingual embeddings, motivation classification | faiss-gpu | cc |
| 06 | `06_llm_analysis.py` | ABSA + narrative summaries via LLMs | faiss-gpu | both |
| 07_01 | `07_01_absa_validation.py` | ABSA vs manual coding | base | cc |
| 07_02 | `07_02_dictionary_check.py` | KWIC export and precision scoring of hypothesis dictionaries | base | cc |
| 08_01 | `08_01_hypothesis_tests.py` | Hofstede-based hypothesis tests (Mann-Whitney U, chi-square, sensitivity) | base | cc |
| 09_01 | `09_01_naver_models.py` | Revisit (logit) and keyword-diversity (ordered logit, Poisson) models | base | naver |
| 09_02 | `09_02_rating_checks.py` | Star ratings: sentiment validation, H5 with ratings, revisitor ratings | base | naver |
| 10_01 | `10_01_descriptive_tables.py` | 표 1-4 for the proposal (`proposal/tables_naver.tex`) | base | naver |
| — | `run_pipeline.py` | Runs the cc branch then the naver branch in order, one log per step | any | both |
| — | `hypothesis_dictionaries.py` | Shared dictionaries/tokenizers for 07_02 and 08_01 (module, not run directly) | base | cc |

### Environments

- **base**: `C:\Users\crono\anaconda3\python.exe`
- **faiss-gpu**: `C:\Users\crono\anaconda3\envs\faiss-gpu\python.exe` (PyTorch/CUDA)

### Running

```powershell
$env:PYTHONIOENCODING="utf-8"
& "C:\Users\crono\anaconda3\python.exe" 02_cc_build_corpus.py
& "C:\Users\crono\anaconda3\python.exe" 03_01_analyze.py
& "C:\Users\crono\anaconda3\python.exe" 04_01_visualize.py
& "C:\Users\crono\anaconda3\envs\faiss-gpu\python.exe" 05_01_advanced_nlp.py
& "C:\Users\crono\anaconda3\envs\faiss-gpu\python.exe" 06_llm_analysis.py
```

## Analysis Outputs

All outputs are saved in `data/analysis/`:

- `sentiment_results.csv` — per-review sentiment scores
- `stats_mannwhitney.csv` — Mann-Whitney U test results
- `crosslingual_similarity.csv` — KO-EN cosine similarity per place
- `motivation_summary.csv` — zero-shot motivation classification
- `ttr_results.csv` — type-token ratio per place/language
- `tfidf_contrast.csv` — distinctive keywords per language group
- `lda_en_topics.csv`, `lda_ko_topics.csv` — LDA topic words
- `absa_summary.csv` — aspect-based sentiment (5 dimensions)
- `llm_summaries.json` — narrative summaries per place

## Places

Single source of truth: **`places.json`** (23 places as of 2026-10). To add a
place or change its Naver id / Google Maps URL / type, edit it there — never
in a script. `places_data.py` loads it for Python; `gmaps_scraper/scrape.js`
loads it directly (`require("../places.json")`) for Node.

```powershell
& "C:\Users\crono\anaconda3\python.exe" places_data.py   # inventory / sanity check
```

Every place-name dependent script (`01_01_scrape_naver.py`, `02_cc_build_corpus.py`,
`04_01_visualize.py`, `04_02_geo_bubble.py`, `05_01_advanced_nlp.py`,
`06_llm_analysis.py`, `02_naver_build_dataset.py`, `hypothesis_dictionaries.py`,
`gmaps_scraper/scrape.js`) imports from here.

New places are added to `places.json` only from the agreed criteria --
Yanolja Research "Korea's Top 500" and KTO visitor-volume data (see memory
`project-place-selection-criteria`), never from general knowledge or an
ungrounded web search.
