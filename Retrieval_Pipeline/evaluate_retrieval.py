# evaluate_retrieval.py
# author: Ethan Soroko
#
# Evaluates retrieval quality of the fine-tuned model on the eval (or test) split.
# Each example has a known focal-method ↔ test-case pair, so we can measure
# whether the correct test case appears in the Top-K results.
#
# Metrics: Hit@K, MRR@K, Precision@K

from __future__ import annotations

import argparse
import json
import random
import numpy as np
import torch
from pathlib import Path
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer, util


def stream_jsonl(path: Path):
    """Yield (line_index, parsed dict) from a JSONL file."""
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                yield i, json.loads(line)


def load_metadata(path: Path) -> List[Dict[str, Any]]:
    """Load metadata JSONL."""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_candidate_lookup(metadata: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    """Map candidate_text → list of indices in the candidate pool."""
    lookup: Dict[str, List[int]] = {}
    for idx, m in enumerate(metadata):
        text = m.get("candidate_text", "")
        lookup.setdefault(text, []).append(idx)
    return lookup


def evaluate(
    model: SentenceTransformer,
    candidate_matrix: np.ndarray,
    candidate_lookup: Dict[str, List[int]],
    eval_path: Path,
    sample_size: int | None,
    k: int,
    seed: int,
):
    """Run evaluation and return metrics."""
    # collect eval examples
    eval_examples = []
    for _, row in stream_jsonl(eval_path):
        q = row.get("query_text", "").strip()
        c = row.get("candidate_text", "").strip()
        if q and c:
            eval_examples.append({"query_text": q, "candidate_text": c})

    if not eval_examples:
        raise RuntimeError(f"No valid examples in {eval_path}")

    if sample_size and sample_size < len(eval_examples):
        rng = random.Random(seed)
        eval_examples = rng.sample(eval_examples, sample_size)

    total = len(eval_examples)
    print(f"Evaluating {total} queries against {candidate_matrix.shape[0]} indexed candidates (K={k})")

    # encode all eval queries in one batch
    query_texts = [ex["query_text"] for ex in eval_examples]
    print("Encoding eval queries ...")
    query_vecs = model.encode(
        query_texts,
        batch_size=128,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    # run similarity search
    corpus_tensor = torch.from_numpy(candidate_matrix)
    query_tensor = torch.from_numpy(query_vecs)

    print("Running similarity search ...")
    all_hits = util.semantic_search(query_tensor, corpus_tensor, top_k=k)

    hits = 0
    reciprocal_ranks = []

    for i, (ex, hit_list) in enumerate(zip(eval_examples, all_hits)):
        correct_indices = set(candidate_lookup.get(ex["candidate_text"], []))
        retrieved_ids = [h["corpus_id"] for h in hit_list]

        found_rank = None
        for rank, idx in enumerate(retrieved_ids, start=1):
            if idx in correct_indices:
                found_rank = rank
                break

        if found_rank is not None and found_rank <= k:
            hits += 1
        reciprocal_ranks.append(1.0 / found_rank if found_rank else 0.0)

    hit_at_k = hits / total
    mrr = sum(reciprocal_ranks) / total

    print(f"\n{'=' * 40}")
    print(f"  Hit@{k}:       {hit_at_k:.4f}  ({hits}/{total})")
    print(f"  MRR@{k}:       {mrr:.4f}")
    print(f"{'=' * 40}")

    return {"hit_at_k": hit_at_k, "mrr": mrr, "k": k, "n": total}


parser = argparse.ArgumentParser(
    description="Evaluate the fine-tuned retrieval model using ground-truth pairs."
)
parser.add_argument(
    "--eval-file", type=str, default="processed/methods2test_eval_embedded.jsonl",
    help="Path to the eval split JSONL.",
)
parser.add_argument(
    "--index-dir", type=str, default="processed",
    help="Directory containing candidate_embeddings.npy and candidate_metadata.jsonl.",
)
parser.add_argument(
    "--model-dir", type=str, default="models/retrieval_model",
    help="Path to the fine-tuned model directory.",
)
parser.add_argument("--k", type=int, default=5, help="Top-K to evaluate.")
parser.add_argument("--sample", type=int, default=2000, help="Number of eval queries to sample (0 = all).")
parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling.")
parser.add_argument("--save-results", type=str, default=None, help="Optional path to save results JSON.")

args = parser.parse_args()

index_dir = Path(args.index_dir).resolve()
emb_path = index_dir / "candidate_embeddings.npy"
meta_path = index_dir / "candidate_metadata.jsonl"

if not emb_path.exists():
    raise FileNotFoundError(f"Candidate embeddings not found: {emb_path}")
if not meta_path.exists():
    raise FileNotFoundError(f"Metadata not found: {meta_path}")

# load candidate pool
print("Loading candidate embeddings ...")
candidate_matrix = np.load(str(emb_path)).astype("float32")
metadata = load_metadata(meta_path)
candidate_lookup = build_candidate_lookup(metadata)
print(f"  {candidate_matrix.shape[0]} candidates, {len(candidate_lookup)} unique texts")

# load fine-tuned model
model_dir = Path(args.model_dir).resolve()
print(f"Loading fine-tuned model from {model_dir} ...")
model = SentenceTransformer(str(model_dir))

results = evaluate(
    model=model,
    candidate_matrix=candidate_matrix,
    candidate_lookup=candidate_lookup,
    eval_path=Path(args.eval_file).resolve(),
    sample_size=args.sample if args.sample > 0 else None,
    k=args.k,
    seed=args.seed,
)

if args.save_results:
    out = Path(args.save_results)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"Results saved to {out}")
