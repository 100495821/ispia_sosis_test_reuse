"""
pipeline.py
-----------
Orchestrates the full backend pipeline in one function call.

This is the single entry point that main.py (and later the API) should call.

Flow:
    1. Take a Feature and a list of TestCases as input
    2. Use embedder.py to rank test cases by similarity to the feature
    3. Take the top-k most similar tests
    4. Use generator.py to generate a suggested new test case
    5. Return a PipelineOutput with both results

Optional corpus_embeddings and feature_embedding can be passed in when the
caller has pre-loaded embeddings from the groupmate's data files (via loader.py).
Passing them avoids re-encoding everything and makes the pipeline much faster.
"""

import numpy as np

from embedder import rank_tests_by_similarity
from generator import generate_test
from models import Feature
from models import PipelineOutput


# How many top similar tests to pass to the generator
DEFAULT_TOP_K = 3


def run(
    feature: Feature,
    test_cases: list,
    top_k: int = DEFAULT_TOP_K,
    corpus_embeddings: np.ndarray = None,
    feature_embedding: np.ndarray = None,
    skip_generation: bool = False
) -> PipelineOutput:
    """
    Runs the full SEAI backend pipeline.

    Args:
        feature            - The new Feature to analyze
        test_cases         - Existing TestCase objects to compare against
        top_k              - How many top similar tests to feed into the generator
        corpus_embeddings  - Optional pre-computed embeddings from loader.load_candidates()
        feature_embedding  - Optional pre-computed feature vector from loader.load_query_feature()
        skip_generation    - If True, skip the generator and return only ranked tests

    Returns:
        PipelineOutput with:
            - ranked_tests   : all test cases sorted by similarity score
            - generated_test : a suggested new test case from flan-t5 (empty if skipped)
    """

    # --- Step 1: Rank all test cases by similarity to the feature ---
    print("\n[Pipeline] Step 1: Computing similarity scores...")
    ranked_tests = rank_tests_by_similarity(
        feature=feature,
        test_cases=test_cases,
        corpus_embeddings=corpus_embeddings,
        feature_embedding=feature_embedding
    )

    # --- Step 2: Select the top-k most similar test cases ---
    print(f"\n[Pipeline] Step 2: Selecting top {top_k} similar tests...")
    top_tests = []
    for i in range(top_k):
        # Guard against having fewer test cases than top_k
        if i < len(ranked_tests):
            top_tests.append(ranked_tests[i].test_case)

    # --- Step 3: Generate a new test case (optional) ---
    generated_test = ""
    if skip_generation:
        print("\n[Pipeline] Step 3: Skipping generation (--no-generate flag set)")
    else:
        print("\n[Pipeline] Step 3: Generating new test case...")
        generated_test = generate_test(feature, top_tests)

    # --- Step 4: Package and return the results ---
    output = PipelineOutput(
        ranked_tests=ranked_tests,
        generated_test=generated_test
    )

    return output
