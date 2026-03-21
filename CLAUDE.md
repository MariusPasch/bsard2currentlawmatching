# Project Rules for Claude Code

## Python Environment

- **Always execute Python scripts inside the local virtual environment** located at `.venv/` in this project root.
- Activate it before running any script:
  ```bash
  # Windows
  .venv\Scripts\activate

  # macOS / Linux
  source .venv/bin/activate
  ```
- When installing new packages, install them into the local venv and update `requirements.txt` immediately:
  ```bash
  pip install <package>
  pip freeze > requirements.txt
  ```
- Never install packages globally or into the system Python.
- The venv directory (`.venv/`) is excluded from version control (see `.gitignore`).

---

## File Storage Rules

### Large files and datasets → OneDrive only

All large files, datasets, and generated outputs must be stored on OneDrive at:

```
OneDrive\Python Project Storage\BSARD_THESIS_DATASET
```

This includes:
- The 49 Justel consolidated PDFs (`output/pdfs/`)
- The SQLite database (`output/bsard_corpus.db`)
- Parquet exports (`output/*.parquet`)
- JSONL exports (`output/*.jsonl`)
- Per-PDF intermediate JSONL files (`output/extracted/*.jsonl`)
- Any other large binary or generated data files

The `output/` directory in the project root is a **directory junction** pointing to the OneDrive location. Do not break or replace this junction.

### Code and configuration files → GitHub repository

All of the following must be committed to the GitHub repository:
- Python scripts (`pipeline/`, `analysis/`)
- Jupyter notebooks
- Configuration files
- Documentation (`.md` files, `.txt` analysis files)
- `requirements.txt`
- `CLAUDE.md`, `README.md`, `CORPUS_DATABASE_PROJECT.md`
- `.gitignore`

Do **not** commit:
- `.venv/` (virtual environment)
- Any file in `output/` (all large outputs go to OneDrive via the junction)
- Any file larger than ~1 MB unless explicitly requested

---

## Project Context

- See [CORPUS_DATABASE_PROJECT.md](CORPUS_DATABASE_PROJECT.md) for the full technical specification of the pipeline and database schema.
- See [README.md](README.md) for the project overview and setup instructions.
- The parent project's data (PDFs, `bsard_full_verify.csv`) is read-only from this project — never modify parent project files.
- BSARD benchmark data is loaded from HuggingFace: `maastrichtlawtech/bsard`.
