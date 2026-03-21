# BSARD Corpus Database

**Author:** Marios Paschalidis | **Last updated:** 2026-03-21
**Parent project:** BSARD RAG Thesis

---

## Overview

This project builds a **SQLite corpus database** (with Parquet and JSONL exports) containing every article from all 49 Justel consolidated Belgian law PDFs, enriched with retrieval-ready structural and relational metadata. The database serves as the single source of truth for all downstream RAG retrieval experiments (RQ1–RQ3) described in the master thesis.

The corpus has two tiers:

- **BSARD articles** — 33,741 article records (22,633 unique benchmark IDs) linked by `bsard_id`, with ground truth question–article annotations used to compute Recall@k, NDCG, and MRR across all experiments.
- **Non-BSARD articles** — 6,490 additional articles from the same 49 PDFs. These serve as retrieval distractors and provide full context for Graph RAG citation-neighbourhood expansion.

All PDF article extraction and structural hierarchy detection uses **PyMuPDF (`fitz`)** with font-size heuristics and regex-based pattern matching.

---

## Project Structure

```
Dataset_Creation/                          ← Project root (this repo)
│
├── pipeline/                              ← ETL data pipeline (run once, in order)
│   ├── download_pdfs.py                   ← Phase A: download 49 Justel PDFs
│   ├── extract_articles_from_pdf.py       ← Phase A: PyMuPDF structural extraction
│   ├── link_bsard.py                      ← Phase B: BSARD linkage + metadata merge
│   ├── extract_citations.py               ← Phase C: cross-reference extraction
│   ├── build_database.py                  ← Phase D: SQLite assembly
│   └── export_corpus.py                   ← Phase D: Parquet + JSONL exports
│
├── analysis/                              ← Analysis scripts (run independently)
│   ├── corpus_stats.py                    ← Phase E: Chapter 3 statistics
│   └── exploratory_analysis.ipynb         ← Interactive corpus exploration notebook
│
├── output/                                ← Junction → OneDrive storage
│   │                                         (OneDrive\Python Project Storage\BSARD_THESIS_DATASET)
│   ├── bsard_corpus.db                    ← Primary SQLite database (~100 MB)
│   ├── bsard_articles.parquet             ← Full corpus flat export (14 MB)
│   ├── bsard_articles.jsonl               ← Full corpus for vector store ingestion (90 MB)
│   ├── bsard_articles_only.parquet        ← BSARD-only subset (12 MB)
│   ├── bsard_articles_only.jsonl          ← BSARD-only subset for benchmarking (78 MB)
│   ├── corpus_stats.json                  ← Chapter 3 statistics
│   ├── pdfs/                              ← 49 downloaded Justel PDFs
│   ├── extracted/                         ← Per-PDF intermediate JSONL (Phase A output)
│   └── linked/                            ← Intermediate enriched JSONL (Phases B–C output)
│
├── .venv/                                 ← Local Python virtual environment (not committed)
├── requirements.txt                       ← All project dependencies
├── CLAUDE.md                              ← Project rules for Claude Code
├── CORPUS_DATABASE_PROJECT.md             ← Full technical specification
├── PROJECT_MAP.md                         ← Quick reference: all file locations + descriptions
├── RETRIEVAL_PROJECT.md                   ← Context document for the downstream retrieval project
└── README.md                              ← This file
```

