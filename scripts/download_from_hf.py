"""Download the bsard2currentlawmatching dataset from Hugging Face into ./output/.

Pulls the published SQLite databases, Parquet exports, JSONL exports, source
PDFs, and intermediate artifacts into the local `output/` directory so the
pipeline and analysis notebooks can run without re-building.

Usage:
    python scripts/download_from_hf.py
    python scripts/download_from_hf.py --repo OTHER/REPO --revision v1
    python scripts/download_from_hf.py --include "*.parquet" "*.db"

Requires `huggingface_hub` (already pinned in requirements.txt).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO_ID = "MariusPasch/bsard2currentlawmatching"
DEFAULT_LOCAL_DIR = PROJECT_ROOT / "output"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=DEFAULT_REPO_ID,
                        help=f"HF dataset repo id (default: {DEFAULT_REPO_ID})")
    parser.add_argument("--revision", default=None,
                        help="Optional branch / tag / commit hash")
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_DIR,
                        help=f"Where to mirror the dataset (default: {DEFAULT_LOCAL_DIR})")
    parser.add_argument("--include", nargs="*", default=None,
                        help="Glob patterns to selectively download (default: everything)")
    args = parser.parse_args()

    args.local_dir.mkdir(parents=True, exist_ok=True)

    path = snapshot_download(
        repo_id=args.repo,
        repo_type="dataset",
        revision=args.revision,
        local_dir=str(args.local_dir),
        allow_patterns=args.include,
    )
    print(f"Dataset mirrored into: {path}")


if __name__ == "__main__":
    main()
