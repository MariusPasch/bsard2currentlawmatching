# Project Map — bsard2currentlawmatching

Quick reference for all code and data locations.
Data lives on the Hugging Face dataset repo `MariusPasch/bsard2currentlawmatching`;
download into `output/` via `python scripts/download_from_hf.py`.
Last updated: 2026-05-17

---

## Code (GitHub)

### `pipeline/` — ETL data pipeline (run once, in order)

| File | Phase | What it does |
|---|---|---|
| `download_pdfs.py` | A | Downloads 49 Justel consolidated PDFs from URLs in `bsard_full_verify.csv` |
| `extract_articles_from_pdf.py` | A | Extracts articles from each PDF via font-size analysis and regex heading detection; writes one JSONL per PDF to `output/extracted/` |
| `link_bsard.py` | B | Links extracted articles to the BSARD HuggingFace benchmark (corpus + questions); three-fallback normalised matching; appends 5,944 unmatched BSARD articles as stubs; writes `output/linked/` |
| `extract_citations.py` | C | Parses French legal cross-references from article text using five regex patterns; resolves cited article IDs; writes citation graph; enriches articles with citation metadata |
| `build_database.py` | D | Builds SQLite database from Phase C outputs; creates `articles`, `questions`, and `citation_graph` tables; FTS5 index; token counts via tiktoken |
| `export_corpus.py` | D | Exports the database to Parquet and JSONL formats (full corpus + BSARD-only subset) |
| `build_clean_dataset.py` | F (post) | Builds the deduplicated, PDF-only companion dataset from `bsard_corpus.db`; excludes Phase B HF-only stubs and collapses duplicate `(pdf_filename, article_number)` rows. See [CLEAN_DATASET.md](CLEAN_DATASET.md) |

### `analysis/` — Analysis scripts (run independently)

| File | What it does |
|---|---|
| `corpus_stats.py` | Phase E: computes 10 categories of corpus statistics (length distributions, Jaccard overlap, hierarchy coverage, citation density, etc.); writes `output/corpus_stats.json` |
| `exploratory_analysis.ipynb` | Interactive Jupyter notebook: corpus-wide statistics and visualisations (Part 1), article deep-dive by BSARD ID / article number / law code (Part 2), FTS5 search and filter utilities (Part 3) |

### `scripts/` — Hugging Face helpers

| File | What it does |
|---|---|
| `upload_to_hf.py` | Pushes the local `output/` artifacts (DB, Parquet, JSONL, PDFs) to the Hugging Face dataset repo |
| `download_from_hf.py` | Mirrors the Hugging Face dataset repo into the local `output/` directory |

### Root

| File | What it is |
|---|---|
| `CORPUS_DATABASE_PROJECT.md` | Full technical specification: schema, pipeline design, regex patterns |
| `README.md` | Project overview, setup instructions, pipeline summary, schema reference |
| `PROJECT_MAP.md` | This file |
| `RETRIEVAL_PROJECT.md` | Context document for the downstream retrieval experiments project |
| `CLEAN_DATASET.md` | Documentation for the deduplicated, PDF-only companion dataset (`bsard_corpus_clean.db`) |
| `QUESTION_EXTRACTION_ANALYSIS.md` | Per-question PDF-extraction status analysis docs |
| `requirements.txt` | Pinned Python dependencies |
| `.gitignore` | Excludes `.venv/`, `output/`, `__pycache__/` |

---

## Data (Hugging Face → local `output/`)

**Hugging Face dataset:** [`MariusPasch/bsard2currentlawmatching`](https://huggingface.co/datasets/MariusPasch/bsard2currentlawmatching)
**Local path:** `output/` (populated by `python scripts/download_from_hf.py`)

### Raw inputs

| Path | Size | What it is |
|---|---|---|
| `output/pdfs/` | 49 files | Justel consolidated Belgian law PDFs (one per law code) |

### Intermediate outputs

| Path | Size | What it is |
|---|---|---|
| `output/extracted/` | 49 files | Per-PDF JSONL files from Phase A; one record per extracted article (~34 K articles total) |
| `output/linked/articles_linked.jsonl` | ~70 MB | Phase B output: all 40,231 articles with BSARD linkage and metadata merged in |
| `output/linked/articles_with_citations.jsonl` | ~90 MB | Phase C output: articles enriched with parsed cross-references and citation counts |
| `output/linked/citation_graph.jsonl` | ~3 MB | Phase C output: 27,712 resolved citation edges |
| `output/linked/questions.jsonl` | small | Phase B output: 1,108 BSARD questions with resolved ground-truth article IDs |

### Final outputs

| Path | Size | What it is |
|---|---|---|
| `output/bsard_corpus.db` | ~100 MB | Primary SQLite database: `articles` (40,231 rows), `questions` (1,108 rows), `citation_graph` (27,712 rows), FTS5 index |
| `output/bsard_articles.parquet` | ~14 MB | Full corpus (all 40,231 articles) in Parquet |
| `output/bsard_articles.jsonl` | ~90 MB | Full corpus in JSONL |
| `output/bsard_articles_only.parquet` | ~12 MB | BSARD benchmark subset (33,741 articles) in Parquet |
| `output/bsard_articles_only.jsonl` | ~78 MB | BSARD benchmark subset in JSONL |
| `output/bsard_corpus_clean.db` | ~68 MB | Deduplicated, PDF-only companion SQLite (28,817 rows). See [CLEAN_DATASET.md](CLEAN_DATASET.md) |
| `output/bsard_articles_clean.parquet` | ~10 MB | Clean dataset in Parquet |
| `output/bsard_articles_clean.jsonl` | ~63 MB | Clean dataset in JSONL |
| `output/corpus_stats.json` | ~5 KB | Phase E statistics: corpus overview, length distributions, Jaccard overlap, etc. |

---

## Key numbers (Phase E)

| Metric | Value |
|---|---|
| Total articles | 40,231 |
| BSARD articles | 33,741 (83.9%) |
| Non-BSARD articles | 6,490 (16.1%) |
| Unique BSARD IDs | 22,633 |
| Unique law codes | 34 |
| PDFs | 49 |
| Citation edges | 27,712 |
| Articles with outgoing citations | 21,300 (52.9%) |
| Questions | 1,108 (886 train / 222 test) |
| Multi-article questions | 726 (65.5%) |
| Avg relevant articles per question | 6.18 |
| Median article length | 133 tokens / 492 chars |
| Mean Jaccard (query ↔ relevant article) | 0.052 |
| Median Jaccard (query ↔ relevant article) | 0.045 |
