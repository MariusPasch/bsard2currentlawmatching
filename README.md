# BSARD Corpus Database

**Author:** Marios Paschalidis | **Last updated:** 2026-03-20
**Parent project:** BSARD RAG Thesis

---

## Overview

This project builds a **SQLite corpus database** (with Parquet and JSONL exports) containing every article from all 49 Justel consolidated Belgian law PDFs, enriched with retrieval-ready structural and relational metadata. The database serves as the single source of truth for all downstream RAG retrieval experiments (RQ1–RQ3) described in the master thesis.

The corpus has two tiers:

- **BSARD articles** — ~22,633 articles from the benchmark dataset, linked by `bsard_id`, with ground truth question–article annotations used to compute Recall@k, NDCG, and MRR across all experiments.
- **Non-BSARD articles** — all remaining articles in the same 49 PDFs. These serve as retrieval distractors and provide full context for Graph RAG citation-neighbourhood expansion (Stage 5.5 of thesis).

All PDF article extraction and structural hierarchy detection uses **PyMuPDF (`fitz`)** with font-size heuristics and regex-based pattern matching. No Azure Document Intelligence is used.

---

## Project Structure

```
Dataset_Creation/                      ← Project root (this repo)
│
├── retrieval/
│   ├── extract_articles_from_pdf.py   ← Phase A: PyMuPDF structural extraction
│   ├── link_bsard.py                  ← Phase B: BSARD linkage + metadata merge
│   ├── extract_citations.py           ← Phase C: cross-reference extraction
│   ├── build_database.py              ← Phase D: SQLite assembly
│   ├── export_corpus.py               ← Phase D: Parquet + JSONL exports
│   └── corpus_stats.py                ← Phase E: Chapter 3 statistics
│
├── output/                            ← Junction/symlink → OneDrive storage
│   │                                     (OneDrive\Python Project Storage\BSARD_THESIS_DATASET)
│   ├── bsard_corpus.db                ← Primary SQLite database
│   ├── bsard_articles.parquet         ← Full corpus flat export
│   ├── bsard_articles.jsonl           ← Full corpus for vector store ingestion
│   ├── bsard_articles_only.parquet    ← BSARD-only subset
│   ├── bsard_articles_only.jsonl      ← BSARD-only subset for benchmarking
│   ├── corpus_stats.json              ← Chapter 3 statistics
│   ├── pdfs/                          ← 49 downloaded Justel PDFs (~59 MB)
│   └── extracted/                     ← Per-PDF intermediate JSONL (Phase A output)
│
├── analysis/
│   └── augment_markers.py             ← Temporal status enrichment (from parent project)
│
├── .venv/                             ← Local Python virtual environment (not committed)
├── requirements.txt                   ← All project dependencies
├── CLAUDE.md                          ← Project rules for Claude Code
├── CORPUS_DATABASE_PROJECT.md         ← Full technical specification
└── README.md                          ← This file
```

> **Storage rule:** All large files, datasets, and database outputs (`output/`) are stored on OneDrive at `OneDrive\Python Project Storage\BSARD_THESIS_DATASET` via a directory junction. All code and configuration files are committed to this GitHub repository.

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

The pipeline runs in five sequential phases. Each phase has its own script; they can be run independently once the previous phase output exists.

### Phase A — PDF Article Extraction

**Script:** `retrieval/extract_articles_from_pdf.py`

Reads all 49 Justel PDFs from `output/pdfs/` using PyMuPDF. Performs font-size analysis per PDF to establish the heading hierarchy, then detects French and Dutch structural markers (LIVRE, TITRE, CHAPITRE, SECTION, Art.) to extract every article with its full hierarchical context.

Output: one JSONL file per PDF in `output/extracted/`.

### Phase B — BSARD Linkage and Metadata Merge

**Script:** `retrieval/link_bsard.py`

Links extracted articles to the BSARD HuggingFace benchmark corpus (`maastrichtlawtech/bsard`). BSARD articles get canonical text from the dataset; non-BSARD articles keep the PDF-extracted text. Merges temporal status from `augment_markers.py` and verification metadata from `bsard_full_verify.csv`.

Also loads the 1,100 BSARD benchmark questions and resolves ground truth article IDs.

### Phase C — Cross-Reference Extraction

**Script:** `retrieval/extract_citations.py`

