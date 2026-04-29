# query_top_k.py
# author: Ethan Soroko
#
# Takes a Java source file (or raw text) as input, encodes it with the
# fine-tuned retrieval model, and retrieves the Top-K most similar test
# cases using cosine similarity against the pre-encoded candidate pool.

from __future__ import annotations

import argparse
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from huggingface_hub import hf_hub_download
from huggingface_hub import snapshot_download

from sentence_transformers import SentenceTransformer, util


def load_metadata(path: Path) -> List[Dict[str, Any]]:
    """Load the metadata JSONL into a list aligned with the embeddings matrix."""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_query_text(source: str) -> str:
    """Read query text from a file path or treat it as inline text."""
    p = Path(source)
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return source


def search(candidate_matrix: np.ndarray, metadata: List[dict], query_vec: np.ndarray, k: int):
    """Cosine similarity search and return ranked results."""
    import torch

    query_tensor = torch.from_numpy(query_vec)
    corpus_tensor = torch.from_numpy(candidate_matrix)

    hits = util.semantic_search(query_tensor, corpus_tensor, top_k=k)[0]

    results = []
    for rank, hit in enumerate(hits, start=1):
        idx = hit["corpus_id"]
        entry = metadata[idx].copy()
        entry["rank"] = rank
        entry["score"] = float(hit["score"])
        results.append(entry)
    return results


def print_results(results: list, verbose: bool):
    """Pretty-print retrieval results."""
    for r in results:
        print(f"\n--- Rank {r['rank']} (score: {r['score']:.4f}) ---")
        if verbose:
            print(f"  Source: {r['source_file']}")
            print(f"  Focal method:\n    {r['query_text'][:300]}")
        print(f"  Test case:\n    {r['candidate_text'][:500]}")


parser = argparse.ArgumentParser(
    description="Query the trained retrieval model with a code file or text and retrieve Top-K test cases."
)
parser.add_argument(
    "input",
    type=str,
    help="Path to a Java/code file, or a quoted string of code to use as the query.",
)
parser.add_argument(
    "--dataset-repo",
    type=str,
    default="EthanS38/test_case_dataset",
    help="Hugging Face dataset repo containing candidate_embeddings.npy and metadata JSONL.",
)
parser.add_argument(
    "--model-id",
    type=str,
    default="EthanS38/test_case_retreival",
    help="Hugging Face model repo for the fine-tuned retriever.",
)
parser.add_argument(
    "--model-subdir",
    type=str,
    default="retrieval_model",
    help="Optional subdirectory in the model repo containing SentenceTransformer files.",
)
parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
parser.add_argument("--verbose", action="store_true", help="Show focal method context too.")
parser.add_argument("--json-output", action="store_true", help="Print results as JSON instead.")

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

# load candidate pool
print("Loading candidate embeddings ...")
candidate_matrix = np.load(str(emb_path)).astype("float32")
metadata = load_metadata(meta_path)
print(f"  {candidate_matrix.shape[0]} candidates, dim {candidate_matrix.shape[1]}")

# load fine-tuned model
snapshot_dir = Path(snapshot_download(repo_id=args.model_id, repo_type="model"))
candidate_model_dir = snapshot_dir / args.model_subdir
model_dir = candidate_model_dir if (candidate_model_dir / "modules.json").exists() else snapshot_dir
print(f"Loading fine-tuned model from {model_dir} ...")
model = SentenceTransformer(str(model_dir))

# encode the query
query_text = read_query_text(args.input)
print(f"Encoding query ({len(query_text)} chars) ...")
query_vec = model.encode([query_text], normalize_embeddings=True, convert_to_numpy=True).astype("float32")

# search
results = search(candidate_matrix, metadata, query_vec, args.top_k)

# output
if args.json_output:
    print(json.dumps(results, indent=2, ensure_ascii=False))
else:
    print(f"\nTop {args.top_k} test cases for your query:")
    print_results(results, args.verbose)
