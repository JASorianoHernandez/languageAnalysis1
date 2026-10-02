# Cross-Cultural Tourist Review Analysis

Comparative NLP analysis of domestic Korean and foreign tourist reviews
for major attractions in Seoul and Busan.

## Corpus

- 496 reviews across 8 places
- Korean-language (domestic) and English-language (foreign) reviews
- Balanced sampling (~30 per language per place)

## Pipeline

| Script | Description | Environment |
|--------|-------------|-------------|
| `01_scrape_gmaps.js` | Google Maps review scraper (Puppeteer) | Node.js |
| `02_scrape_naver.py` | Naver Place review scraper (Selenium) | base |
| `02_02_export_flat.py` | Export raw JSON to flat CSV | base |
| `03_build_corpus.py` | Build bilingual corpus from raw data | base |
| `04_analyze.py` | Sentiment, TF-IDF, TTR, LDA, cross-lingual similarity | base |
| `05_visualize.py` | Generate analysis figures | base |
| `05_02_geo_bubble.py` | Geographic bubble map (folium + matplotlib) | base |
| `06_advanced_nlp.py` | Multilingual embeddings, motivation classification | faiss-gpu |
| `07_llm_analysis.py` | ABSA + narrative summaries via LLMs | faiss-gpu |

### Environments

- **base**: `C:\Users\crono\anaconda3\python.exe`
- **faiss-gpu**: `C:\Users\crono\anaconda3\envs\faiss-gpu\python.exe` (PyTorch/CUDA)

### Running

```powershell
$env:PYTHONIOENCODING="utf-8"
& "C:\Users\crono\anaconda3\python.exe" 03_build_corpus.py
& "C:\Users\crono\anaconda3\python.exe" 04_analyze.py
& "C:\Users\crono\anaconda3\python.exe" 05_visualize.py
& "C:\Users\crono\anaconda3\envs\faiss-gpu\python.exe" 06_advanced_nlp.py
& "C:\Users\crono\anaconda3\envs\faiss-gpu\python.exe" 07_llm_analysis.py
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

| City | Place |
|------|-------|
| Seoul | Gyeongbokgung, Changdeokgung, Bukchon Village, Gwangjang Market, Hongdae Street, Lotte World |
| Busan | Gwangalli Beach, Haeundae Beach |

Two additional places (Insadong-gil, N Seoul Tower) are pending data collection.