Applies regex patterns to each article's text to extract raw Belgian legal citation strings (`art. 42`, `l'article 3 de la loi du 10 juin 1998`, etc.). Resolves citations to `article_id` values where possible. Builds the inverse index (`cited_by_ids`) as a post-processing step.

### Phase D — Database Assembly and Exports

**Script:** `retrieval/build_database.py` + `retrieval/export_corpus.py`

Assembles the SQLite database (`output/bsard_corpus.db`) with three tables: `articles`, `questions`, `citation_graph`. Creates critical indices and an FTS5 virtual table for BM25-style full-text search. Exports Parquet and JSONL files for downstream retrieval workflows.

### Phase E — Corpus Statistics

**Script:** `retrieval/corpus_stats.py`

Computes all corpus statistics required for Chapter 3 of the thesis and saves them to `output/corpus_stats.json`. Includes article count by tier, token length distribution, cross-reference density, hierarchy coverage, and PDF extraction failure rate.

---

## Database Schema

### `articles` table

One row per extracted article (BSARD + non-BSARD). Key columns:

| Column | Description |
|--------|-------------|
| `article_id` | Auto-assigned primary key |
| `bsard_id` | BSARD benchmark ID (NULL for non-BSARD articles) |
| `is_bsard_article` | 1 if in the BSARD benchmark, 0 otherwise |
| `law_code` | Law name (e.g. `"Code Civil"`, `"Code Pénal"`) |
| `article_number` | Article number as it appears in the PDF |
| `article_text` | Full article body (canonical HF text for BSARD, PDF-extracted for others) |
| `hierarchy_path` | JSON array of heading path from law title to article |
| `chapter_title`, `section_title` | Structural headings from PyMuPDF parsing |
| `cross_reference_ids` | JSON array of resolved `article_id` values cited |
| `cited_by_ids` | JSON array of articles that cite this article |
| `token_count` | Token count via `tiktoken` `cl100k_base` encoding |
| `amendment_date`, `article_status`, `is_pre_bsard` | Temporal metadata (BSARD articles only) |

### `questions` table

One row per BSARD benchmark question (1,100 total). Includes `question_text`, `relevant_article_ids` (resolved), `relevant_bsard_ids`, `n_relevant_articles`, and `split` (train/test).

### `citation_graph` table

Materialized directed edge list for Graph RAG. Each row is one citation edge with `source_id`, `target_id`, `citation_text`, and a `resolved` flag.

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
| Pattern matching | `re` (stdlib) |
| Text normalisation | `unicodedata` (stdlib) |

---

## External Data Sources

| Source | Access |
|--------|--------|
| BSARD corpus (22,633 articles) | `load_dataset("maastrichtlawtech/bsard", "corpus", split="corpus")` |
| BSARD questions (1,100) | `load_dataset("maastrichtlawtech/bsard", "questions", split="train/test")` |
| 49 Justel consolidated PDFs | Downloaded to `output/pdfs/` (stored on OneDrive) |

---

## Integration with Thesis RAG Experiments

| Database Feature | Thesis Stage |
|-----------------|-------------|
| `article_text` + `is_bsard_article` | Corpus for all Tier 1–4 retrieval (RQ1, Ch. 4) |
| `bsard_id` + `questions` table | Ground truth for Recall@k, MRR@10, NDCG@10 |
| `token_count` | Chunking ablation (Stage 5.1, RQ2) |
| `hierarchy_path`, `chapter_title`, `section_title` | Hierarchical chunking, PageIndex tree (Stages 5.1–5.3, RQ2) |
| `law_code`, `law_type`, `amendment_date` | Metadata-filtered retrieval (Stage 5.2, RQ2) |
| `citation_graph` + `cross_reference_ids` | Graph RAG knowledge graph (Stage 5.5, RQ2) |
| `has_cross_references`, `n_relevant_articles` | Failure-condition stratification (§4.5, RQ1) |
| FTS5 virtual table | BM25 baseline + sparse retrieval prototyping |

---

## Parent Project Artefacts

This project reads from (but never writes to) these parent project outputs:

| File | Description |
|------|-------------|
| `bsard_full_verify.csv` | 22,633 rows with verification status, PDF/HTML match info |
| `output/pdfs/` | 49 downloaded Justel consolidated PDFs |
| `output/pdf_article_counts.json` | Article counts per PDF |
| `output/pdf_page_coverage.json` | Per-article page index |

Configure the parent project path via the `BSARD_PARENT_PROJECT` environment variable or a local config file.
