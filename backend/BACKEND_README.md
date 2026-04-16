# SEAI Backend

This is the backend for SEAI — an AI-powered pipeline that, given a new software feature, finds the most relevant existing test cases and generates a suggested new one.

The backend is pure Python. No web framework, no API server. It runs from the terminal.

---

## What the backend does

```
[Feature description]
        ↓
[Embedder]        encode the feature as a 384-dim vector
        ↓           compute cosine similarity against all candidate test vectors
[Top-K results]   ranked list of most similar existing tests
        ↓
[Generator]       feed feature + top-k tests into flan-t5-base
        ↓
[Output]          ranked_tests  +  generated_test string
```

The candidate test embeddings come from the data pipeline (your groupmate's JSONL files). The backend loads them from disk — it does not re-encode the full corpus on every run.

---

## Files

### `models.py`
Defines the four shared data structures used everywhere in the backend.

- `Feature(name, description, code)` — the new feature you want tests for
- `TestCase(name, description, code)` — one existing test case
- `SimilarityResult(test_case, score)` — a test case paired with its similarity score (0.0–1.0)
- `PipelineOutput(ranked_tests, generated_test)` — what the pipeline returns

No external dependencies. These are plain Python dataclasses.

---

### `embedder.py`
Computes semantic similarity between a feature and a list of test cases.

- Model: `sentence-transformers/all-MiniLM-L6-v2` (same model used by the data pipeline — vectors are directly compatible)
- The model is loaded once on first call and cached in memory for all subsequent calls
- Two modes:
  - **Corpus mode** (fast): pass pre-computed `corpus_embeddings` from `loader.py` — only the feature needs to be encoded
  - **Inline mode** (flexible): no pre-computed embeddings — encodes everything on the fly; used by `main.py` for free-text input
- Returns a list of `SimilarityResult` sorted from highest to lowest score

Key function: `rank_tests_by_similarity(feature, test_cases, corpus_embeddings=None, feature_embedding=None)`

---

### `generator.py`
Generates a new test case string using a language model.

- Model: `google/flan-t5-base` (~250 MB, downloads automatically on first run)
- Takes the feature and the top-k similar test cases as input
- Builds a structured prompt via LangChain `PromptTemplate`, then runs the model
- Returns the generated text as a plain string

Key function: `generate_test(feature, top_tests, max_new_tokens=200)`

---

### `loader.py`
Reads the data pipeline's output (embedded JSONL files) and converts rows into backend objects.

- `load_candidates(jsonl_path, max_items)` — loads N test cases and their pre-computed embeddings into a `(np.ndarray, list[TestCase])` tuple. The array has shape `(N, 384)`.
- `load_query_feature(jsonl_path, index)` — reads one specific row and returns it as a `(np.ndarray, Feature)` tuple.

The JSONL format expected per line:
```json
{
  "source_file": "path/to/TestClass.java",
  "query_text": "focal method source code",
  "candidate_text": "test case source code",
  "query_embedding": [0.12, -0.34, ...],
  "candidate_embedding": [0.56, 0.78, ...]
}
```

---

### `pipeline.py`
The single orchestration function. Connects embedder → top-k selection → generator.

Key function:
```python
run(feature, test_cases, top_k=3, corpus_embeddings=None, feature_embedding=None, skip_generation=False)
```

Returns a `PipelineOutput`. Pass `skip_generation=True` to skip the generator and only get the ranked test list (much faster).

---

### `main.py`
Interactive CLI that mirrors the SOSIS web UI in the terminal. Accepts free-text input instead of reading from a JSONL file.

**Input (prompted interactively):**
1. A free-text description of the new feature or variant
2. Existing test cases pasted one per line (e.g. `TEST-001: Check payload`)

**Output:**
1. Top 5 Reusable Test Cases — ranked list with test name, short description, similarity score as %
2. AI-Generated Test Case Suggestion — raw output from flan-t5

```bash
python main.py                  # full run: retrieval + generation
python main.py --no-generate    # retrieval only (skips flan-t5)
```

The feature description is encoded on the fly using the same `all-MiniLM-L6-v2` model, so its vector is directly comparable to the pre-computed candidate embeddings in the JSONL.

---

## How to run

### Setup
```bash
cd backend
pip install -r requirements.txt
```

### Run interactively (main.py)
```bash
python main.py
python main.py --no-generate
```

---

## Dependencies

| Package | Version | Used in |
|---|---|---|
| `sentence-transformers` | >=2.7 | `embedder.py` |
| `transformers` | >=4.40 | `generator.py` |
| `torch` | >=2.0 | both models |
| `numpy` | >=1.26 | `embedder.py`, `loader.py` |
| `langchain-core` | >=0.2 | `generator.py` (prompt template) |

---

## What is NOT in the backend

- The data pipeline (JSONL generation, embedding of the full corpus) — that is your groupmate's work in `data_pipeline/`
- A REST API or web server — the pipeline is CLI-only for now
- Automated tests — see the project status doc for what's planned
