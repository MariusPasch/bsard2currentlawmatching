# BSARD Retrieval Experiments — Project Context

**Author:** Marios Paschalidis | **Last updated:** 2026-03-21
**Thesis:** RAG Retrieval over Belgian Statutory Law (BSARD)
**Predecessor project:** `Dataset_Creation/` — corpus and database construction (complete)

This document is the primary context file for the **Retrieval** project. It describes everything a new project needs to know: what the corpus contains, how it is stored, how to access it, what must be built, and how success is measured.

---

## 1. What This Project Builds

A systematic comparison of retrieval methods over the BSARD Belgian legal corpus, producing the empirical results for **RQ1**, **RQ2**, and **RQ3** of the master thesis. Each retrieval method is evaluated against the same 222-question BSARD test set using standard IR metrics.

The pipeline progresses through five implementation stages, each building on the previous:

| Stage | Method family | Thesis mapping |
|---|---|---|
| 1 | Sparse (BM25) | RQ1 baseline |
| 2 | Dense (bi-encoder embeddings) | RQ1 main comparison |
| 3 | Hybrid (sparse + dense fusion) | RQ1 extension |
| 4 | Re-ranking (cross-encoder) | RQ1 extension |
| 5 | Advanced RAG (chunking, metadata, GraphRAG) | RQ2 + RQ3 |

---

## 2. Corpus — What Is Available

All corpus data is in **`output/bsard_corpus.db`** (SQLite, ~100 MB) and its flat exports. The `output/` directory is a Windows junction pointing to:

```
OneDrive\Python Project Storage\BSARD_THESIS_DATASET\
```

### 2.1 Primary files

| File | Size | When to use |
|---|---|---|
| `output/bsard_corpus.db` | ~100 MB | All querying, evaluation, citation graph traversal |
| `output/bsard_articles_only.parquet` | ~12 MB | Fast loading of BSARD subset for indexing/embedding |
| `output/bsard_articles.parquet` | ~14 MB | Full corpus including distractor articles |
| `output/bsard_articles_only.jsonl` | ~78 MB | JSONL ingestion into vector stores |
| `output/corpus_stats.json` | ~5 KB | Corpus statistics for thesis Chapter 3 |

### 2.2 Corpus tiers

**BSARD articles** (`is_bsard_article = 1`): 33,741 records, 22,633 unique `bsard_id` values.
- These are the articles the benchmark questions were written about.
- They carry ground truth annotations via the `questions` table.
- Sub-paragraph variants share a `bsard_id` (e.g., Art.1.1.1-1, Art.1.1.1-2 → same BSARD ID).
- Article text source: HuggingFace canonical text for 33,741 records (post-2021 language).

**Non-BSARD articles** (`is_bsard_article = 0`): 6,490 records.
- Articles found in the 49 Justel PDFs that are not in the BSARD benchmark.
- These are retrieval distractors — the retrieval system must not surface them as answers.
- Text source: PDF-extracted.

### 2.3 Key `articles` table columns for retrieval

| Column | Type | Use |
|---|---|---|
| `article_id` | INTEGER PK | All internal references |
| `bsard_id` | INTEGER | Ground truth linkage to `questions.relevant_article_ids` |
| `is_bsard_article` | INTEGER | Filter: corpus tier |
| `law_code` | TEXT | 34 unique values; metadata-filtered retrieval |
| `article_number` | TEXT | Human-readable article reference |
| `article_text` | TEXT | The text to embed / index |
| `token_count` | INTEGER | Chunking decisions (cl100k_base tokens) |
| `char_count` | INTEGER | Lightweight size proxy |
| `hierarchy_path` | TEXT (JSON) | Hierarchical context for PageIndex (Stage 5.3) |
| `chapter_title`, `section_title` | TEXT | Structural metadata for context-aware chunking |
| `cross_reference_ids` | TEXT (JSON) | Neighbour expansion in GraphRAG (Stage 5.5) |
| `cited_by_ids` | TEXT (JSON) | Inverse neighbour expansion |
| `n_outgoing_refs`, `n_cited_by` | INTEGER | Citation degree; failure-condition stratification |
| `has_cross_references` | INTEGER | Stratification flag for §4.5 analysis |
| `amendment_date`, `is_pre_bsard` | TEXT/INTEGER | Temporal filtering (Stage 5.2) |
| `article_status` | TEXT | `ORIGINAL_NEVER_AMENDED`, `PRE_BSARD`, `POST_BSARD` |

