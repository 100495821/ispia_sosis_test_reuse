"""
main.py
-------
Interactive CLI entry point for the SEAI backend pipeline.

Mirrors the SOSIS web UI input/output in the terminal:
  - Input:  Java focal method (pasted code)
  - Output 1: Top 5 Reusable Test Cases with similarity scores (%)
  - Output 2: AI-Generated Test Case Suggestion

Usage:
    python main.py                           # fine-tuned model, full candidate index
    python main.py --no-generate             # retrieval only (skips flan-t5, much faster)
    python main.py --vanilla                 # base model + per-row embedded JSONL
    python main.py --vanilla --no-generate   # vanilla retrieval only

Candidate pool sources:
    Fine-tuned (default): Hugging Face dataset candidate index files
    Vanilla (--vanilla):  Hugging Face dataset embedded eval JSONL
"""

import argparse
import os

from embedder import configure_model
from loader import load_candidates_from_hf_index
from loader import load_candidates_from_hf_jsonl
from models import Feature
from pipeline import run


HF_DATASET_REPO = os.getenv("SEAI_HF_DATASET_REPO", "EthanS38/test_case_dataset")
HF_MODEL_REPO = os.getenv("SEAI_HF_MODEL_REPO", "EthanS38/test_case_retreival")
HF_EMB_FILENAME = os.getenv("SEAI_HF_EMB_FILENAME", "candidate_embeddings.npy")
HF_META_PRIMARY = os.getenv("SEAI_HF_META_FILENAME", "candidate_metadata-002.jsonl")
HF_META_FALLBACK = os.getenv("SEAI_HF_META_FALLBACK", "candidate_metadata.jsonl")
HF_VANILLA_JSONL = os.getenv("SEAI_HF_VANILLA_JSONL", "methods2test_eval_embedded.jsonl")

