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
from huggingface_hub import hf_hub_download
from huggingface_hub import snapshot_download

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
    "--dataset-repo", type=str, default="EthanS38/test_case_dataset",
    help="Hugging Face dataset repo containing eval JSONL and candidate index.",
)
parser.add_argument(
    "--eval-filename", type=str, default="methods2test_eval_embedded.jsonl",
    help="Eval split JSONL filename in the dataset repo.",
)
parser.add_argument(
    "--model-id", type=str, default="EthanS38/test_case_retreival",
    help="Hugging Face model repo for the fine-tuned retriever.",
)
parser.add_argument(
    "--model-subdir", type=str, default="retrieval_model",
    help="Optional subdirectory in the model repo containing SentenceTransformer files.",
)
parser.add_argument("--k", type=int, default=5, help="Top-K to evaluate.")
parser.add_argument("--sample", type=int, default=2000, help="Number of eval queries to sample (0 = all).")
parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling.")
parser.add_argument("--save-results", type=str, default=None, help="Optional path to save results JSON.")

args = parser.parse_args()

emb_path = hf_hub_download(
    repo_id=args.dataset_repo,
    filename="candidate_embeddings.npy",
    repo_type="dataset",
)

try:
    meta_path = hf_hub_download(
        repo_id=args.dataset_repo,
        filename="candidate_metadata-002.jsonl",
        repo_type="dataset",
    )
except Exception:
    meta_path = hf_hub_download(
        repo_id=args.dataset_repo,
        filename="candidate_metadata.jsonl",
        repo_type="dataset",
    )

eval_path = Path(
    hf_hub_download(
        repo_id=args.dataset_repo,
        filename=args.eval_filename,
        repo_type="dataset",
    )
)

# load candidate pool
print("Loading candidate embeddings ...")
candidate_matrix = np.load(str(emb_path)).astype("float32")
metadata = load_metadata(meta_path)
candidate_lookup = build_candidate_lookup(metadata)
print(f"  {candidate_matrix.shape[0]} candidates, {len(candidate_lookup)} unique texts")

# load fine-tuned model
snapshot_dir = Path(snapshot_download(repo_id=args.model_id, repo_type="model"))
candidate_model_dir = snapshot_dir / args.model_subdir
model_dir = candidate_model_dir if (candidate_model_dir / "modules.json").exists() else snapshot_dir
print(f"Loading fine-tuned model from {model_dir} ...")
model = SentenceTransformer(str(model_dir))

results = evaluate(
    model=model,
    candidate_matrix=candidate_matrix,
    candidate_lookup=candidate_lookup,
    eval_path=eval_path,
    sample_size=args.sample if args.sample > 0 else None,
    k=args.k,
    seed=args.seed,
)

if args.save_results:
    out = Path(args.save_results)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"Results saved to {out}")