### 2.4 FTS5 full-text index (already built)

The database has a pre-built FTS5 virtual table for BM25-style sparse retrieval:

```sql
-- FTS5 search with BM25 ranking and snippet extraction
SELECT a.article_id, a.bsard_id, a.law_code, a.article_number,
       snippet(articles_fts, 0, '>>>', '<<<', '...', 20) AS snippet
FROM articles_fts
JOIN articles a ON a.article_id = articles_fts.rowid
WHERE articles_fts MATCH ?
ORDER BY rank
LIMIT 100;
```

The FTS5 tokenizer is `unicode61` (handles accented French characters correctly).

### 2.5 Citation graph

The `citation_graph` table has 27,712 directed edges. It can be loaded into NetworkX for graph traversal:

```python
import sqlite3, networkx as nx

conn = sqlite3.connect("output/bsard_corpus.db")
edges = conn.execute(
    "SELECT source_id, target_id FROM citation_graph WHERE resolved = 1"
).fetchall()
G = nx.DiGraph()
G.add_edges_from(edges)
```

For GraphRAG neighbourhood expansion: given a retrieved `article_id`, retrieve its `k`-hop neighbours via `cross_reference_ids` and `cited_by_ids` columns (pre-materialised in the `articles` table for efficiency).

---

## 3. Benchmark — Questions and Ground Truth

### 3.1 The questions table

1,108 natural language legal questions in French. Each question has one or more ground-truth relevant articles.

```python
import sqlite3, json

conn = sqlite3.connect("output/bsard_corpus.db")

# Load all test questions with ground truth
questions = conn.execute("""
    SELECT question_id, question_text, relevant_article_ids, n_relevant_articles
    FROM questions
    WHERE split = 'test'
""").fetchall()

for q in questions:
    q_id     = q["question_id"]
    text     = q["question_text"]
    gt_ids   = json.loads(q["relevant_article_ids"])  # list of article_id integers
    n_gt     = q["n_relevant_articles"]
```

### 3.2 Ground truth structure

| Field | Description |
|---|---|
| `relevant_article_ids` | JSON array of `article_id` integers — the internal PKs for this corpus |
| `relevant_bsard_ids` | JSON array of BSARD benchmark `id` values — for traceability |
| `n_relevant_articles` | Number of ground-truth articles (mean = 6.18, range 1–many) |
| `split` | Use `test` (222 questions) for all reported experiments; `train` (886) for development |

**Important:** 65.5% of questions require multiple relevant articles. Retrieval must surface *all* of them to score perfectly on Recall@k for those queries.

### 3.3 Benchmark statistics

| Metric | Value |
|---|---|
| Total questions | 1,108 |
| Test set | 222 |
| Train set | 886 |
| Single-article questions | 382 (34.5%) |
| Multi-article questions | 726 (65.5%) |
| Mean relevant articles | 6.18 |
| Median Jaccard (query ↔ relevant article) | 0.045 |

The **low Jaccard overlap (median 0.045)** is the core motivation for dense retrieval: questions rarely share exact vocabulary with their relevant articles.

---

## 4. Evaluation Protocol

### 4.1 Metrics

All methods are evaluated on the **test split** (222 questions) with these standard IR metrics:

| Metric | Definition | Why |
|---|---|---|
| **Recall@k** | Fraction of ground-truth articles found in top-k results | Primary metric; measures how many correct articles are retrieved |
| **MRR@10** | Mean Reciprocal Rank of the first relevant result in top-10 | Captures position of first correct hit |
| **NDCG@10** | Normalized Discounted Cumulative Gain at 10 | Rewards higher-ranked relevant results |

Report for k ∈ {1, 5, 10, 20, 50, 100}.

### 4.2 Ground truth matching

