# =============================================================================
# prepare_methods2test_embeddings.py
# author: Ethan Soroko
#
# Loads Methods2Test corpus data, builds text representations of focal methods
# (queries) and test cases (candidates), embeds them using a HuggingFace
# sentence-transformer model, and writes the results to a JSONL file.
# =============================================================================

from __future__ import annotations

import argparse
from collections import deque
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def iter_json_files(split_dir: Path) -> Iterable[Path]:
    """
    Recursively yield all Methods2Test JSON files for a given split directory.
    Example split_dir:
      /path/to/methods2test/corpus/json/train
    """
    if not split_dir.exists():
        raise FileNotFoundError(f"Split directory not found: {split_dir}")

    for path in split_dir.rglob("*_corpus.json"):
        if path.is_file():
            yield path


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------

def load_json_file(path: Path) -> List[Dict[str, Any]]:
    """
    Load one Methods2Test corpus JSON file.
    Some files may contain a JSON list; others may contain a single JSON object.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]

    raise ValueError(f"Unexpected JSON structure in {path}")


# ---------------------------------------------------------------------------
# Text builders — convert raw JSON records into plain-text representations
# that are suitable for embedding.
#
# Actual Methods2Test corpus keys (all flat strings):
#   target         – the test case source
#   src_fm         – focal method only
#   src_fm_fc      – focal method + focal class
#   src_fm_fc_co   – + constructors
#   src_fm_fc_ms   – + method signatures
#   src_fm_fc_ms_ff – + fields / functions
# ---------------------------------------------------------------------------

def build_query_text(record: Dict[str, Any]) -> str:
    """
    Build the retrieval query from the focal-method side.
    Uses src_fm_fc (method + class context) when available,
    falls back to src_fm (method only).
    """
    return (record.get("src_fm_fc") or record.get("src_fm") or "").strip()


def build_candidate_text(record: Dict[str, Any]) -> str:
    """
    Build the candidate test-case text from the test side.
    The 'target' field contains the full test source.
    """
    return (record.get("target") or "").strip()


def truncate_text(text: str, max_chars: int) -> str:
    """Collapse whitespace and hard-truncate to *max_chars* characters."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def format_progress_bar(current: int, total: int, width: int = 32) -> str:
    """Render a fixed-width progress bar for terminal output."""
    if total <= 0:
        return "[" + ("-" * width) + "] 0.000%"

    ratio = min(current / total, 1.0)
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {ratio * 100:7.3f}%"


