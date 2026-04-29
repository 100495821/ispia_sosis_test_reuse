# SEAI Backend

This is the backend for SEAI — an AI-powered pipeline that, given a new software feature, finds the most relevant existing test cases and generates a suggested new one.

The backend exposes a **FastAPI** HTTP server (`api.py`) and an interactive **CLI** (`main.py`). Both use the same underlying pipeline.

---

## What the backend does

```
[Java focal method]
        ↓
[Embedder]        encode the feature as a 384-dim vector
        ↓           compute cosine similarity against all candidate test vectors
[Top-K results]   ranked list of most similar existing tests
        ↓
[Generator]       feed feature + top-k tests into Qwen2.5-Coder-3B-Instruct
        ↓
[Output]          ranked_tests  +  generated_test string
```

The candidate test embeddings are downloaded automatically from Hugging Face
(`EthanS38/test_case_dataset`) on first run. The backend does not re-encode the
full corpus on every request.

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
Computes semantic similarity between a focal method and a list of test cases.

- **Fine-tuned mode** (default): loads `EthanS38/test_case_retreival` from Hugging Face — a MiniLM model fine-tuned with MultipleNegativesRankingLoss on Methods2Test pairs
- **Vanilla mode** (`use_vanilla=True`): uses the base `sentence-transformers/all-MiniLM-L6-v2` model
- Call `configure_model(use_vanilla)` once at startup to select the mode; the model is loaded lazily and cached
- **Corpus mode** (fast): pass pre-computed `corpus_embeddings` — only the query needs to be encoded
- **Inline mode** (flexible): encodes everything on the fly; no pre-computed embeddings needed
- Returns a list of `SimilarityResult` sorted from highest to lowest score

Key function: `rank_tests_by_similarity(feature, test_cases, corpus_embeddings=None, feature_embedding=None)`

---

### `generator.py`
Generates a new JUnit test method using a causal language model.

- Model: `Qwen/Qwen2.5-Coder-3B-Instruct` (~6 GB in float16, downloads automatically on first run)
- Takes the focal method and the top-K similar test cases as input
- Builds a structured chat prompt (system message + user template) via `transformers` chat-template API
- Returns the generated test method as a plain string

Key functions:
- `generate_test(feature, top_tests, max_new_tokens=512)` — returns the generated test string
- `extract_test_method_name(java_code)` — extracts the first `@Test void` method name from Java source

---

### `loader.py`
Loads the candidate pool from disk or Hugging Face Hub.

- `load_candidates_from_hf_index(dataset_repo, emb_filename, meta_filenames)` — **primary** loader; downloads `candidate_embeddings.npy` and `candidate_metadata-002.jsonl` from `EthanS38/test_case_dataset` and returns `(np.ndarray, list[TestCase])`
- `load_candidates_from_hf_jsonl(dataset_repo, jsonl_filename, max_items)` — vanilla-mode loader; downloads the per-row embedded JSONL and parses candidate embeddings inline
- `load_candidates_from_index(emb_path, meta_path)` — local-file fallback used internally by the HF loaders

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

### `api.py`
FastAPI HTTP server. This is the main entry point when running the web interface.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Returns `{ok, useVanilla, candidateCount}` |
| `POST` | `/generate` | Accepts `{focalMethod, topK?, skipGeneration?}`, returns ranked reusable tests + amplified test |

**Startup:** on server start, the API downloads the embedding model and candidate index from Hugging Face and holds them in memory for the lifetime of the process.

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `SEAI_HF_DATASET_REPO` | `EthanS38/test_case_dataset` | HF dataset repo for candidate index |
| `SEAI_HF_MODEL_REPO` | `EthanS38/test_case_retreival` | HF model repo for fine-tuned encoder |
| `SEAI_USE_VANILLA` | `0` | Set to `1` to use the base MiniLM model |
| `SEAI_HF_EMB_FILENAME` | `candidate_embeddings.npy` | Embeddings file in dataset repo |
| `SEAI_HF_META_FILENAME` | `candidate_metadata-002.jsonl` | Primary metadata file in dataset repo |

**Starting the server:**
```bash
cd backend
../.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Or use the convenience script from the project root:
```bash
bash run_website.sh
```

---

### `main.py`
Interactive CLI that mirrors the SOSIS web UI in the terminal. Accepts a pasted Java focal method instead of reading from a JSONL file.

**Input:** Java focal method (pasted interactively)

**Output:**
1. Top 5 Reusable Test Cases — ranked list with test name, description, similarity score as %
2. AI-Generated Test Case Suggestion — Qwen2.5-Coder-3B-Instruct output

```bash
python main.py                   # fine-tuned model, full candidate index
python main.py --no-generate     # retrieval only (skips generation, much faster)
python main.py --vanilla          # base all-MiniLM-L6-v2 model + eval JSONL candidates
python main.py --vanilla --no-generate
```

---

## How to run

### Setup
```bash
# From the project root
bash setup.sh
source .venv/bin/activate
```

### Run the API server
```bash
cd backend
../.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

### Run interactively (CLI)
```bash
python main.py
python main.py --no-generate
```

---

## Dependencies

| Package | Used in |
|---|---|
| `sentence-transformers` | `embedder.py` |
| `transformers` | `generator.py` |
| `torch` | both models |
| `numpy` | `embedder.py`, `loader.py` |
| `fastapi` | `api.py` |
| `uvicorn` | `api.py` (ASGI server) |
| `huggingface_hub` | `embedder.py`, `loader.py` |
| `accelerate` | `generator.py` (required for large model loading) |

All dependencies are declared in the project root `requirements.txt`.

---

## What is NOT in the backend

- The data pipeline (JSONL generation, embedding of the full corpus) — see `Data_Loading_and_Processing/`
- The retrieval model training — see `Retrieval_Pipeline/train_retrieval_model.py`
- Automated tests — see the project status doc for what's planned
