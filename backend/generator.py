"""
generator.py
------------
Generates a new JUnit test case using Qwen/Qwen2.5-Coder-7B-Instruct.

Responsibility:
    Given a Java focal method and the top similar test cases retrieved by the
    embedder, generate a suggested new JUnit test method using a chat prompt.

Model used:
    Qwen/Qwen2.5-Coder-3B-Instruct
    - Decoder-only causal LM instruction-tuned for code tasks
    - Strong Java unit test generation
    - Downloads automatically on first run (~6GB in float16)
    - Requires accelerate: pip install accelerate
"""

import re
from typing import Tuple

from transformers import AutoTokenizer
from transformers import AutoModelForCausalLM
import torch

from models import Feature
from models import TestCase


# ---------------------------------------------------------------------------
# Model name — change this to swap in a different generator
# ---------------------------------------------------------------------------
GENERATOR_MODEL_NAME = "Qwen/Qwen2.5-Coder-3B-Instruct"

# Maximum number of new tokens the model can generate
MAX_NEW_TOKENS = 512

_tokenizer = None
_generator_model = None

# ---------------------------------------------------------------------------
# Chat messages — system sets the role, user template carries the task
# {focal_method} and {similar_tests} are filled at call time in the user message
# ---------------------------------------------------------------------------
SYSTEM_MESSAGE = (
    "You are an expert Java software test engineer. "
    "Generate clean, correct JUnit unit tests. "
    "Output only the test method — no class wrapper, no import statements."
)

USER_TEMPLATE = """Given the focal method below, generate a new JUnit unit test for it.

Focal Method (Java):
{focal_method}

Top similar existing test cases for reference:
{similar_tests}

Rules for the generated test:
- Use @Test annotation (JUnit 4 or JUnit 5)
- Method name must follow the pattern: test<MethodName>_<scenario> or should_<expectedBehavior>_when_<condition>
- Follow the Arrange-Act-Assert (AAA) structure with one logical assertion per test
- The test must be self-contained — no shared mutable state with other tests
- Use standard assertions: assertEquals, assertTrue, assertFalse, assertThrows, assertNotNull
- Do not use comments — the test name and assertions should be self-explanatory

Generate only the test method body (no class wrapper, no imports):"""


def extract_test_method_name(java_code: str) -> str:
    """
    Extracts the first JUnit test method name from Java test source code.
    Looks for @Test followed by a void method declaration.
    Falls back to 'test_unknown' if no match is found.
    """
    match = re.search(r"@Test(?:\([^)]*\))?\s+(?:public\s+)?void\s+(\w+)", java_code)
    if match:
        return match.group(1)
    return "test_unknown"


def format_similar_tests(top_tests: list) -> str:
    """
    Formats a list of TestCase objects into a numbered string
    so the model can read them clearly in the prompt.
    Uses the extracted JUnit method name instead of the source file path.
    """
    formatted_lines = []

    for index, test_case in enumerate(top_tests):
        entry_number = index + 1
        test_name = extract_test_method_name(test_case.code) if test_case.code else "test_unknown"
        entry = str(entry_number) + ". " + test_name + "\n"
        if test_case.code:
            entry = entry + "   " + test_case.code + "\n"
        formatted_lines.append(entry)

    return "\n".join(formatted_lines)


def _get_generator() -> Tuple[AutoTokenizer, AutoModelForCausalLM]:
    """
    Lazily loads and caches tokenizer/model so generation requests do not
    re-download/reinitialize the model each time.
    """
    global _tokenizer
    global _generator_model

    if _tokenizer is None or _generator_model is None:
        print(f"Loading {GENERATOR_MODEL_NAME}...")
        _tokenizer = AutoTokenizer.from_pretrained(GENERATOR_MODEL_NAME)
        _generator_model = AutoModelForCausalLM.from_pretrained(
            GENERATOR_MODEL_NAME,
            torch_dtype="auto",
            device_map="auto",
        )

    return _tokenizer, _generator_model


def generate_test(
    feature: Feature,
    top_tests: list,
    max_new_tokens: int = MAX_NEW_TOKENS
) -> str:
    """
    Generates a suggested new JUnit test method for the given focal method,
    informed by the most similar existing test cases.

    Args:
        feature        - Feature whose .code field holds the Java focal method;
                         falls back to .description if .code is empty
        top_tests      - A list of TestCase objects (top-k from the embedder)
        max_new_tokens - How many tokens the model can generate (default 512)

    Returns:
        A string containing the suggested test method body
    """

    # --- Step 1: Load tokenizer and model ---
    tokenizer, model = _get_generator()

    # --- Step 2: Build the chat messages ---
    similar_tests_text = format_similar_tests(top_tests)
    user_message = USER_TEMPLATE.format(
        focal_method=feature.code or feature.description,
        similar_tests=similar_tests_text
    )
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user",   "content": user_message},
    ]

    # --- Step 3: Apply the model's chat template ---
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    # --- Step 4: Generate ---
    print(f"Generating test case with {GENERATOR_MODEL_NAME}...")
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )

    # --- Step 5: Decode only the newly generated tokens (skip the prompt) ---
    new_tokens = output_ids[0][inputs.input_ids.shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)