def format_duration(seconds: float) -> str:
    """Render seconds as h:mm:ss or m:ss for progress output."""
    total_seconds = max(int(seconds), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def print_collection_progress(
    split_name: str,
    files_seen: int,
    total_files: int,
    examples_count: int,
    start_time: float,
    rate: float,
) -> None:
    """Print a single-line collection progress update."""
    progress_bar = format_progress_bar(files_seen, total_files)
    elapsed = max(time.perf_counter() - start_time, 0.0)
    remaining_files = max(total_files - files_seen, 0)
    eta_seconds = remaining_files / rate if rate > 0 else 0.0
    sys.stdout.write(
        "\033[2K\r"
        f"  {split_name}: {progress_bar} {files_seen}/{total_files} files | "
        f"{rate:7.2f} files/s | ETA {format_duration(eta_seconds)} | "
        f"elapsed {format_duration(elapsed)} | {examples_count} examples"
    )
    sys.stdout.flush()


def clear_progress_line() -> None:
    """Clear the current terminal progress line."""
    sys.stdout.write("\033[2K\r")
    sys.stdout.flush()


def compute_recent_rate(samples: deque[tuple[float, int]]) -> float:
    """Estimate file throughput from recent redraw samples."""
    if len(samples) < 2:
        return 0.0

    start_time, start_files = samples[0]
    end_time, end_files = samples[-1]
    elapsed = end_time - start_time
    files_processed = end_files - start_files
    if elapsed <= 0 or files_processed <= 0:
        return 0.0
    return files_processed / elapsed


# ---------------------------------------------------------------------------
# Corpus collection — walk the split directory, parse each JSON file,
# and assemble a flat list of (query, candidate) example dicts.
# ---------------------------------------------------------------------------

def collect_examples(
    split_dir: Path,
    max_files: int | None,
    max_examples: int | None,
    max_chars: int,
) -> List[Dict[str, Any]]:
    """Read corpus files and return a flat list of example dicts."""
    examples: List[Dict[str, Any]] = []
    json_files = list(iter_json_files(split_dir))
    if max_files is not None:
        json_files = json_files[:max_files]

    total_files = len(json_files)

    if total_files == 0:
        return examples

    start_time = time.perf_counter()
    print(f"  Found {total_files} corpus files")
    progress_samples: deque[tuple[float, int]] = deque(maxlen=20)
    progress_samples.append((start_time, 0))
    print_collection_progress(split_dir.name, 0, total_files, len(examples), start_time, 0.0)
    last_redraw = start_time

    for files_seen, json_file in enumerate(json_files, start=1):
        try:
            records = load_json_file(json_file)
        except Exception as exc:
            now = time.perf_counter()
            progress_samples.append((now, files_seen))
            recent_rate = compute_recent_rate(progress_samples)
            clear_progress_line()
            print(f"Skipping {json_file} due to load error: {exc}")
            print_collection_progress(split_dir.name, files_seen, total_files, len(examples), start_time, recent_rate)
            continue

        for record in records:
            try:
                query_text = truncate_text(build_query_text(record), max_chars=max_chars)
                candidate_text = truncate_text(build_candidate_text(record), max_chars=max_chars)

                if not query_text or not candidate_text:
                    continue

                examples.append(
                    {
                        "source_file": str(json_file),
                        "query_text": query_text,
                        "candidate_text": candidate_text,
                        # Keep the richest context variant available
                        "src_fm_fc_ms_ff": truncate_text(
                            (record.get("src_fm_fc_ms_ff") or "").strip(),
                            max_chars=max_chars,
                        ),
                    }
                )

                if max_examples is not None and len(examples) >= max_examples:
                    now = time.perf_counter()
                    progress_samples.append((now, files_seen))
                    recent_rate = compute_recent_rate(progress_samples)
                    print_collection_progress(split_dir.name, files_seen, total_files, len(examples), start_time, recent_rate)
                    print()
                    return examples

            except Exception as exc:
                clear_progress_line()
                print(f"Skipping record in {json_file} due to parse error: {exc}")
                print_collection_progress(split_dir.name, files_seen, total_files, len(examples), start_time)

        now = time.perf_counter()
        if now - last_redraw >= 0.1 or files_seen == total_files:
            progress_samples.append((now, files_seen))
            recent_rate = compute_recent_rate(progress_samples)
            print_collection_progress(split_dir.name, files_seen, total_files, len(examples), start_time, recent_rate)
            last_redraw = now

    print()

    return examples


# ---------------------------------------------------------------------------
# Embedding — encode text lists into normalized vectors via sentence-transformers.
# ---------------------------------------------------------------------------

def embed_texts(
    model: SentenceTransformer,
    texts: List[str],
    batch_size: int = 32,
) -> List[List[float]]:
    """Return a list of normalised embedding vectors for the given texts."""
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write a list of dicts as newline-delimited JSON (JSONL)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ===========================================================================
# Main pipeline — runs directly when the script is executed.
# ===========================================================================

SPLITS = ["train", "eval", "test"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Methods2Test data, embed with a Hugging Face model, and save processed examples."
    )
    parser.add_argument(
        "--methods2test-root",
        type=str,
        required=True,
        help="Path to the local Methods2Test repo root.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="processed",
        help="Directory for output JSONL files (one per split).",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Hugging Face embedding model.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=2000,
        help="Maximum characters kept per text field before embedding.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size.",
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embedding computation — write only text fields (much smaller files).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    methods2test_root = Path(args.methods2test_root).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not args.skip_embeddings:
        print(f"Loading model: {args.model_name}")
        model = SentenceTransformer(args.model_name)
    else:
        print("Skipping embeddings — will write text-only JSONL files.")
        model = None

    for split in SPLITS:
        split_dir = methods2test_root / "corpus" / "json" / split

        if not split_dir.exists():
            print(f"Skipping split '{split}' — directory not found: {split_dir}")
            continue

        print(f"\n{'=' * 60}")
        print(f"Processing split: {split}")
        print(f"Reading from: {split_dir}")

        examples = collect_examples(
            split_dir=split_dir,
            max_files=None,
            max_examples=None,
            max_chars=args.max_chars,
        )

        if not examples:
            print(f"  No examples found for split '{split}', skipping.")
            continue

        print(f"  Loaded {len(examples)} examples")

        if args.skip_embeddings:
            rows = examples
        else:
            print("  Embedding query texts...")
            query_embeddings = embed_texts(
                model=model,
                texts=[ex["query_text"] for ex in examples],
                batch_size=args.batch_size,
            )

            print("  Embedding candidate test texts...")
            candidate_embeddings = embed_texts(
                model=model,
                texts=[ex["candidate_text"] for ex in examples],
                batch_size=args.batch_size,
            )

            rows = []
            for ex, query_emb, cand_emb in zip(examples, query_embeddings, candidate_embeddings):
                rows.append(
                    {
                        **ex,
                        "query_embedding": query_emb,
                        "candidate_embedding": cand_emb,
                    }
                )

        output_path = output_dir / f"methods2test_{split}_embedded.jsonl"
        save_jsonl(output_path, rows)
        print(f"  Saved {len(rows)} rows to: {output_path}")

    print(f"\nDone — all splits written to {output_dir}/")


if __name__ == "__main__":
    main()