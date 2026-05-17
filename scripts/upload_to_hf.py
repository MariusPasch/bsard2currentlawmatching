"""Upload the local ./output/ artifacts to the bsard2currentlawmatching HF dataset.

Mirrors the local `output/` directory to a Hugging Face dataset repo so the
SQLite databases, Parquet exports, JSONL exports, and source PDFs can be
downloaded by anyone via `scripts/download_from_hf.py`.

Authentication: run `huggingface-cli login` once, or set the HF_TOKEN env var
to a token that has write access to the target repo.

Usage:
    python scripts/upload_to_hf.py                       # dry-run plan first
    python scripts/upload_to_hf.py --confirm             # actually upload
    python scripts/upload_to_hf.py --confirm --create    # also create the repo
    python scripts/upload_to_hf.py --repo OTHER/REPO --confirm

Requires `huggingface_hub` (already pinned in requirements.txt).
"""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path

from huggingface_hub import HfApi, create_repo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO_ID = "mpaschalidis/bsard2currentlawmatching"
DEFAULT_LOCAL_DIR = PROJECT_ROOT / "output"

# Always ignored on upload:
#   - local SQLite WAL/SHM sidecars and OS junk
#   - cache/ and logs/ (local-only working directories)
#   - artifacts that belong to the downstream retrieval project, not this corpus project:
#     embeddings/, results/, llm_judge_cache_*.json
DEFAULT_IGNORE = [
    "*.db-wal",
    "*.db-shm",
    ".DS_Store",
    "Thumbs.db",
    "cache/**",
    "logs/**",
    "embeddings/**",
    "results/**",
    "llm_judge_cache_*.json",
]


def human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def is_ignored(rel_posix: str, patterns: list[str]) -> bool:
    """Mirror HfApi.upload_folder semantics for ignore_patterns matching."""
    name = rel_posix.split("/")[-1]
    for pat in patterns:
        if fnmatch.fnmatch(rel_posix, pat) or fnmatch.fnmatch(name, pat):
            return True
        if pat.endswith("/**") and (
            rel_posix.startswith(pat[:-3] + "/") or rel_posix == pat[:-3]
        ):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=DEFAULT_REPO_ID,
                        help=f"HF dataset repo id (default: {DEFAULT_REPO_ID})")
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_DIR,
                        help=f"Local source directory (default: {DEFAULT_LOCAL_DIR})")
    parser.add_argument("--commit-message", default="Sync local output/ to HF dataset",
                        help="Commit message to record on the dataset repo")
    parser.add_argument("--create", action="store_true",
                        help="Create the dataset repo if it does not exist")
    parser.add_argument("--private", action="store_true",
                        help="Make the repo private when creating (default: public)")
    parser.add_argument("--confirm", action="store_true",
                        help="Actually upload. Without this flag, only prints a plan.")
    args = parser.parse_args()

    if not args.local_dir.exists():
        raise SystemExit(f"Local dir not found: {args.local_dir}")

    all_files = [p for p in args.local_dir.rglob("*") if p.is_file()]
    kept, skipped = [], []
    for p in all_files:
        rel = p.relative_to(args.local_dir).as_posix()
        (skipped if is_ignored(rel, DEFAULT_IGNORE) else kept).append(p)
    total_keep = sum(p.stat().st_size for p in kept)
    total_skip = sum(p.stat().st_size for p in skipped)
    print(f"Local source : {args.local_dir}")
    print(f"Target repo  : {args.repo} (dataset)")
    print(f"Ignored      : {', '.join(DEFAULT_IGNORE)}")
    print(f"Will upload  : {len(kept)} files ({human_bytes(total_keep)})")
    print(f"Will skip    : {len(skipped)} files ({human_bytes(total_skip)})")

    if not args.confirm:
        print("\nDry run only. Re-run with --confirm to upload.")
        return

    api = HfApi()
    if args.create:
        create_repo(args.repo, repo_type="dataset", private=args.private, exist_ok=True)
        print(f"Ensured dataset repo exists: {args.repo}")

    api.upload_folder(
        repo_id=args.repo,
        repo_type="dataset",
        folder_path=str(args.local_dir),
        commit_message=args.commit_message,
        ignore_patterns=DEFAULT_IGNORE,
    )
    print("Upload complete.")


if __name__ == "__main__":
    main()
