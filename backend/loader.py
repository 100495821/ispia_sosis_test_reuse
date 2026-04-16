"""
loader.py
---------
Two candidate-pool loaders for the two pipeline modes:

  load_candidates_from_index(emb_path, meta_path)
      Fine-tuned mode (default). Loads the separate .npy embedding matrix and
      metadata JSONL produced by train_retrieval_model.py.

  load_candidates(jsonl_path, max_items)
      Vanilla mode (--vanilla flag). Loads from the per-row embedded JSONL
      produced by prepare_methods2test_embeddings.py, where each row contains
      both text fields and a candidate_embedding vector.
"""

import json
import numpy as np

from models import Feature
from models import TestCase


def load_candidates_from_index(emb_path: str, meta_path: str):
    """
    Loads the candidate pool from the retrieval pipeline's fine-tuned outputs:
      - emb_path:  processed/candidate_embeddings.npy   (fine-tuned model vectors)
      - meta_path: processed/candidate_metadata.jsonl   (source_file, query_text, candidate_text)

    Returns:
        embeddings  - NumPy array of shape (N, 384), float32
        test_cases  - List of TestCase objects aligned with embedding rows
    """
    embeddings = np.load(emb_path).astype("float32")

    test_cases = []
    with open(meta_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            test_cases.append(TestCase(
                name=record.get("source_file", "unknown"),
                description=record.get("query_text", ""),
                code=record.get("candidate_text", "")
            ))

    print(f"Loaded {len(test_cases)} candidates. Embeddings shape: {embeddings.shape}")
    return embeddings, test_cases


def load_candidates(jsonl_path: str, max_items: int = None):
    """
    Reads an embedded JSONL file and returns the candidate pool.

    Each line becomes one TestCase, and its pre-computed candidate_embedding
    is stacked into a NumPy array so we can do fast cosine similarity later
    without re-encoding anything.

    Args:
        jsonl_path  - Path to the embedded JSONL file (e.g. methods2test_train_embedded.jsonl)
        max_items   - If set, stop after loading this many rows (useful for testing)

    Returns:
        embeddings  - NumPy array of shape (N, 384), float32
                      Row i corresponds to test_cases[i]
        test_cases  - List of TestCase objects, one per row
    """
    embeddings_list = []
    test_cases = []
    rows_loaded = 0

    print(f"Loading candidates from: {jsonl_path}")

    with open(jsonl_path, "r", encoding="utf-8") as file:
        for line in file:

            # Skip blank lines
            line = line.strip()
            if not line:
                continue

            # Parse the JSON object on this line
            record = json.loads(line)

            # Build a TestCase from this record
            # source_file  → name  (which Java file this test came from)
            # query_text   → description  (the focal method — what the test exercises)
            # candidate_text → code  (the actual test case code)
            test_case = TestCase(
                name=record.get("source_file", "unknown"),
                description=record.get("query_text", ""),
                code=record.get("candidate_text", "")
            )
            test_cases.append(test_case)

            # Store the pre-computed embedding as a float32 numpy row
            embedding_values = record.get("candidate_embedding", [])
            embedding_row = np.array(embedding_values, dtype=np.float32)
            embeddings_list.append(embedding_row)

            rows_loaded += 1

            # Stop early if a limit was requested
            if max_items is not None and rows_loaded >= max_items:
                break

    # Stack all embedding rows into one 2D array: shape (N, 384)
    embeddings_array = np.stack(embeddings_list, axis=0)

    print(f"Loaded {len(test_cases)} candidates. Embeddings shape: {embeddings_array.shape}")

    return embeddings_array, test_cases


def load_query_feature(jsonl_path: str, index: int = 0):
    """
    Reads one row from an embedded JSONL file and returns it as a Feature.

    Used to pull a real query from the test split so we can run a meaningful
    CLI trial with actual data instead of hardcoded examples.

    Args:
        jsonl_path  - Path to the embedded JSONL file (e.g. methods2test_test_embedded.jsonl)
        index       - Which row to use as the query (default: first row)

    Returns:
        query_embedding - NumPy array of shape (384,), float32
        feature         - Feature object built from the row's query_text
    """
    current_index = 0

    with open(jsonl_path, "r", encoding="utf-8") as file:
        for line in file:

            line = line.strip()
            if not line:
                continue

            if current_index == index:
                record = json.loads(line)

                # Build a Feature from this record
                feature = Feature(
                    name="query_" + str(index),
                    description=record.get("query_text", ""),
                    code=record.get("candidate_text", "")
                )

                # Extract the pre-computed query embedding
                embedding_values = record.get("query_embedding", [])
                query_embedding = np.array(embedding_values, dtype=np.float32)

                print(f"Loaded query feature from row {index} of: {jsonl_path}")

                return query_embedding, feature

            current_index += 1

    raise ValueError(f"Row {index} not found in {jsonl_path}")
