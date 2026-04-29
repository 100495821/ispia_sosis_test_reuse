# SOSIS — Test Amplification and Reuse Recommendations

> **Task 3.4** of the SOSIS (Software of Software-Intensive Systems) framework

## Overview

This project builds an MVP system for **test amplification and reuse** in software product lines. Given a new software feature or variant description, the system:

1. **Retrieves** the Top 5 most relevant existing test cases from a large corpus
2. **Scores** each recommendation with a semantic relevance score
3. **Generates** a new "amplified" test case to improve coverage beyond what existing tests provide

The goal is to reduce redundant test authoring effort across software variants by identifying reusable tests and automatically generating new ones where gaps exist.

## SOSIS Context

The SOSIS framework addresses challenges in developing and maintaining software-intensive systems, particularly those built as product lines with many variants. Task 3.4 focuses on the observation that many test cases across variants are functionally similar — this system surfaces those similarities and recommends reuse opportunities.

## System Architecture

```
┌──────────────────────┐
│  Java focal method    │
│  (user input)         │
└─────────┬────────────┘
          │
     ┌────▼─────────────────┐
     │  Data Loading         │  prepare_methods2test_embeddings.py
     │  (embed corpus with   │  → processed/*_embedded.jsonl
     │   all-MiniLM-L6-v2)   │
     └────┬─────────────────┘
          │
     ┌────▼─────────────────┐
     │  Contrastive Training │  train_retrieval_model.py
     │  (fine-tune MiniLM    │  → models/retrieval_model/ (HF: EthanS38/test_case_retreival)
     │   with MNR loss)      │  → processed/candidate_embeddings.npy (HF: EthanS38/test_case_dataset)
     └────┬─────────────────┘
          │
     ┌────▼─────────────────┐
     │  Top-K Retrieval      │  backend/embedder.py + pipeline.py
     │  (encode query,       │  → Top 5 test cases + cosine similarity scores
     │   cosine similarity)  │
     └────┬─────────────────┘
          │
          ▼
     ┌──────────────────────┐
     │  Qwen2.5-Coder-3B     │  backend/generator.py
     │  Generator            │  → AI-amplified JUnit test method
     └──────────────────────┘
          │
          ▼
     ┌──────────────────────┐
     │  FastAPI + Next.js    │  backend/api.py  +  frontend/
     │  Web Interface        │  http://localhost:3000
     └──────────────────────┘
```

**Stage 1 — Data Loading:** The Methods2Test corpus is loaded and each focal method + test case pair is embedded with all-MiniLM-L6-v2.

**Stage 2 — Contrastive Training:** The pre-trained MiniLM encoder is fine-tuned with MultipleNegativesRankingLoss so that focal methods and their ground-truth test cases are pulled closer in embedding space. All candidates are then encoded with the fine-tuned model and published to Hugging Face.

**Stage 3 — Retrieval:** A new code input is encoded with the fine-tuned model (downloaded from `EthanS38/test_case_retreival` on HF) and compared against the pre-computed candidate embeddings (downloaded from `EthanS38/test_case_dataset` on HF) via cosine similarity.

**Stage 4 — Generation:** The input and top-K retrieved tests are fed to `Qwen/Qwen2.5-Coder-3B-Instruct` to generate an amplified JUnit test targeting uncovered behavior.

## Models Used

