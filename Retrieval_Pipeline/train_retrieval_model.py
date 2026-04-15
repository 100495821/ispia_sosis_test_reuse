# train_retrieval_model.py
# author: Ethan Soroko
#
# Fine-tunes a HuggingFace sentence-transformer on the Methods2Test
# focal-method ↔ test-case pairs using contrastive learning
# (MultipleNegativesRankingLoss). The model learns to place matching
# query/candidate pairs close together in embedding space.
#
# After training, encodes all candidate texts with the fine-tuned model
# and saves the embeddings + metadata for use by query_top_k.py.

from __future__ import annotations

import argparse
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from datasets import Dataset
from sentence_transformers import (
    SentenceTransformer,
    SentenceTransformerTrainer,
    SentenceTransformerTrainingArguments,
)
from sentence_transformers.sentence_transformer.losses import MultipleNegativesRankingLoss
from sentence_transformers.sentence_transformer.evaluation import InformationRetrievalEvaluator


# -- helpers ------------------------------------------------------------------

def stream_jsonl(path: Path):
    """Yield parsed dicts from a JSONL file."""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_pairs(input_paths: List[Path], max_pairs: int | None = None):
    """Load (query_text, candidate_text) pairs from embedded JSONL files."""
    queries, candidates = [], []
    for path in input_paths:
        print(f"  Reading {path.name} ...")
        for row in stream_jsonl(path):
            q = row.get("query_text", "").strip()
            c = row.get("candidate_text", "").strip()
            if q and c:
                queries.append(q)
                candidates.append(c)
                if max_pairs and len(queries) >= max_pairs:
                    return queries, candidates
    return queries, candidates


def load_all_candidates(input_paths: List[Path]):
    """Load candidate texts + metadata from all splits for encoding."""
    metadata: List[Dict[str, Any]] = []
    for path in input_paths:
        for row in stream_jsonl(path):
            c = row.get("candidate_text", "").strip()
            if not c:
                continue
            metadata.append({
                "source_file": row.get("source_file", ""),
                "query_text": row.get("query_text", ""),
                "candidate_text": c,
                "src_fm_fc_ms_ff": row.get("src_fm_fc_ms_ff", ""),
            })
    return metadata


def build_eval_ir(eval_path: Path, sample_size: int = 1000, seed: int = 42):
    """Build an InformationRetrievalEvaluator from eval-split pairs."""
    import random
    rng = random.Random(seed)

    pairs = []
    for row in stream_jsonl(eval_path):
        q = row.get("query_text", "").strip()
        c = row.get("candidate_text", "").strip()
        if q and c:
            pairs.append((q, c))

    if sample_size and sample_size < len(pairs):
        pairs = rng.sample(pairs, sample_size)

    queries = {f"q{i}": q for i, (q, _) in enumerate(pairs)}
    corpus = {f"c{i}": c for i, (_, c) in enumerate(pairs)}
    relevant_docs = {f"q{i}": {f"c{i}"} for i in range(len(pairs))}

    return InformationRetrievalEvaluator(
        queries=queries,
        corpus=corpus,
        relevant_docs=relevant_docs,
        name="eval",
        show_progress_bar=True,
    )


# -- main ---------------------------------------------------------------------

parser = argparse.ArgumentParser(
    description="Fine-tune a sentence-transformer on Methods2Test pairs."
)
parser.add_argument(
    "--input-dir", type=str, default="processed",
    help="Directory with methods2test_*_embedded.jsonl files.",
)
parser.add_argument(
    "--output-model-dir", type=str, default="models/retrieval_model",
    help="Where to save the fine-tuned model.",
)
parser.add_argument(
    "--output-index-dir", type=str, default="processed",
    help="Where to save encoded candidate embeddings + metadata.",
)
parser.add_argument(
    "--base-model", type=str, default="sentence-transformers/all-MiniLM-L6-v2",
    help="Pre-trained model to fine-tune.",
)
parser.add_argument("--epochs", type=int, default=1, help="Training epochs.")
parser.add_argument("--batch-size", type=int, default=64, help="Training batch size.")
parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate.")
parser.add_argument("--warmup-ratio", type=float, default=0.1, help="Warmup ratio.")
parser.add_argument(
    "--max-train-pairs", type=int, default=None,
    help="Cap training pairs (useful for quick experiments). Default: use all.",
)
parser.add_argument(
    "--eval-sample", type=int, default=1000,
    help="How many eval pairs to use for validation during training.",
)
parser.add_argument("--encode-batch-size", type=int, default=128, help="Batch size for post-training encoding.")
parser.add_argument(
    "--skip-training", action="store_true",
    help="Skip training and load an already fine-tuned model from --output-model-dir. "
         "Useful for re-encoding candidates without retraining.",
)

