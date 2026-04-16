"""
main.py
-------
Interactive CLI entry point for the SEAI backend pipeline.

Mirrors the SOSIS web UI input/output in the terminal:
  - Input 1: free-text feature/variant description
  - Input 2: existing test cases, pasted one per line
  - Output 1: Top 5 Reusable Test Cases with similarity scores (%)
  - Output 2: AI-Generated Test Case Suggestion

Usage:
    python main.py                  # retrieval + generation
    python main.py --no-generate    # retrieval only (skips flan-t5, much faster)

Candidate pool (pre-computed embeddings):
    /Users/henry/Desktop/SEAI/processed/methods2test_test_embedded.jsonl
"""

import argparse
import os

from loader import load_candidates
from models import Feature
from models import TestCase
from pipeline import run


# ---------------------------------------------------------------------------
# Constants — change these to point at a different data file or adjust limits
# ---------------------------------------------------------------------------
CANDIDATES_JSONL = "/Users/henry/Desktop/SEAI/processed/methods2test_test_embedded.jsonl"
MAX_CANDIDATES   = 300   # number of rows to load from the JSONL as the candidate pool
TOP_K            = 5    # number of top similar test cases to display
DESC_MAX_CHARS   = 80   # max characters to show for test case descriptions


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args():
    """
    Parses command-line arguments.

    Supported flags:
        --no-generate   Skip the AI generation step (retrieval only, much faster)
    """
    parser = argparse.ArgumentParser(
        description="SEAI CLI — AI-powered test reuse pipeline"
    )
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="Skip AI test case generation (retrieval only, much faster)"
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
    print("\nDescribe the new feature or variant:")
    while True:
        description = input("> ").strip()
        if description:
            return description
        print("  (Input cannot be empty. Please enter a description.)")


def prompt_test_cases():
    """
    Prompts the user to paste existing test cases, one per line.
    Input ends when the user presses Enter on a blank line.

    Returns:
        list[str] — raw lines entered by the user (not yet parsed)
    """
    print("\nPaste your existing test cases (one per line).")
    print("Press Enter on a blank line when done:")
    raw_lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        raw_lines.append(line)
    return raw_lines


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------
def parse_test_cases(raw_lines):
    """
    Parses raw user-pasted lines into TestCase objects.

    Expected format (one per line):
        TEST-001: Check payload validation
        TEST-002: Verify handshake under timeout

    Lines without a colon are treated as a name with no description.
    Empty lines are skipped.

    Args:
        raw_lines: list[str] — raw lines from prompt_test_cases()

    Returns:
        list[TestCase]
    """
    test_cases = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        if ": " in line:
            parts = line.split(": ", 1)
            name = parts[0].strip()
            description = parts[1].strip()
        else:
            name = line
            description = ""
        test_cases.append(TestCase(name=name, description=description, code=""))
    return test_cases


# ---------------------------------------------------------------------------
# Pipeline wrappers
# ---------------------------------------------------------------------------
def load_candidate_pool():
    """
    Loads the pre-computed candidate test cases and their embeddings from JSONL.

    Returns:
        tuple: (corpus_embeddings: np.ndarray, test_cases: list[TestCase])
    """
    print("\nLoading candidate test pool...")
    corpus_embeddings, test_cases = load_candidates(
        jsonl_path=CANDIDATES_JSONL,
        max_items=MAX_CANDIDATES
    )
    print(f"  Loaded {len(test_cases)} candidate test cases.")
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
    return Feature(name="user_feature", description=description, code="")


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
        [1]  <test name padded to 50 chars>   84%
             <short description, truncated>

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
        short_desc = format_description(result.test_case.description)
        score_str = format_score_percent(result.score)

        print(f"\n[{rank_number}]  {test_name:<50}  {score_str}")
        print(f"     {short_desc}")


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


def print_output(feature, user_test_cases, output, skip_generation):
    """
    Prints all results after the pipeline completes.

    Sections printed:
        1. Feature description confirmation
        2. User's test case names (if any were entered)
        3. Top 5 Reusable Test Cases
        4. AI-Generated Test Case Suggestion (unless skipped)

    Args:
        feature:          Feature
        user_test_cases:  list[TestCase] — parsed from user input (display only)
        output:           PipelineOutput
        skip_generation:  bool
    """
    print("\n" + "=" * 62)
    print(f'Feature: "{feature.description}"')

    if user_test_cases:
        names = ", ".join(tc.name for tc in user_test_cases)
        print(f"Your test cases: {names}")

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
        1. Parse --no-generate flag
        2. Print banner
        3. Prompt for feature description
        4. Prompt for existing test cases
        5. Load candidate pool from JSONL
        6. Build Feature object from user input
        7. Run the pipeline
        8. Print formatted results
    """
    args = parse_args()
    skip_generation = args.no_generate

    print("\nSOSIS — AI-Powered Test Reuse Pipeline")
    print("=" * 62)
    print(f"Generation: {'DISABLED (--no-generate)' if skip_generation else 'ENABLED'}")

    # --- Collect user input ---
    description = prompt_feature_description()
    raw_lines = prompt_test_cases()
    user_test_cases = parse_test_cases(raw_lines)

    # --- Load the candidate pool ---
    corpus_embeddings, candidate_test_cases = load_candidate_pool()

    # --- Build the Feature from free-text input ---
    feature = build_feature(description)

    # --- Run the pipeline (on-the-fly feature embedding) ---
    output = run_pipeline(
        feature=feature,
        test_cases=candidate_test_cases,
        corpus_embeddings=corpus_embeddings,
        skip_generation=skip_generation
    )

    # --- Print results ---
    print_output(feature, user_test_cases, output, skip_generation)


if __name__ == "__main__":
    main()