A retrieved article is **relevant** if its `article_id` appears in `relevant_article_ids` for the question. Because multiple articles can share a `bsard_id` (sub-paragraph variants), always match on `article_id`, not `bsard_id`.

### 4.3 Evaluation function template

```python
def evaluate(results: dict[int, list[int]], ground_truth: dict[int, list[int]],
             k_values: list[int] = [1, 5, 10, 20, 50, 100]) -> dict:
    """
    results      : {question_id: [article_id, ...]} — ranked list, best first
    ground_truth : {question_id: [article_id, ...]} — from questions table
    """
    from collections import defaultdict
    import numpy as np

    recall_at_k = defaultdict(list)
    mrr_scores, ndcg_scores = [], []

    for q_id, gt in ground_truth.items():
        ranked = results.get(q_id, [])
        gt_set = set(gt)

        # Recall@k
        for k in k_values:
            top_k = set(ranked[:k])
            recall_at_k[k].append(len(top_k & gt_set) / len(gt_set))

        # MRR@10
        mrr = 0.0
        for rank, art_id in enumerate(ranked[:10], 1):
            if art_id in gt_set:
                mrr = 1.0 / rank
                break
        mrr_scores.append(mrr)

        # NDCG@10
        gains = [1 if art_id in gt_set else 0 for art_id in ranked[:10]]
        dcg  = sum(g / np.log2(i + 2) for i, g in enumerate(gains))
        ideal = sorted(gains, reverse=True)
        idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal))
        ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)

    return {
        **{f"Recall@{k}": np.mean(recall_at_k[k]) for k in k_values},
        "MRR@10":  np.mean(mrr_scores),
        "NDCG@10": np.mean(ndcg_scores),
    }
```

### 4.4 Stratified analysis (§4.5 of thesis)

Beyond aggregate metrics, report results broken down by:
- **Single vs. multi-article questions** (`n_relevant_articles == 1` vs. `> 1`)
- **Articles with cross-references vs. without** (`has_cross_references`)
- **Article length quartile** (using `token_count` percentiles from `corpus_stats.json`)

---

## 5. Retrieval Stages

### Stage 1 — Sparse Retrieval (BM25)

**Goal:** Establish the BM25 baseline using the pre-built FTS5 index.

Implementation options (choose one):
- **SQLite FTS5** — built-in, zero dependency. Use `ORDER BY rank` for BM25 scoring.
- **BM25s** (`bm25s` library) — pure-Python BM25 with optional stemming; fast batch evaluation.
- **Whoosh** — Python-native inverted index with BM25F variant.

For FTS5, tokenise queries the same way: pass the French query string directly. The `unicode61` tokenizer handles accent normalisation.

Key implementation decisions:
- French stopword removal (optional — FTS5 does not strip stopwords by default)
- Stemming (Snowball French stemmer may help recall)
- Field weighting: consider weighting `article_text` + `law_code` + `chapter_title` separately

### Stage 2 — Dense Retrieval (Bi-encoder)

**Goal:** Embed all articles and queries; retrieve by cosine similarity (ANN).

Recommended embedding models for French legal text:
| Model | Notes |
|---|---|
| `antoinelouis/colbert-xm` | ColBERT multilingual, late interaction |
| `intfloat/multilingual-e5-large` | Strong multilingual bi-encoder |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Solid baseline |
| `dangvantuan/sentence-camembert-large` | French-specific |
| `mistral-embed` (via API) | Larger context, API cost |

Implementation steps:
1. Embed all articles in `bsard_articles_only.parquet` (use `article_text` column)
2. Store embeddings in a vector store (FAISS, ChromaDB, or LanceDB)
3. At query time: embed the question, retrieve top-k by cosine similarity
4. Map results back to `article_id` for evaluation

Batch embedding:
```python
import pandas as pd
from sentence_transformers import SentenceTransformer

df = pd.read_parquet("output/bsard_articles_only.parquet")
model = SentenceTransformer("intfloat/multilingual-e5-large")

# E5 models require prefix
texts = ["passage: " + t for t in df["article_text"].fillna("")]
embeddings = model.encode(texts, batch_size=64, show_progress_bar=True,
                          normalize_embeddings=True)
```

### Stage 3 — Hybrid Retrieval

