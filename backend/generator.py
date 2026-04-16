"""
generator.py
------------
Generates a new/amplified test case using google/flan-t5-base.

Responsibility:
    Given a feature and the top similar test cases retrieved by the embedder,
    generate a suggested new test case using a structured prompt.

Model used:
    google/flan-t5-base
    - Instruction-following text-to-text model
    - Lightweight enough for an MVP (~250MB)
    - Downloads automatically on first run

LangChain classes used:
    - HuggingFacePipeline  : wraps the HuggingFace model as a LangChain LLM
    - PromptTemplate        : defines the structured prompt with variables
    - LCEL chain            : connects prompt → model → output
"""

from transformers import AutoTokenizer
from transformers import AutoModelForSeq2SeqLM
from langchain_core.prompts import PromptTemplate
import torch

from models import Feature
from models import TestCase


# ---------------------------------------------------------------------------
# Model name — change this to swap in a different generator
# ---------------------------------------------------------------------------
GENERATOR_MODEL_NAME = "google/flan-t5-base"

# Maximum number of new tokens the model can generate
MAX_NEW_TOKENS = 200


# ---------------------------------------------------------------------------
# Prompt template
# Curly brace variables are filled in at call time by LangChain
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """You are a software test engineer working on a software product line.

Given the new feature below and the existing similar test cases,
generate a new test case that tests the new feature.

New Feature Name: {feature_name}
Feature Description: {feature_description}
Feature Code:
{feature_code}

Similar existing test cases:
{similar_tests}

Generate a new test case for the feature described above:"""


def format_similar_tests(top_tests: list) -> str:
    """
    Formats a list of TestCase objects into a numbered string
    so the model can read them clearly in the prompt.
    """
    formatted_lines = []

    for index, test_case in enumerate(top_tests):
        # Build one entry per test case
        entry_number = index + 1
        entry = str(entry_number) + ". " + test_case.name + "\n"
        entry = entry + "   Description: " + test_case.description + "\n"

        # Only include code block if test code was provided
        if test_case.code:
            entry = entry + "   Code:\n   " + test_case.code + "\n"

        formatted_lines.append(entry)

    # Join all entries with a blank line between them
    return "\n".join(formatted_lines)


def generate_test(
    feature: Feature,
    top_tests: list,
    max_new_tokens: int = MAX_NEW_TOKENS
) -> str:
    """
    Generates a suggested new test case for the given feature,
    informed by the most similar existing test cases.

    Args:
        feature        - The new Feature to generate a test for
        top_tests      - A list of TestCase objects (top-k from the embedder)
        max_new_tokens - How many tokens the model can generate (default 200)

    Returns:
        A string containing the suggested test case
    """

    # --- Step 1: Load the tokenizer and model directly from HuggingFace ---
    print("Loading flan-t5-base model...")
    tokenizer = AutoTokenizer.from_pretrained(GENERATOR_MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(GENERATOR_MODEL_NAME)

    # --- Step 2: Build the prompt template using LangChain ---
    prompt_template = PromptTemplate(
        input_variables=[
            "feature_name",
            "feature_description",
            "feature_code",
            "similar_tests"
        ],
        template=PROMPT_TEMPLATE
    )

    # --- Step 3: Format the similar tests into a readable string ---
    similar_tests_text = format_similar_tests(top_tests)

    # --- Step 4: Use placeholder text if no code was provided for the feature ---
    feature_code_text = feature.code
    if not feature_code_text:
        feature_code_text = "(no code provided)"

    # --- Step 5: Fill in the prompt template to get the final prompt string ---
    filled_prompt = prompt_template.format(
        feature_name=feature.name,
        feature_description=feature.description,
        feature_code=feature_code_text,
        similar_tests=similar_tests_text
    )

    # --- Step 6: Tokenize the prompt into model input tensors ---
    print("Generating test case with flan-t5...")
    input_tokens = tokenizer(
        filled_prompt,
        return_tensors="pt",
        max_length=512,
        truncation=True
    )

    # --- Step 7: Run the model to generate output tokens ---
    with torch.no_grad():
        output_tokens = model.generate(
            input_tokens.input_ids,
            max_new_tokens=max_new_tokens
        )

    # --- Step 8: Decode the output tokens back into readable text ---
    generated_text = tokenizer.decode(
        output_tokens[0],
        skip_special_tokens=True
    )

    return generated_text
