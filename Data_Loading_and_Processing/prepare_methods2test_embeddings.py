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
import json
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
    files_seen = 0

    for json_file in iter_json_files(split_dir):
        files_seen += 1
        if max_files is not None and files_seen > max_files:
            break

        try:
            records = load_json_file(json_file)
        except Exception as exc:
            print(f"Skipping {json_file} due to load error: {exc}")
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
                    return examples

            except Exception as exc:
                print(f"Skipping record in {json_file} due to parse error: {exc}")

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

# ---- CLI argument definitions ----
SPLITS = ["train", "eval", "test"]

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

args = parser.parse_args()

methods2test_root = Path(args.methods2test_root).resolve()
output_dir = Path(args.output_dir).resolve()

# ---- Load the embedding model once, reuse across all splits ----
print(f"Loading model: {args.model_name}")
model = SentenceTransformer(args.model_name)

# ---- Process every split (train, eval, test) ----
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
        max_files=None,       # no cap — load every file
        max_examples=None,    # no cap — load every example
        max_chars=args.max_chars,
    )

    if not examples:
        print(f"  No examples found for split '{split}', skipping.")
        continue

    print(f"  Loaded {len(examples)} examples")

    # ---- Embed both sides ----
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

    # ---- Merge embeddings back into each example row ----
    rows: List[Dict[str, Any]] = []
    for ex, query_emb, cand_emb in zip(examples, query_embeddings, candidate_embeddings):
        rows.append(
            {
                **ex,
                "query_embedding": query_emb,
                "candidate_embedding": cand_emb,
            }
        )

    # ---- Save to JSONL ----
    output_path = output_dir / f"methods2test_{split}_embedded.jsonl"
    save_jsonl(output_path, rows)
    print(f"  Saved {len(rows)} rows to: {output_path}")

print(f"\nDone — all splits written to {output_dir}/")