**Goal:** Combine BM25 and dense scores via score fusion.

Fusion strategies:
- **Reciprocal Rank Fusion (RRF):** `score = Σ 1 / (k + rank_i)` across retrievers (k=60 standard). Simple, no calibration needed.
- **Linear interpolation:** `score = α * bm25_score + (1-α) * dense_score`. Requires score normalisation.
- **CombSUM / CombMNZ:** Sum (or sum × number of systems returning the doc) of normalised scores.

Use the train split (886 questions) to tune the fusion weight `α`.

### Stage 4 — Re-ranking (Cross-encoder)

**Goal:** Re-score the top-k candidates from Stage 2/3 using a cross-encoder that reads both query and article jointly.

Recommended cross-encoders:
| Model | Notes |
|---|---|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Fast, English-trained — use as sanity check |
| `amberoad/bert-multilingual-passage-reranking-msmarco` | Multilingual cross-encoder |
| `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | mMARCO multilingual |

Apply to top-100 candidates from the retriever; re-rank to produce final top-10 for MRR/NDCG.

### Stage 5 — Advanced RAG Ablations (RQ2)

Five ablations measuring what each corpus feature contributes to retrieval quality:

#### 5.1 Chunking ablation

Articles have median 133 tokens (p95 = 798). Some articles are long enough to benefit from chunking. Compare:
- **No chunking** — embed whole article (baseline)
- **Fixed-size chunks** — 256 / 512 tokens with 50-token overlap
- **Sentence-boundary chunks** — split at sentence boundaries respecting `token_count`
- **Structural chunks** — use `hierarchy_path` to split at paragraph or section boundaries

Evaluation: map chunk results back to `article_id` for evaluation (a chunk is relevant if its parent article is relevant).

#### 5.2 Metadata filtering

Use `law_code`, `law_type`, `is_pre_bsard`, or `amendment_date` to restrict retrieval scope before or during ANN search. Implement as pre-filter (filter the index) or post-filter (filter retrieved results).

Example: if the question is about employment law, filter to `law_code = 'Code du Bien-être au Travail'`.

This requires a query classification step (or metadata prediction from the query).

#### 5.3 Hierarchical context (PageIndex)

Instead of embedding only `article_text`, prepend the `hierarchy_path` and heading titles as context:

```python
def build_indexed_text(row) -> str:
    path = json.loads(row["hierarchy_path"]) if row["hierarchy_path"] else []
    header = " > ".join(path[:-1])  # exclude the article entry itself
    return f"{header}\n\n{row['article_text']}"
```

Compare retrieval quality with vs. without structural context prepended.

#### 5.4 HyDE (Hypothetical Document Embedding)

Generate a hypothetical answer to the query using an LLM, then embed the hypothetical answer instead of the query. The idea: hypothetical answers are written in the same register as legal articles.

```python
# Generate hypothetical answer
hyp_doc = llm.generate(f"Répondez à cette question juridique: {question}")
# Embed the hypothetical doc
query_embedding = model.encode("passage: " + hyp_doc)
```

#### 5.5 GraphRAG — Citation Neighbourhood Expansion

After initial retrieval, expand the candidate set using the citation graph:

```python
import json, sqlite3

def expand_with_citations(article_ids: list[int], conn, hops: int = 1) -> set[int]:
    expanded = set(article_ids)
    frontier = set(article_ids)
    for _ in range(hops):
        new_frontier = set()
        for aid in frontier:
            row = conn.execute(
                "SELECT cross_reference_ids, cited_by_ids FROM articles WHERE article_id = ?",
                (aid,)
            ).fetchone()
            if row:
                out = json.loads(row["cross_reference_ids"] or "[]")
                inc = json.loads(row["cited_by_ids"] or "[]")
                new_frontier.update(out + inc)
        new_frontier -= expanded
        expanded.update(new_frontier)
        frontier = new_frontier
    return expanded
