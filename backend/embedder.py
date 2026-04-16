"""
embedder.py
-----------
Handles semantic similarity scoring using Sentence Transformers.

Two modes:

    Corpus mode  (fast)
        Pass corpus_embeddings — pre-loaded from loader.load_candidates().
        The test cases are already encoded; we only encode the feature query.
        This is how the full pipeline runs with the groupmate's data.

    Inline mode  (flexible)
        No corpus_embeddings provided — encode both the feature and all test
        cases on the fly. Useful for small one-off calls without a pre-built corpus.

Model:
    sentence-transformers/all-MiniLM-L6-v2
    Same model the data pipeline uses — vectors are directly compatible.

The model is loaded once on first call and reused for every subsequent call.
Re-loading it per request would add ~2 seconds of overhead each time.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from models import Feature
from models import TestCase
from models import SimilarityResult


# Change this to use a different embedding model (e.g. the fine-tuned one)
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Cached model instance — loaded once, shared across all calls
_model = None


def _get_model() -> SentenceTransformer:
    """
    Returns the shared embedding model, loading it on first call.
    Subsequent calls return the already-loaded instance immediately.
    """
    global _model
    if _model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def _build_feature_text(feature: Feature) -> str:
    """
    Combines a feature's fields into one string for embedding.
    We include name, description, and code so the model gets full context.
    """
    text = feature.name + ". " + feature.description

    # Only include code if it was provided
    if feature.code:
        text = text + ". " + feature.code

    return text


def _build_test_text(test_case: TestCase) -> str:
    """
    Combines a test case's fields into one string for embedding.
    Same structure as _build_feature_text so both live in the same vector space.
    """
    text = test_case.name + ". " + test_case.description

    # Only include code if it was provided
    if test_case.code:
        text = text + ". " + test_case.code

    return text


def rank_tests_by_similarity(
    feature: Feature,
    test_cases: list,
    corpus_embeddings: np.ndarray = None,
    feature_embedding: np.ndarray = None
) -> list:
    """
    Ranks test cases by cosine similarity to the feature and returns them sorted.

    Args:
        feature            - The Feature to compare against
        test_cases         - List of TestCase objects (must align with corpus_embeddings rows)
        corpus_embeddings  - Optional pre-computed embeddings, shape (N, 384).
                             If provided, test_cases are not re-encoded (much faster).
        feature_embedding  - Optional pre-computed feature vector, shape (384,).
                             If provided, the feature is not re-encoded either.

    Returns:
        List of SimilarityResult sorted from highest to lowest score.
    """
    model = _get_model()

    # --- Get the feature vector ---
    if feature_embedding is not None:
        # Use the pre-computed vector directly (already normalized by the data pipeline)
        feature_vector = feature_embedding
    else:
        # Encode the feature text right now
        feature_text = _build_feature_text(feature)
        feature_vector = model.encode(feature_text, normalize_embeddings=True)

    # --- Get the test case vectors ---
    if corpus_embeddings is not None:
        # Use the pre-computed corpus matrix directly
        test_vectors = corpus_embeddings
    else:
        # Encode each test case text right now
        test_texts = []
        for test_case in test_cases:
            test_text = _build_test_text(test_case)
            test_texts.append(test_text)

        test_vectors = model.encode(test_texts, normalize_embeddings=True)

    # --- Compute similarity scores ---
    # Cosine similarity = dot product when both vectors are normalized
    # test_vectors shape: (N, 384), feature_vector shape: (384,)
    similarity_scores = np.dot(test_vectors, feature_vector)

    # --- Pair each test case with its score ---
    results = []
    for i in range(len(test_cases)):
        score = float(similarity_scores[i])
        result = SimilarityResult(test_case=test_cases[i], score=score)
        results.append(result)

    # --- Sort from highest to lowest similarity ---
    results.sort(key=lambda result: result.score, reverse=True)

    return results
