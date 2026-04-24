# Feasibility Report — Pushing Non-BSARD Article Extraction Beyond 40,231

**Author:** Claude (investigation for Marios Paschalidis)
**Date:** 2026-04-23
**Scope:** read-only inspection of [pipeline/](pipeline/), [CORPUS_DATABASE_PROJECT.md](CORPUS_DATABASE_PROJECT.md), and [output/bsard_corpus.db](output/bsard_corpus.db).

---

## 1. How the pipeline currently discovers articles

### 1.1 Extraction mechanism ([pipeline/extract_articles_from_pdf.py](pipeline/extract_articles_from_pdf.py))

Phase A opens each PDF with PyMuPDF and iterates **block-by-block** (not line-by-line). Per block:

1. **Structural-heading test** — regex match against 10 French/Dutch markers (`LIVRE/BOEK`, `TITRE/TITEL`, `CHAPITRE/HOOFDSTUK`, `SECTION/AFDELING`, `SOUS-SECTION/ONDERAFDELING`), guarded by font-size ≥ body_size − 1 to filter footnotes ([extract_articles_from_pdf.py:283-310](pipeline/extract_articles_from_pdf.py#L283-L310)). If matched, any open article is flushed and the hierarchy state is updated (levels below are cleared).
2. **Article-marker test** — `^\s*Art\.?\s+([A-Z0-9][A-Z0-9_./-]*)` anchored to the **start of the block** ([extract_articles_from_pdf.py:37-40, 219-225](pipeline/extract_articles_from_pdf.py#L37-L40)). If matched, the previous article is flushed and a new accumulator starts; any trailing text on that same block is captured as the opening line.
3. **Otherwise** — the block text is appended to `state["article_lines"]` and its page number recorded.

At flush time the accumulator is serialised with the current `(law_title_text, chapter_title, section_title, subsection_title)`, a `hierarchy_path` JSON array, page range, numac, and an `article_text_source` flag: `pdf_extracted` (non-empty body) or `pdf_extraction_failed` (empty body).

### 1.2 BSARD vs non-BSARD tagging ([pipeline/link_bsard.py](pipeline/link_bsard.py))

A Phase A article becomes **BSARD** only inside Phase B. For each extracted article the linker tries three successively looser matches keyed by `pdf_filename` + `article_number`:

1. Exact normalised match ([link_bsard.py:204-207](pipeline/link_bsard.py#L204-L207))
2. Leading-integer match, accepted only if unique in that PDF ([link_bsard.py:209-215](pipeline/link_bsard.py#L209-L215))
3. Base-article match (strips `-N` sub-paragraph and `_REGION_X` suffixes) ([link_bsard.py:217-230](pipeline/link_bsard.py#L217-L230))

If any match hits → `is_bsard_article = 1`, `bsard_id` populated, `article_text` **overridden with HuggingFace canonical text**, `article_text_source = bsard_dataset`, and all verify-CSV fields (`pdf_url`, `law_type`, `verification_status`, etc.) are merged in. Otherwise → `is_bsard_article = 0`, PDF-extracted text kept, `law_code` set to the *dominant* law code of that PDF ([link_bsard.py:180-184, 253-267](pipeline/link_bsard.py#L180-L184)).

**So `is_bsard_article` is entirely a *linkage* attribute set by Phase B — Phase A does not distinguish them.** Non-BSARD = "Phase A found something, Phase B could not reconcile it to a BSARD CSV row."

### 1.3 Multi-book PDFs (Code Judiciaire, Code Civil, Code d'Instruction Criminelle)

These are one PDF per book — not a consolidated multi-book PDF. The parent project's URL list already splits them:

| Code | PDFs | Example rows |
|---|---|---|
| Code Civil | 6 (`1804032150_F` … `1804032155_F`) | Book 1: 944, Book 3: 586, … |
| Code Judiciaire | 8 (`1967101052_F` … `1967101064_F`) | Part 3: 1,225, Part 5: 1,275, … |
| Code d'Instruction Criminelle | 6 (`18081117..` … `18081216..`) | 305, 168, 248, 202, 190, 74 |

Because each book is its own PDF, article-number restarts are disambiguated by `pdf_filename`. The Phase B lookup `exact_lookup[pdf_filename][norm_art_no]` is scoped **per PDF**, so overlap like `Art. 1` appearing in multiple Civil Code books resolves correctly.

### 1.4 Hierarchy for non-BSARD articles

Non-BSARD articles do **not** inherit anything from BSARD — they get their hierarchy metadata directly from Phase A's running state (`law_title_text`, `chapter_title`, `section_title`, `subsection_title`) captured at the moment the article was flushed ([extract_articles_from_pdf.py:172-206](pipeline/extract_articles_from_pdf.py#L172-L206)). The `law_code` is the PDF's dominant BSARD-derived code, which is the only field that is "inherited" ([link_bsard.py:180-184](pipeline/link_bsard.py#L180-L184)).

Non-BSARD hierarchy coverage is actually solid:

| hierarchy_depth | non-BSARD count |
|---|---|
| 0 (rootless) | 3 |
| 1 (law title only) | 770 |
| 2 (law + chapter) | 2,686 |
| 3 (law + chapter + section) | 2,428 |
| 4 (full) | 603 |

**88% of non-BSARD articles have ≥ chapter-level context.**

---

## 2. Current coverage

### 2.1 Headline figures (queried from [output/bsard_corpus.db](output/bsard_corpus.db))

| Metric | Value |
|---|---|
| Total rows | 40,231 |
| `is_bsard_article = 1` | 33,741 |
| `is_bsard_article = 0` | 6,490 |
| `article_text_source = bsard_dataset` | 33,741 |
| `article_text_source = pdf_extracted` | 5,152 |
| `article_text_source = pdf_extraction_failed` | 1,338 |
| Unique `bsard_id` | 22,633 |
| Unique `(pdf_filename, article_number)` | 30,524 |
| BSARD rows with `hierarchy_depth = 0` (Phase B append stubs) | 5,979 |

### 2.2 Hidden duplication — important

The 40,231 figure materially overstates unique-article coverage:

- **5,795 distinct `(pdf_filename, article_number)` keys appear more than once** → 14,308 total duplicate rows (≈ 35% of the corpus).
- Most are BSARD articles with multiple physical occurrences in the same PDF: table of contents + body + sometimes a regional-variant block. Average duplication rate per duplicated BSARD ID: **3.24 rows**.
- The corpus effectively contains ~22,633 unique BSARD articles + ~3,829 unique non-BSARD `article_text` values ≈ **~26,500 genuinely distinct article bodies**.
- An `output/bsard_articles_dedup.parquet` file already exists, suggesting this has been partly noticed.

### 2.3 Per-PDF spot-check (4 representative PDFs)

Comparing DB counts to a raw `^\s*Art\.\s+` MULTILINE regex scan over `page.get_text()` of each PDF:

| PDF | Law | Raw anchored `Art.` unique nums | DB distinct `article_number` | DB rows | `pdf_extraction_failed` |
|---|---|---|---|---|---|
| `1804032150_F` | Code Civil (Book 1) | 792 | 810 | 944 | 4 |
| `1967101053_F` | Code Judiciaire (part 3) | 1,034 | 1,031 | 1,225 | 23 |
| `1867060850_F` | Code Pénal | 972 | 980 | 1,051 | 8 |
| `2016A05561_F` | Code Wallon du Développement Territorial | 813 | 902 | 1,612 | 173 |

For Code Judiciaire, the 14 numbers in the raw-regex-but-not-in-DB set are things like `1, 2, 3, 5, 8, 14, 17, 29, 31, 36, 37, 38, 39, 50` — inspection showed these are **not missed articles**. They are line-wrapped amendment markers of the form `<L 1990-07-26/31,\nart. 1, 016; En vigueur : ...>` where "art. 1" happens to land at a line start inside a Justel amendment annotation. The pipeline correctly skips them because in PyMuPDF block-level text they are inside a continuation block, not at block-start. Code Pénal had the same pattern — only 1 spurious "missed" number.

**Key conclusion: the current pipeline already matches or exceeds the flat regex as a ceiling.** The "distinct `article_number`" column above is ≥ the raw-regex unique-number column in every PDF checked. There is no meaningful population of articles that the regex sees and the pipeline doesn't.

---

## 3. Gap analysis — what is still missing?

Breaking down the 1,338 `pdf_extraction_failed` rows:

| Pattern | Count | What it is |
|---|---|---|
| Range headers (`"172-179"`, `"1.4.5-5-1.4.5-11"`) | 894 | Abrogated/repealed article ranges. Justel renders these as one heading with no body — **there is no text to extract**. Not a pipeline gap. |
| Regional / community variants (`"1714_REGION_WALLONNE"`, `"100_COMMUNAUTE_GERMANOPHONE"`) | 307 | The sub-variant is detected but its body didn't accumulate — usually because a `SECTION`/`CHAPITRE` heading appearing between `Art. N_REGION_X.` and the body flushed the article early. ~220 already have a text-bearing twin in the DB. |
| Abrogated single articles (`228`, `1333`, `1348bis`) with only `<Abrogé par L ...>` body | ~90 | The abrogation marker body should have been captured but wasn't. Inspection of `Art. 1333` shows **it IS captured — in a second DB row from the later page (p17)**. The failed row is the **table-of-contents phantom** from the early-page TOC list. |
| Misclassified CHAPITRE/SECTION heading leaked as article_number (e.g. `"CHAPITRE 13/1. [1 - Définitions…]1"`) | ~2 | Genuine parser bug: the `CHAPITRE` regex requires `CHAPITRE [IVX]+|\d+` but this case uses `13/1` with trailing bracketed metadata — font-size check didn't filter it out. |

**618 of 1,338 failures have a successfully-extracted twin elsewhere in the same PDF with non-empty text.** So roughly half of all "extraction failures" are phantoms duplicating a real article — they *reduce* corpus quality, not expand it.

### 3.1 The real gap: Phase A → B linkage, not Phase A extraction

5,979 BSARD articles have `hierarchy_depth = 0`, which is the signature of a Phase B append stub. Top contributors:

| PDF | Law | Stubs appended |
|---|---|---|
| `2017A10461_F` | Code du Bien-être au Travail | 1,238 |
| `<NULL>` | Code des Sociétés et des Associations | 1,194 (no PDF at all on Justel — `pdf_url='nan'`) |
| `2004A27184_F` | Code de la Démocratie Locale | 1,003 |
| `2004A27101_F` | Code de l'Eau / Env. Wallon | 675 + 335 |
| `2016A05561_F` | Code Wallon du Développement Territorial | 293 |
| `2019A30854_F` | Code Wallon Enseignement Fondamental | 267 |

For the 1,194 Code des Sociétés rows, **no PDF exists** on Justel for that code. Nothing to extract; they will always be HF-text-only stubs.

For the other ~4,785 stubs, the text is almost certainly already in the DB — it was extracted by Phase A into a non-BSARD row under a slightly different article-number format (e.g. `I.1-1` vs `1.1` vs `1-1`), and none of Phase B's three fallbacks bridged the gap. These show up as **non-BSARD rows for codes like Code du Bien-être au Travail**, where Walloon-style codified numbering (`I.1-1`, `II.3-5`) is common.

---

## 4. Extension feasibility

| # | Candidate extension | What it would buy | Where it plugs in | Effort | Risk |
|---|---|---|---|---|---|
| **4.1** | **Deduplicate TOC phantoms** (same `(pdf_filename, article_number)` with empty vs non-empty text → keep the non-empty one) | Removes ~618 phantom rows; reduces corpus by ~8–14k duplicate rows in total if generalised | Post-processing pass after Phase A or during Phase D SQL insert | **Minor** — a few SQL/pandas lines | Low; already implied by existence of `bsard_articles_dedup.parquet`. Unlocks cleaner distractor pool for retrieval eval. |
| **4.2** | **Tighten Phase B linkage** — add 4th fallback that strips Walloon/CoBAT numbering separators (`I.1-1` ↔ `I.1.1` ↔ `1.1-1`) | Reassigns ~4,000+ of the 5,979 BSARD stubs to their PDF-extracted row; reclaims hierarchy + page metadata for them | [link_bsard.py:190-268](pipeline/link_bsard.py#L190-L268) — add one more fallback branch | **Minor** — 20–40 lines of regex normalisation, no schema change | Medium — risk of false links; needs unit tests against a held-out sample from a few Walloon codes. Does **not** add new rows, but substantially improves Graph RAG metadata. |
| **4.3** | **Capture `<Abrogé ...>` bodies as structured metadata** (`is_abrogated`, `abrogation_law`, `abrogation_date`) | Adds meaningful content to ~720 currently-empty rows; avoids Phase A flushing on the interceding SECTION header | Phase A block loop + new columns in schema | **New pipeline stage** — regex + schema migration + re-run Phase D | Medium — easy to parse, but requires schema extension the downstream retrieval project would need to accept. |
| **4.4** | **TOC-detection heuristic** (first N pages, densely spaced `Art. X` entries without bodies → skip or tag `is_toc_entry`) | Prevents creation of phantom articles upstream; cleaner alternative to (4.1) | Phase A, new pre-pass on first 5–10 pages | **Small** — 50-line helper using font-size + density signals | Medium — over-aggressive skip could drop legitimate short articles that sit on early pages. |
| **4.5** | **Cross-PDF citation resolution / fixing bracket-headings** (e.g. `CHAPITRE 13/1. [1 - …]1`) | Fixes ~2 parser bugs, negligible coverage lift | Tweak `CHAPITRE` regex in [extract_articles_from_pdf.py:48](pipeline/extract_articles_from_pdf.py#L48) | Trivial | Low |
| **4.6** | **OCR fallback for image-based pages** (`pytesseract` on pages where `page.get_text()` returns < X chars) | Would catch any image-only Justel pages | New Phase A branch; requires Tesseract install | **Substantial** — adds a non-Python system dependency and noise | **High** — every PDF sampled already yields clean text. Spot-check shows **no image-only pages**. Likely zero real return. |
| **4.7** | **Scrape Justel HTML per-article for missed content** | Would provide canonical text for Code des Sociétés (1,194 articles) and any other HF gap | New fetcher script, leverages existing `justel_html_url` | **New pipeline stage** | High — rate-limited HTTP, HTML parsing variance across Justel page types. But HF already provides the canonical body text for Code des Sociétés, so the only real gain is hierarchy metadata. |

---

## 5. Recommendation

**The existing 40,231 is at or above the practical ceiling for distinct articles extractable from these 49 PDFs.** Every spot-check confirmed the pipeline finds at least as many article numbers as a flat regex over raw PDF text, and the few "misses" flagged by the regex are amendment-annotation false positives, not real articles. The PDFs simply do not contain a large reservoir of articles the pipeline hasn't seen.

What the corpus does have, in order of leverage-per-effort:

1. **(4.1) Phantom-duplicate cleanup** — highest priority. Roughly **8,000–14,000 rows** are TOC duplicates or otherwise redundant. Fixing this strictly improves retrieval evaluation quality (cleaner distractor pool, no inflated Recall denominators). Effort: minor. Already partly done in `bsard_articles_dedup.parquet` — worth promoting into the main DB build.

2. **(4.2) Linkage fallback for Walloon/CoBAT numbering** — second priority. ~4,000 BSARD articles sit as Phase B stubs *despite* having an extracted counterpart in the DB under a slightly-different article-number spelling. Fixing this doesn't add rows, but it promotes thousands of BSARD articles from "text-only stub" to "full hierarchy + pages + neighbours" — directly improving Stage 5.3 PageIndex and Stage 5.5 Graph RAG inputs. Effort: minor.

Skip (4.3)–(4.7). Their real-coverage yield is small: ~720 abrogation-only articles (which carry almost no retrieval signal), ~2 parser bugs, zero OCR benefit, and redundant HF scraping.

**Go/no-go:** don't chase coverage beyond 40k. Do invest a focused session in (4.1) + (4.2) — they tighten what's already there, make the non-BSARD distractor set honest, and reclaim ~4k BSARD articles as first-class nodes for Graph RAG. That's the best thesis-timeline value available from the extraction side; any further time is better spent on the downstream retrieval experiments.
