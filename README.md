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
│  Feature / Variant    │
│  Description (input)  │
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
     │  (fine-tune MiniLM    │  → models/retrieval_model/
     │   with MNR loss)      │  → processed/candidate_embeddings.npy
     └────┬─────────────────┘
          │
     ┌────▼─────────────────┐
     │  Top-K Retrieval      │  query_top_k.py
     │  (encode query,       │  → Top 5 test cases + scores
     │   cosine similarity)  │
     └────┬─────────────────┘
          │
          ▼
     ┌──────────────────────┐
     │  FLAN-T5 Generator    │  (future)
     │  (amplified test case)│
     └──────────────────────┘
```

**Stage 1 — Data Loading:** The Methods2Test corpus is loaded and each focal method + test case pair is embedded with all-MiniLM-L6-v2.

**Stage 2 — Contrastive Training:** The pre-trained MiniLM encoder is fine-tuned with MultipleNegativesRankingLoss so that focal methods and their ground-truth test cases are pulled closer in embedding space. All candidates are then encoded with the fine-tuned model.

**Stage 3 — Retrieval:** A new code input is encoded with the fine-tuned model and compared against the pre-computed candidate embeddings via cosine similarity to find the top-K most relevant test cases.

**Stage 4 — Generation (future):** The input and retrieved tests will be fed to FLAN-T5 to generate an amplified test case targeting uncovered behavior.

## Models Used

| Model | Role | Why |
|-------|------|-----|
| [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Semantic embedding & retrieval | Fast, lightweight (384-dim), strong performance on similarity tasks. Encodes both focal methods and test cases into a shared vector space for cosine similarity search. |
| [`google/flan-t5-base`](https://huggingface.co/google/flan-t5-base) | Test case generation | Instruction-tuned seq2seq model capable of generating code given context. Used to produce amplified test cases from the input description and retrieved examples. |

> **Note:** FLAN-T5 generation has not yet been integrated into the pipeline. This is planned for a future milestone.

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

## Project Structure

```
ispia_sosis_test_reuse/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── setup.sh                           # One-command environment setup
├── .gitignore                         # Excludes processed/, .venv/, models/
├── Data_Loading_and_Processing/
│   ├── README.md                      # Detailed docs for data scripts
│   └── prepare_methods2test_embeddings.py
│                                      # Loads corpus, embeds with MiniLM,
│                                      # writes per-split JSONL output
├── Retrieval_Pipeline/
│   ├── train_retrieval_model.py       # Fine-tune sentence-transformer,
│   │                                  # encode candidates
│   ├── query_top_k.py                 # Retrieve top-K tests for a query
│   └── evaluate_retrieval.py          # Evaluate Hit@K and MRR@K on eval split
├── models/                            # (git-ignored) Fine-tuned model weights
│   └── retrieval_model/
└── processed/                         # (git-ignored) Embeddings & index
    ├── methods2test_train_embedded.jsonl
    ├── methods2test_eval_embedded.jsonl
    ├── methods2test_test_embedded.jsonl
    ├── candidate_embeddings.npy        # Pre-encoded candidate vectors
    └── candidate_metadata.jsonl        # Metadata for each candidate
```

## Setup

### 1. Clone this repository

```bash
git clone https://github.com/<your-org>/ispia_sosis_test_reuse.git
cd ispia_sosis_test_reuse
```

### 2. Clone the Methods2Test dataset

```bash
git clone https://github.com/microsoft/methods2test.git /path/to/methods2test
```

> This is a large repository. Only the `corpus/json/` directory is needed.

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

### Generation (future)

> **TODO:** FLAN-T5 test amplification has not yet been integrated. This is planned for a future milestone.

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
- [ ] **Full training run** — train on all 624K pairs (currently validated with 500-pair test run)
- [ ] **FLAN-T5 generation module** — prompt engineering and integration for test amplification
- [ ] **End-to-end pipeline script** — single entry point accepting a feature description and producing all outputs
- [ ] **Compact storage format** — migrate from JSONL to Parquet or NumPy for smaller embedding files
- [ ] **Incremental processing** — support resuming interrupted embedding runs