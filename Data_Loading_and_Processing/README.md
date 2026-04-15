# Data Loading and Processing

Scripts for loading the [Methods2Test](https://github.com/microsoft/methods2test) corpus, building text representations of focal methods and test cases, embedding them with a HuggingFace sentence-transformer, and writing the results to JSONL files.

## Contents

| File | Description |
|------|-------------|
| `prepare_methods2test_embeddings.py` | Main pipeline — reads every JSON corpus file across the train/eval/test splits, constructs query (focal method) and candidate (test case) texts, encodes them with `all-MiniLM-L6-v2`, and saves per-split JSONL output. |

## Prerequisites

1. Clone the [Methods2Test](https://github.com/microsoft/methods2test) repo somewhere locally (it contains the `corpus/json/{train,eval,test}/` directories).
2. From the **project root** (one level up), set up the Python environment:

```bash
bash setup.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the embedding pipeline (processes all three splits)
python Data_Loading_and_Processing/prepare_methods2test_embeddings.py \
    --methods2test-root /path/to/methods2test
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--methods2test-root` | *(required)* | Path to the local Methods2Test repo root |
| `--output-dir` | `processed` | Directory for output JSONL files (one per split) |
| `--model-name` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace embedding model |
| `--max-chars` | `2000` | Max characters per text field before embedding |
| `--batch-size` | `32` | Embedding batch size |

## Output

Three JSONL files are written to `processed/`:

- `methods2test_train_embedded.jsonl`
- `methods2test_eval_embedded.jsonl`
- `methods2test_test_embedded.jsonl`

Each row contains:

| Field | Description |
|-------|-------------|
| `source_file` | Path to the original corpus JSON file |
| `query_text` | Focal method + class context (truncated) |
| `candidate_text` | Test case source (truncated) |
| `src_fm_fc_ms_ff` | Richest context variant (method + class + sigs + fields) |
| `query_embedding` | 384-dim normalized float array |
| `candidate_embedding` | 384-dim normalized float array |

> **Note:** The output files are large (~15 GB total for the full corpus) and are excluded from Git via `.gitignore`.
