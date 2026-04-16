"""
models.py
---------
Shared data structures used across the backend.

These are plain Python dataclasses — no external libraries needed.
Other team members can add fields here as the project evolves.
"""

from dataclasses import dataclass
from dataclasses import field


@dataclass
class Feature:
    """
    Represents a software feature or variant being introduced.

    Fields:
        name        - Short identifier, e.g. "login_with_oauth"
        description - Plain text description of what the feature does
        code        - Optional: the actual function or code snippet
    """
    name: str
    description: str
    code: str = ""


@dataclass
class TestCase:
    """
    Represents a single test case (existing or to be evaluated).

    Fields:
        name        - Short identifier, e.g. "test_login_success"
        description - Plain text description of what the test checks
        code        - Optional: the actual test code
    """
    name: str
    description: str
    code: str = ""


@dataclass
class SimilarityResult:
    """
    Pairs a test case with its similarity score relative to a feature.

    Fields:
        test_case - The TestCase that was compared
        score     - Cosine similarity value between 0.0 (no match) and 1.0 (identical)
    """
    test_case: TestCase
    score: float


@dataclass
class PipelineOutput:
    """
    The final output of the full backend pipeline.

    Fields:
        ranked_tests   - All test cases sorted from most to least similar to the feature
        generated_test - A new test case suggested by the generator model
    """
    ranked_tests: list = field(default_factory=list)   # list of SimilarityResult
    generated_test: str = ""
