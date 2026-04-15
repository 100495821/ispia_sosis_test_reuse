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
          ▼
┌──────────────────────┐     ┌──────────────────────────────┐
│  MiniLM Encoder      │────▶│  Vector Similarity Search     │
│  (query embedding)   │     │  (Top 5 retrieval + scores)   │
└──────────────────────┘     └──────────────┬───────────────┘
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │  FLAN-T5 Generator            │
                             │  (amplified test case)        │
                             └──────────────────────────────┘
```

**Stage 1 — Retrieval:** The input description is embedded with MiniLM and compared against pre-computed test case embeddings to find the most semantically similar existing tests.

**Stage 2 — Generation:** The input description and retrieved tests are fed to FLAN-T5, which generates a new amplified test case targeting uncovered behavior.

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
├── .gitignore                         # Excludes processed/ and .venv/
├── Data_Loading_and_Processing/
│   ├── README.md                      # Detailed docs for data scripts
│   └── prepare_methods2test_embeddings.py
│                                      # Loads corpus, embeds with MiniLM,
│                                      # writes per-split JSONL output
└── processed/                         # (git-ignored) Embedding output files
    ├── methods2test_train_embedded.jsonl
    ├── methods2test_eval_embedded.jsonl
    └── methods2test_test_embedded.jsonl
```

> **Note:** As the project grows, additional directories will be added for retrieval, generation, and evaluation components. This structure will be updated accordingly.

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

### Retrieval and generation

> **TODO:** The retrieval (Top 5 similarity search) and generation (FLAN-T5 amplification) stages have not yet been implemented as runnable scripts. These are the next milestones.

## Expected Outputs

When the full pipeline is complete, a single run will produce:

| Output | Description |
|--------|-------------|
| **Top 5 reusable tests** | Existing test cases most semantically similar to the input feature description |
| **Relevance scores** | Cosine similarity score for each recommended test |
| **Amplified test case** | A new generated test targeting behavior not covered by the retrieved tests |

## Future Work

- [ ] **Similarity search module** — implement Top 5 retrieval using cosine similarity (optionally backed by ChromaDB or FAISS for scalable vector search)
- [ ] **FLAN-T5 generation module** — prompt engineering and integration for test amplification
- [ ] **End-to-end pipeline script** — single entry point accepting a feature description and producing all outputs
- [ ] **Evaluation framework** — measure retrieval precision, generation quality, and coverage improvement
- [ ] **Compact storage format** — migrate from JSONL to Parquet or NumPy for smaller embedding files
- [ ] **Incremental processing** — support resuming interrupted embedding runs