VANILLA_MAX_ITEMS = None  # no cap — load all candidates
TOP_K             = 5     # number of top similar test cases to display
DESC_MAX_CHARS    = 80    # max characters to show for test case descriptions


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args():
    """
    Parses command-line arguments.

    Supported flags:
        --no-generate   Skip the AI generation step (retrieval only, much faster)
        --vanilla       Use base all-MiniLM-L6-v2 model and per-row embedded JSONL
                        instead of the fine-tuned pipeline outputs
    """
    parser = argparse.ArgumentParser(
        description="SEAI CLI — AI-powered test reuse pipeline"
    )
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="Skip AI test case generation (retrieval only, much faster)"
    )
    parser.add_argument(
        "--vanilla",
        action="store_true",
        help="Use base all-MiniLM-L6-v2 model and per-row embedded JSONL instead of fine-tuned pipeline outputs"
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# User input prompts
# ---------------------------------------------------------------------------
def prompt_feature_description():
    """
    Prompts the user to describe the new feature or variant.
    Re-prompts if the input is blank.

    Returns:
        str — non-empty feature description entered by the user
    """
    print("\nPaste the Java focal method to generate a test for:")
    while True:
        description = input("> ").strip()
        if description:
            return description
        print("  (Input cannot be empty. Please enter a description.)")


# ---------------------------------------------------------------------------
# Pipeline wrappers
# ---------------------------------------------------------------------------
def load_candidate_pool(use_vanilla: bool):
    """
    Loads the candidate test pool for the selected mode.

    Fine-tuned mode (default): loads index files from Hugging Face dataset.
    Vanilla mode (--vanilla):  loads the embedded JSONL from Hugging Face dataset.

    Returns:
        tuple: (corpus_embeddings: np.ndarray, test_cases: list[TestCase])
    """
    print("\nLoading candidate test pool...")
    if use_vanilla:
        corpus_embeddings, test_cases = load_candidates_from_hf_jsonl(
            dataset_repo=HF_DATASET_REPO,
            jsonl_filename=HF_VANILLA_JSONL,
            max_items=VANILLA_MAX_ITEMS
        )
    else:
        corpus_embeddings, test_cases = load_candidates_from_hf_index(
            dataset_repo=HF_DATASET_REPO,
            emb_filename=HF_EMB_FILENAME,
            meta_filenames=(HF_META_PRIMARY, HF_META_FALLBACK),
        )
    return corpus_embeddings, test_cases


def build_feature(description):
    """
    Constructs a Feature object from the user's free-text description.

    The name is fixed to "user_feature" so the embedding centres on the
    description text rather than a variable name string.

    Args:
        description: str — the feature description entered by the user

    Returns:
        Feature
    """
    return Feature(name="user_feature", description="", code=description)


def run_pipeline(feature, test_cases, corpus_embeddings, skip_generation):
    """
    Runs the full SEAI pipeline with the given feature and candidate pool.

    Passes feature_embedding=None so the embedder computes the feature
    vector on-the-fly from the free-text description (all-MiniLM-L6-v2).

    Args:
        feature:           Feature — the user's feature
        test_cases:        list[TestCase] — the candidate pool
        corpus_embeddings: np.ndarray — pre-computed candidate embeddings
        skip_generation:   bool — if True, skips flan-t5 generation

    Returns:
        PipelineOutput
    """
    output = run(
        feature=feature,
        test_cases=test_cases,
        top_k=TOP_K,
        corpus_embeddings=corpus_embeddings,
        feature_embedding=None,
        skip_generation=skip_generation
    )
    return output


# ---------------------------------------------------------------------------
# Output formatting helpers
# ---------------------------------------------------------------------------
def format_score_percent(score):
    """
    Converts a cosine similarity float (0.0–1.0) to a percentage string.

    Example: 0.8432 -> "84%"

    Args:
        score: float

    Returns:
        str
    """
    percent = round(score * 100)
    return str(percent) + "%"


def format_test_name(source_file_path):
    """
    Extracts just the filename from a full source file path.

    Example: "/Users/henry/.../17898911_348_corpus.json" -> "17898911_348_corpus.json"

    Args:
        source_file_path: str

    Returns:
        str
    """
    return os.path.basename(source_file_path)


def format_description(description, max_chars=DESC_MAX_CHARS):
    """
    Truncates a long description to max_chars characters, adding "..." if cut.

    Args:
        description: str
        max_chars:   int

    Returns:
        str
    """
    if len(description) <= max_chars:
        return description
    return description[:max_chars].rstrip() + "..."


# ---------------------------------------------------------------------------
# Output printing
# ---------------------------------------------------------------------------
def print_ranked_tests(ranked_tests):
    """
    Prints the "Top 5 Reusable Test Cases" section.

    Format:
        [1]  64%  —  7437073_381_corpus.json
        <full test case code>

    Args:
        ranked_tests: list[SimilarityResult] — from PipelineOutput.ranked_tests
    """
    print("\n" + "=" * 62)
    print("Top 5 Reusable Test Cases")
    print("=" * 62)

    for rank_index in range(TOP_K):
        if rank_index >= len(ranked_tests):
            break

        result = ranked_tests[rank_index]
        rank_number = rank_index + 1
        test_name = format_test_name(result.test_case.name)
        score_str = format_score_percent(result.score)

        print(f"\n[{rank_number}]  {score_str}  —  {test_name}")
        print("-" * 62)
        print(result.test_case.code)
        print()


def print_generated_test(generated_test):
    """
    Prints the "AI-Generated Test Case Suggestion" section.

    The raw flan-t5 output is printed verbatim — no post-processing.

    Args:
        generated_test: str — from PipelineOutput.generated_test
    """
    if not generated_test or not generated_test.strip():
        return

    print("\n" + "=" * 62)
    print("AI-Generated Test Case Suggestion")
    print("=" * 62)
    print()
    print(generated_test)
    print()


def print_output(feature, output, skip_generation):
    """
    Prints all results after the pipeline completes.

    Sections printed:
        1. Focal method confirmation
        2. Top 5 Reusable Test Cases
        3. AI-Generated Test Case Suggestion (unless skipped)

    Args:
        feature:         Feature
        output:          PipelineOutput
        skip_generation: bool
    """
    print("\n" + "=" * 62)
    print(f'Focal method: "{format_description(feature.code)}"')

    print_ranked_tests(output.ranked_tests)

    if not skip_generation:
        print_generated_test(output.generated_test)

    print("\n" + "=" * 62 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """
    Top-level orchestrator for the SEAI CLI.

    Steps:
        1. Parse flags (--no-generate, --vanilla)
        2. Configure the embedding model
        3. Print banner
        4. Prompt for Java focal method
        5. Load candidate pool
        6. Build Feature object from user input
        7. Run the pipeline
        8. Print formatted results
    """
    args = parse_args()
    skip_generation = args.no_generate

    # --- Configure the embedding model before anything else ---
    configure_model(use_vanilla=args.vanilla, model_repo=HF_MODEL_REPO)

    print("\nSOSIS — AI-Powered Test Reuse Pipeline")
    print("=" * 62)
    print(f"Mode:       {'vanilla (base model)' if args.vanilla else 'fine-tuned'}")
    print(f"Generation: {'DISABLED (--no-generate)' if skip_generation else 'ENABLED'}")

    # --- Collect user input ---
    description = prompt_feature_description()

    # --- Load the candidate pool ---
    corpus_embeddings, candidate_test_cases = load_candidate_pool(use_vanilla=args.vanilla)

    # --- Build the Feature from the Java focal method ---
    feature = build_feature(description)

    # --- Run the pipeline (on-the-fly feature embedding) ---
    output = run_pipeline(
        feature=feature,
        test_cases=candidate_test_cases,
        corpus_embeddings=corpus_embeddings,
        skip_generation=skip_generation
    )

    # --- Print results ---
    print_output(feature, output, skip_generation)


if __name__ == "__main__":
    main()