```

The citation graph has 27,712 edges. Max in-degree = 269 (Art.2, Code des Sociétés et des Associations). Neighbour expansion can generate large candidate sets — apply re-ranking after expansion.

---

## 6. Project Structure (Suggested)

```
Retrieval/                          ← New project root
│
├── retrieval/
│   ├── sparse.py                   ← Stage 1: BM25 / FTS5 retriever
│   ├── dense.py                    ← Stage 2: bi-encoder + FAISS/vector store
│   ├── hybrid.py                   ← Stage 3: RRF / score fusion
│   ├── rerank.py                   ← Stage 4: cross-encoder re-ranker
│   └── graph.py                    ← Stage 5.5: citation graph expansion
│
├── ablations/
│   ├── chunking.py                 ← Stage 5.1: chunking strategies
│   ├── metadata_filter.py          ← Stage 5.2: metadata pre/post filtering
│   ├── hierarchical_context.py     ← Stage 5.3: PageIndex / hierarchy prepend
│   └── hyde.py                     ← Stage 5.4: Hypothetical Document Embedding
│
├── evaluation/
│   ├── metrics.py                  ← Recall@k, MRR@10, NDCG@10
│   ├── run_eval.py                 ← Batch evaluation runner
│   └── results/                    ← Per-experiment JSON result files
│
├── analysis/
│   └── results_comparison.ipynb   ← Cross-experiment comparison notebook
│
├── CLAUDE.md                       ← Project rules
└── README.md                       ← Retrieval project overview
```

---

## 7. Data Access Patterns

### Load questions for evaluation

```python
import sqlite3, json

DB = "path/to/output/bsard_corpus.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

test_questions = {
    row["question_id"]: {
        "text":       row["question_text"],
        "ground_truth": json.loads(row["relevant_article_ids"]),
    }
    for row in conn.execute(
        "SELECT question_id, question_text, relevant_article_ids "
        "FROM questions WHERE split = 'test'"
    )
}
```

### Load articles for indexing

```python
import pandas as pd

# BSARD subset only (for retrieval index)
df = pd.read_parquet("path/to/output/bsard_articles_only.parquet",
                     columns=["article_id", "bsard_id", "law_code",
                               "article_number", "article_text",
                               "token_count", "hierarchy_path",
                               "chapter_title", "section_title"])

df = df[df["article_text"].notna()]   # drop the 1,338 failed extractions
```

### Access citation neighbours

```python
import json

def get_neighbours(article_id: int, conn) -> dict:
    row = conn.execute(
        "SELECT cross_reference_ids, cited_by_ids FROM articles WHERE article_id = ?",
        (article_id,)
    ).fetchone()
    return {
        "outgoing": json.loads(row["cross_reference_ids"] or "[]"),
        "incoming": json.loads(row["cited_by_ids"] or "[]"),
    }
```

---

## 8. Environment and Storage Rules

- **Virtual environment:** always execute scripts inside the project-local `.venv/`
- **Large files:** vector store indices, embedding files, and result dumps go to OneDrive, not the Git repo
- **Database:** treat `output/bsard_corpus.db` as **read-only** from this project — never write to it
- **Parquet/JSONL files:** also read-only — source data from the corpus project
- **Result files:** save per-experiment results as JSON in `evaluation/results/` and commit to Git (they are small)
- **Model weights:** do not commit to Git; download on first use from HuggingFace Hub

---

## 9. Research Questions

| RQ | Question | Stages |
|---|---|---|
| **RQ1** | How do sparse, dense, and hybrid retrieval methods compare on the BSARD benchmark in terms of Recall@k, MRR, and NDCG? | Stages 1–4 |
| **RQ2** | To what extent do corpus-specific features (article structure, citation links, temporal metadata) improve retrieval over the baseline? | Stage 5 ablations |
| **RQ3** | What failure conditions (multi-article questions, cross-reference dependencies, article length) most affect retrieval quality? | §4.5 stratified analysis |

---

## 10. Corpus Provenance — Encoding Note

`bsard_full_verify.csv` (the source of `law_code`, metadata) is **UTF-8 encoded**. Always read with `encoding="utf-8"`. An earlier bug (reading as `latin-1`) caused garbled law code names (e.g. "DÃ©mocratie"); this has been corrected in both the pipeline and the database. If you encounter any `Ã` characters in law code strings, apply `s.encode('latin-1').decode('utf-8')` to fix them.
