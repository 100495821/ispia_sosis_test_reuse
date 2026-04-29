"""
embedder.py
-----------
Handles semantic similarity scoring using Sentence Transformers.

Call configure_model(use_vanilla) once at startup (from main.py/API) before
any similarity scoring. This selects which encoder is used:

    Fine-tuned mode (default, use_vanilla=False)
        Loads a public fine-tuned model from Hugging Face.

    Vanilla mode (use_vanilla=True)
        Uses the base sentence-transformers/all-MiniLM-L6-v2 model.

The model is loaded once on first call to _get_model() and cached for reuse.
"""

import os
from pathlib import Path

import numpy as np
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer

from models import Feature
from models import TestCase
from models import SimilarityResult


_FINETUNED_MODEL = os.getenv("SEAI_HF_MODEL_REPO", "EthanS38/test_case_retreival")
_FINETUNED_SUBDIR = os.getenv("SEAI_HF_MODEL_SUBDIR", "retrieval_model")
_FALLBACK_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"

# Set by configure_model() before first use; None means not yet configured
_model_source: str | None = None

# Cached model instance — loaded once, shared across all calls
_model = None


def configure_model(use_vanilla: bool, model_repo: str | None = None) -> None:
    """
    Selects the embedding model to use. Must be called once before any
    similarity scoring.

    Args:
        use_vanilla - If True, use the base all-MiniLM-L6-v2 model.
                  If False, use the fine-tuned model repo.
        model_repo  - Optional Hugging Face model repo id override.
    """
    global _model_source
    if use_vanilla:
        _model_source = _FALLBACK_MODEL
    else:
        repo_id = model_repo or _FINETUNED_MODEL
        snapshot_dir = Path(snapshot_download(repo_id=repo_id, repo_type="model"))

        nested_dir = snapshot_dir / _FINETUNED_SUBDIR
        if nested_dir.exists() and (nested_dir / "modules.json").exists():
            _model_source = str(nested_dir)
        else:
            _model_source = str(snapshot_dir)


def _get_model() -> SentenceTransformer:
    """
    Returns the shared embedding model, loading it on first call.
    Subsequent calls return the already-loaded instance immediately.
    """
    global _model
    if _model is None:
        if _model_source is None:
            raise RuntimeError("embedder not configured — call configure_model() before use")
        print(f"Loading embedding model: {_model_source}")
        _model = SentenceTransformer(_model_source)
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