> **Storage rule:** All large files and database outputs (`output/`) are stored on OneDrive at `OneDrive\Python Project Storage\BSARD_THESIS_DATASET` via a directory junction. All code and configuration files are committed to this GitHub repository.

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd Dataset_Creation
```

### 2. Create and activate the virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the OneDrive output path

The `output/` directory must point to your OneDrive storage location. On Windows, create a directory junction:

```cmd
mklink /J output "C:\Users\<your-username>\OneDrive\Python Project Storage\BSARD_THESIS_DATASET"
```

---

## Pipeline

The pipeline runs in five sequential phases. Each phase reads the previous phase's output from `output/`.

### Phase A — PDF Download and Article Extraction

**Scripts:** `pipeline/download_pdfs.py` → `pipeline/extract_articles_from_pdf.py`

Downloads all 49 Justel PDFs. Then reads each PDF using PyMuPDF, runs font-size frequency analysis to establish the heading hierarchy, and applies French/Dutch structural marker regex patterns (LIVRE, TITRE, CHAPITRE, SECTION, Art.) to extract every article with its full hierarchical context.

Output: `output/pdfs/` (49 PDFs), `output/extracted/` (49 JSONL files, ~34,000 articles total).

### Phase B — BSARD Linkage and Metadata Merge

**Script:** `pipeline/link_bsard.py`

Links extracted articles to the BSARD HuggingFace benchmark corpus (`maastrichtlawtech/bsard`). Uses a three-fallback normalised matching strategy (exact → leading-integer → base-article-number). BSARD articles get canonical text from the dataset; non-BSARD articles keep the PDF-extracted text. Merges all verification metadata from `bsard_full_verify.csv` (UTF-8 encoded). Appends 5,944 BSARD articles not found in Phase A as stubs. Also loads all 1,108 BSARD benchmark questions.

Output: `output/linked/articles_linked.jsonl` (40,231 records), `output/linked/questions.jsonl` (1,108 questions).

### Phase C — Cross-Reference Extraction

**Script:** `pipeline/extract_citations.py`

Applies five French legal citation regex patterns to each article's text. Resolves citations to `article_id` values using a five-step lookup chain. Builds the inverse `cited_by` index as a post-processing step. Produces 27,712 resolved citation edges from 50,515 raw matches.

Output: `output/linked/articles_with_citations.jsonl`, `output/linked/citation_graph.jsonl`.

### Phase D — Database Assembly and Exports

**Scripts:** `pipeline/build_database.py` + `pipeline/export_corpus.py`

Assembles the SQLite database with three tables (`articles`, `questions`, `citation_graph`), seven covering indices, and an FTS5 virtual table for BM25-style full-text search. Token counts computed via `tiktoken` (`cl100k_base`). Then exports Parquet and JSONL files for downstream retrieval workflows.

Output: `output/bsard_corpus.db`, `output/bsard_articles*.parquet`, `output/bsard_articles*.jsonl`.

### Phase E — Corpus Statistics

**Script:** `analysis/corpus_stats.py`

Computes all corpus statistics required for Chapter 3 of the thesis. Saves results to `output/corpus_stats.json` and prints a human-readable report. Also used by `analysis/exploratory_analysis.ipynb`.

---

## Database Schema

### `articles` table — 40,231 rows, 36 columns

| Column | Description |
|--------|-------------|
| `article_id` | Auto-assigned primary key (1–40,231) |
| `bsard_id` | BSARD benchmark ID (NULL for non-BSARD articles) |
| `is_bsard_article` | 1 if in the BSARD benchmark, 0 otherwise |
| `law_code` | Law name (e.g. `"Code Civil"`, `"Code Pénal"`) |
| `law_type` | `national` or `regional` |
| `article_number` | Article number as it appears in the PDF |
| `article_text` | Full article body text |
| `article_text_source` | `bsard_dataset`, `pdf_extracted`, or `pdf_extraction_failed` |
| `law_title_text` | Top-level law heading from PyMuPDF parsing |
| `chapter_title`, `section_title`, `subsection_title` | Structural headings |
| `hierarchy_path` | JSON array: full path from law title to article |
| `hierarchy_depth` | Number of levels in `hierarchy_path` |
| `pdf_filename`, `pdf_page_start`, `pdf_page_end` | PDF provenance |
| `cross_reference_ids` | JSON array of resolved `article_id` values cited by this article |
| `cited_by_ids` | JSON array of `article_id` values of articles citing this one |
| `n_outgoing_refs`, `n_cited_by` | Citation degree counts |
| `token_count` | Token count via `tiktoken` `cl100k_base` |
| `char_count` | Character count |
| `has_cross_references` | 1 if `n_outgoing_refs > 0` |
| `amendment_date`, `article_status`, `is_pre_bsard` | Temporal metadata (BSARD articles only) |
| `verification_status` | `FOUND`, `PARTIAL`, or `NOT FOUND` (BSARD articles only) |

### `questions` table — 1,108 rows

| Column | Description |
|--------|-------------|
| `question_id` | BSARD question ID |
| `question_text` | Natural language legal question in French |
| `relevant_article_ids` | JSON array of ground-truth `article_id` values |
| `relevant_bsard_ids` | JSON array of raw BSARD IDs |
| `n_relevant_articles` | Number of ground-truth articles |
| `split` | `train` (886) or `test` (222) |

### `citation_graph` table — 27,712 rows

| Column | Description |
|--------|-------------|
| `source_id` | `article_id` of the article containing the citation |
| `target_id` | `article_id` of the cited article |
| `citation_text` | Raw citation string |
| `resolved` | 1 if target exists in the corpus |

---

## Key Corpus Statistics (Phase E)

| Metric | Value |
|--------|-------|
| Total articles | 40,231 |
| BSARD articles | 33,741 (83.9%) |
| Non-BSARD (distractors) | 6,490 (16.1%) |
| Unique BSARD IDs | 22,633 |
| Unique law codes | 34 |
| PDFs | 49 |
| Citation edges | 27,712 |
| Articles with outgoing citations | 21,300 (52.9%) |
| Questions total | 1,108 (886 train / 222 test) |
| Multi-article questions | 726 (65.5%) |
| Median token count | 133 tokens |
| Median Jaccard (query ↔ article) | 0.045 |

---

## Technical Stack

| Category | Library |
|----------|---------|
| PDF parsing | `PyMuPDF` (`fitz`) |
| Dataset loading | `datasets` (HuggingFace) |
| Database | `sqlite3` (stdlib) |
| Token counting | `tiktoken` (`cl100k_base`) |
| Data processing | `pandas` |
| Parquet export | `pyarrow` |
| Analysis / viz | `matplotlib`, `seaborn` |
| Pattern matching | `re` (stdlib) |
| Text normalisation | `unicodedata` (stdlib) |

---

## External Data Sources

| Source | Access |
|--------|--------|
| BSARD corpus (22,633 articles) | `load_dataset("maastrichtlawtech/bsard", "corpus", split="corpus")` |
| BSARD questions (1,108) | `load_dataset("maastrichtlawtech/bsard", "questions", split="train/test")` |
| 49 Justel consolidated PDFs | Downloaded to `output/pdfs/` (OneDrive) |
| `bsard_full_verify.csv` | Parent project — UTF-8, read-only |

---

## Downstream Usage

The corpus database feeds the **BSARD Retrieval Experiments** project (`RETRIEVAL_PROJECT.md`). See that document for the full retrieval method roadmap (RQ1–RQ3), evaluation protocol, and how each database feature maps to a specific thesis stage.