| Model | Role | Notes |
|-------|------|-------|
| [`EthanS38/test_case_retreival`](https://huggingface.co/EthanS38/test_case_retreival) | Semantic embedding & retrieval | Fine-tuned MiniLM (384-dim) trained with MultipleNegativesRankingLoss on focal method ↔ test case pairs from Methods2Test. Downloaded automatically from Hugging Face on first run. |
| [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Baseline embedding (vanilla mode) | Base model before fine-tuning. Used when `--vanilla` flag is passed or `SEAI_USE_VANILLA=1` is set. |
| [`Qwen/Qwen2.5-Coder-3B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) | Test case generation | Decoder-only causal LM instruction-tuned for code tasks. Generates a new JUnit test method given the focal method and top-K retrieved examples. Downloads automatically (~6 GB in float16). |

## Dataset

This project uses the [Methods2Test](https://github.com/microsoft/methods2test) dataset — a large-scale corpus mapping Java focal methods to their corresponding unit tests.

**Corpus structure:**

```
methods2test/
  corpus/json/
    train/    (~624K files)
    eval/     (~78K files)
    test/     (~78K files)
```

Each JSON file contains flat string fields:

| Field | Content |
|-------|---------|
| `target` | Unit test source code |
| `src_fm` | Focal method only |
| `src_fm_fc` | Focal method + focal class |
| `src_fm_fc_co` | + constructors |
| `src_fm_fc_ms` | + method signatures |
| `src_fm_fc_ms_ff` | + fields / functions (richest context) |

## Hugging Face Artifacts

| Artifact | HF Repo | Description |
|----------|---------|-------------|
| Fine-tuned retrieval model | [`EthanS38/test_case_retreival`](https://huggingface.co/EthanS38/test_case_retreival) | Fine-tuned sentence-transformer for focal method ↔ test case similarity |
| Candidate dataset + index | [`EthanS38/test_case_dataset`](https://huggingface.co/datasets/EthanS38/test_case_dataset) | `candidate_embeddings.npy`, `candidate_metadata-002.jsonl`, and embedded JSONL splits |

The backend downloads both automatically on first run — no manual file placement needed.

## Project Structure

```
ispia_sosis_test_reuse/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── setup.sh                           # One-command environment setup
├── run_website.sh                     # Start backend + frontend together
├── .gitignore                         # Excludes processed/, .venv/, models/
├── Data_Loading_and_Processing/
│   ├── README.md                      # Detailed docs for data scripts
│   ├── prepare_methods2test_embeddings.py
│   │                                  # Loads corpus, embeds with MiniLM,
│   │                                  # writes per-split JSONL output
│   └── export_java_examples_from_processed.py
│                                      # Exports Java example files from JSONL
├── Retrieval_Pipeline/
│   ├── train_retrieval_model.py       # Fine-tune sentence-transformer,
│   │                                  # encode candidates
│   ├── query_top_k.py                 # Retrieve top-K tests for a query
│   └── evaluate_retrieval.py          # Evaluate Hit@K and MRR@K on eval split
├── backend/
│   ├── api.py                         # FastAPI server — /health + /generate
│   ├── pipeline.py                    # Orchestrates embedder → retrieval → generator
│   ├── embedder.py                    # Sentence-transformer encoding + cosine ranking
│   ├── generator.py                   # Qwen2.5-Coder-3B test generation
│   ├── loader.py                      # Loads candidate index from HF Hub or disk
│   ├── models.py                      # Shared dataclasses (Feature, TestCase, etc.)
│   ├── main.py                        # Interactive CLI entry point
│   └── BACKEND_README.md              # Detailed backend docs
├── frontend/
│   ├── app/                           # Next.js App Router pages
│   ├── components/                    # React UI components
│   ├── lib/                           # Types, store, API client, utilities
│   └── README.md                      # Frontend docs
├── models/                            # (git-ignored) Fine-tuned model weights
│   └── retrieval_model/
└── processed/                         # (git-ignored) Embeddings & index
    ├── methods2test_train_embedded.jsonl
    ├── methods2test_eval_embedded.jsonl
    ├── methods2test_test_embedded.jsonl
    ├── candidate_embeddings.npy        # Pre-encoded candidate vectors
    └── candidate_metadata-002.jsonl    # Metadata for each candidate
```

## Setup

### 1. Clone this repository

```bash
git clone https://github.com/<your-org>/ispia_sosis_test_reuse.git
cd ispia_sosis_test_reuse
```

### 2. Install Git LFS and download the Methods2Test dataset

The Methods2Test repository uses [Git LFS](https://git-lfs.com/) to store the data archives. Install it first, otherwise you will only get small pointer files instead of the actual data.

**macOS**
```bash
brew install git-lfs
git lfs install
```

**Ubuntu / Debian**
```bash
sudo apt-get install git-lfs
git lfs install
```

**Windows** — download the installer from https://git-lfs.com and run `git lfs install` afterwards.

Then clone and pull the data:

```bash
git clone https://github.com/microsoft/methods2test.git /path/to/methods2test
cd /path/to/methods2test

# Pull only the corpus/json archives (much smaller than the full repo)
git lfs pull --include="corpus/json/**"
```

> If you already cloned without Git LFS installed, run `git lfs install` and then `git lfs pull --include="corpus/json/**"` to fetch the real files.

### 2a. Decompress the archives

The corpus splits are stored as `.tar.bz2` archives. Extract them after the LFS pull:

```bash
cd /path/to/methods2test

# Extract each split
tar -xjf corpus/json/train.tar.bz2 -C corpus/json/
tar -xjf corpus/json/eval.tar.bz2  -C corpus/json/
tar -xjf corpus/json/test.tar.bz2  -C corpus/json/
```

This produces the `corpus/json/train/`, `corpus/json/eval/`, and `corpus/json/test/` folders that the scripts expect.

### 3. Install dependencies

```bash
bash setup.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Embedding the corpus

Activate the virtual environment and run the embedding pipeline:

```bash
source .venv/bin/activate

python Data_Loading_and_Processing/prepare_methods2test_embeddings.py \
    --methods2test-root /path/to/methods2test
```

This processes all three splits (train, eval, test) and writes JSONL files to `processed/`. See `Data_Loading_and_Processing/README.md` for full CLI options.

**Output format** — each JSONL row contains:

```json
{
  "source_file": "path/to/corpus_file.json",
  "query_text": "focal method + class context",
  "candidate_text": "unit test source",
  "src_fm_fc_ms_ff": "richest context variant",
  "query_embedding": [0.012, -0.034, ...],
  "candidate_embedding": [0.056, 0.011, ...]
}
```

### Training the retrieval model

Fine-tune the sentence-transformer on focal-method ↔ test-case pairs and encode all candidates:

```bash
source .venv/bin/activate

# Full training (all 624K pairs, 1 epoch)
python Retrieval_Pipeline/train_retrieval_model.py --encode-batch-size 64

# Quick test run (500 pairs)
python Retrieval_Pipeline/train_retrieval_model.py \
    --max-train-pairs 500 --eval-sample 50 --encode-batch-size 64

# Re-encode candidates with a previously saved model (no retraining)
python Retrieval_Pipeline/train_retrieval_model.py --skip-training
```

Outputs: fine-tuned model in `models/retrieval_model/`, candidate embeddings in `processed/candidate_embeddings.npy`, metadata in `processed/candidate_metadata.jsonl`.

### Querying for similar tests

Retrieve the top-K most similar test cases for a given code file or snippet:

```bash
# From a Java source file
python Retrieval_Pipeline/query_top_k.py /path/to/MyClass.java --top-k 5

# From inline code
python Retrieval_Pipeline/query_top_k.py "public void myMethod() { ... }" --top-k 10

# JSON output
python Retrieval_Pipeline/query_top_k.py /path/to/code.java --json-output > results.json
```

### Evaluating retrieval quality

Evaluate Hit@K and MRR@K on the eval split:

```bash
python Retrieval_Pipeline/evaluate_retrieval.py --k 5 --sample 2000
python Retrieval_Pipeline/evaluate_retrieval.py --save-results eval_results.json
```

### Running the web interface

Start the FastAPI backend and Next.js frontend together:

```bash
bash run_website.sh
```

This script:
1. Creates `.venv` and installs Python dependencies if not already done
2. Installs frontend npm dependencies if not already done
3. Starts the backend at `http://127.0.0.1:8000` (uvicorn)
4. Starts the frontend at `http://localhost:3000` (Next.js dev server)

Customise ports with environment variables:
```bash
BACKEND_PORT=8080 FRONTEND_PORT=4000 bash run_website.sh
```

To use the vanilla (base, non-fine-tuned) model:
```bash
SEAI_USE_VANILLA=1 bash run_website.sh
```

### Generation

Generation is handled by `Qwen/Qwen2.5-Coder-3B-Instruct`. It runs automatically as part of the `/generate` endpoint and the CLI `main.py`. To skip generation and only get retrieval results:

```bash
# CLI
python backend/main.py --no-generate

# API — set skipGeneration: true in the request body
curl -X POST http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{"focalMethod": "public int add(int a, int b) { return a + b; }", "skipGeneration": true}'
```

## Expected Outputs

When the full pipeline is complete, a single run will produce:

| Output | Description |
|--------|-------------|
| **Top 5 reusable tests** | Existing test cases most semantically similar to the input feature description |
| **Relevance scores** | Cosine similarity score for each recommended test |
| **Amplified test case** | A new generated test targeting behavior not covered by the retrieved tests |

## Future Work

- [x] **Similarity search module** — contrastive fine-tuning with MultipleNegativesRankingLoss + cosine similarity retrieval
- [x] **Evaluation framework** — Hit@K, MRR@K, NDCG@10 evaluation on eval split
- [x] **Generation module** — Qwen2.5-Coder-3B-Instruct integration for JUnit test amplification
- [x] **FastAPI backend** — `/generate` and `/health` endpoints serving the full pipeline
- [x] **Web interface** — Next.js frontend connected to the backend
- [x] **Hugging Face Hub integration** — model and dataset artifacts published; downloaded automatically on first run
- [ ] **Full training run** — train on all 624K pairs (currently validated with a subset)
- [ ] **Compact storage format** — migrate from JSONL to Parquet or NumPy for smaller embedding files
- [ ] **Incremental processing** — support resuming interrupted embedding runs