args = parser.parse_args()

input_dir = Path(args.input_dir).resolve()
output_model = Path(args.output_model_dir).resolve()
output_index = Path(args.output_index_dir).resolve()
output_index.mkdir(parents=True, exist_ok=True)

# discover split files
all_paths = []
train_path, eval_path = None, None
for split in ["train", "eval", "test"]:
    p = input_dir / f"methods2test_{split}_embedded.jsonl"
    if p.exists():
        all_paths.append(p)
        if split == "train":
            train_path = p
        if split == "eval":
            eval_path = p

if train_path is None:
    raise FileNotFoundError("Training JSONL not found in input-dir.")

if args.skip_training:
    # load previously trained model
    print(f"Skipping training, loading model from {output_model} ...")
    model = SentenceTransformer(str(output_model))
else:
    # ---- 1. Load training pairs ----
    print("Loading training pairs ...")
    train_queries, train_candidates = load_pairs([train_path], max_pairs=args.max_train_pairs)
    print(f"  {len(train_queries)} training pairs loaded")

    train_dataset = Dataset.from_dict({"anchor": train_queries, "positive": train_candidates})

    # ---- 2. Set up model + loss ----
    print(f"Loading base model: {args.base_model}")
    model = SentenceTransformer(args.base_model)
    loss = MultipleNegativesRankingLoss(model)

    # ---- 3. Optional eval during training ----
    evaluator = None
    if eval_path and eval_path.exists():
        print("Building IR evaluator from eval split ...")
        evaluator = build_eval_ir(eval_path, sample_size=args.eval_sample)

    # ---- 4. Train ----
    training_args = SentenceTransformerTrainingArguments(
        output_dir=str(output_model / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.lr,
        warmup_steps=args.warmup_ratio,  # float value = ratio in transformers v5+
        fp16=False,
        bf16=False,
        use_cpu=True,
        dataloader_pin_memory=False,
        logging_steps=100,
        save_strategy="epoch",
        eval_strategy="epoch" if evaluator else "no",
        save_total_limit=2,
        load_best_model_at_end=bool(evaluator),
        metric_for_best_model="eval_cosine_ndcg@10" if evaluator else None,
        greater_is_better=True if evaluator else None,
    )

    trainer = SentenceTransformerTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        loss=loss,
        evaluator=evaluator,
    )

    print("Starting training ...")
    trainer.train()

    # save model for reuse (weights, tokenizer, config, modules.json)
    model.save(str(output_model))
    print(f"Fine-tuned model saved to {output_model}")

# ---- 5. Encode all candidates with the fine-tuned model ----
print("Loading all candidates for encoding ...")
metadata = load_all_candidates(all_paths)
candidate_texts = [m["candidate_text"] for m in metadata]
print(f"  Encoding {len(candidate_texts)} candidates ...")

embeddings = model.encode(
    candidate_texts,
    batch_size=args.encode_batch_size,
    show_progress_bar=True,
    normalize_embeddings=True,
    convert_to_numpy=True,
)

emb_path = output_index / "candidate_embeddings.npy"
meta_path = output_index / "candidate_metadata.jsonl"

np.save(str(emb_path), embeddings)
print(f"Saved embeddings ({embeddings.shape}) to {emb_path}")

with meta_path.open("w", encoding="utf-8") as f:
    for m in metadata:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")
print(f"Saved metadata ({len(metadata)} rows) to {meta_path}")

print("Done.")
