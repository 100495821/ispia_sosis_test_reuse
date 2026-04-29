#!/usr/bin/env python3
"""
Export Java example files from processed Methods2Test JSONL output.

Each JSONL row is expected to contain at least:
- query_text
- candidate_text

Optional field:
- src_fm_fc_ms_ff

For each selected row, this script writes paired .java files:
- <index>_query.java
- <index>_candidate.java

If --include-context is enabled, it also writes:
- <index>_context.java
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


SPLITS = ("train", "eval", "test")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export paired Java files from processed Methods2Test JSONL rows."
    )
    parser.add_argument(
        "--input-jsonl",
        type=str,
        default=None,
        help="Path to a processed JSONL file. If omitted, --processed-dir + --split is used.",
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default="processed",
        help="Directory containing methods2test_<split>_embedded.jsonl files.",
    )
    parser.add_argument(
        "--split",
        type=str,
        choices=SPLITS,
        default="train",
        help="Dataset split used when --input-jsonl is omitted.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="java_examples",
        help="Directory where Java examples will be written.",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=100,
        help="Maximum number of rows to export.",
    )
    parser.add_argument(
        "--include-context",
        action="store_true",
        help="Also export src_fm_fc_ms_ff as a third Java file per example.",
    )
    parser.add_argument(
        "--queries-only",
        action="store_true",
        help="Export only query Java files and omit candidate/context files.",
    )
    return parser.parse_args()


def resolve_input_path(args: argparse.Namespace) -> Path:
    if args.input_jsonl:
        path = Path(args.input_jsonl).expanduser().resolve()
    else:
        path = (
            Path(args.processed_dir).expanduser().resolve()
            / f"methods2test_{args.split}_embedded.jsonl"
        )

    if not path.exists():
        raise FileNotFoundError(f"Input JSONL not found: {path}")
    return path


def iter_jsonl_rows(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} in {path}: {exc}") from exc
            if not isinstance(row, dict):
                continue
            yield row


def safe_comment_text(text: str) -> str:
    # Avoid terminating the Java block comment accidentally.
    return text.replace("*/", "* /")


def write_java_file(path: Path, role: str, source_file: str, content: str) -> None:
    header = (
        "/*\n"
        "Auto-generated from processed Methods2Test JSONL.\n"
        f"Role: {safe_comment_text(role)}\n"
        f"Source: {safe_comment_text(source_file)}\n"
        "*/\n\n"
    )

    # Keep content as-is since retrieval models typically expect original code text.
    body = (content or "").strip()
    full_text = header + body + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(full_text, encoding="utf-8")


def export_examples(
    input_jsonl: Path,
    output_dir: Path,
    num_examples: int,
    include_context: bool,
    queries_only: bool,
) -> int:
    if num_examples <= 0:
        return 0

    queries_dir = output_dir / "queries"
    candidates_dir = output_dir / "candidates"
    context_dir = output_dir / "contexts"
    metadata_path = output_dir / "metadata.jsonl"

    output_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    with metadata_path.open("w", encoding="utf-8") as metadata_file:
        for row in iter_jsonl_rows(input_jsonl):
            query_text = (row.get("query_text") or "").strip()
            candidate_text = (row.get("candidate_text") or "").strip()
            context_text = (row.get("src_fm_fc_ms_ff") or "").strip()
            source_file = str(row.get("source_file") or "")

            if not query_text or not candidate_text:
                continue

            written += 1
            stem = f"example_{written:06d}"

            query_path = queries_dir / f"{stem}_query.java"

            write_java_file(query_path, "query", source_file, query_text)

            record: Dict[str, Any] = {
                "index": written,
                "source_file": source_file,
                "query_file": str(query_path),
            }

            if not queries_only:
                candidate_path = candidates_dir / f"{stem}_candidate.java"
                write_java_file(candidate_path, "candidate", source_file, candidate_text)
                record["candidate_file"] = str(candidate_path)

            if include_context and not queries_only and context_text:
                context_path = context_dir / f"{stem}_context.java"
                write_java_file(context_path, "context", source_file, context_text)
                record["context_file"] = str(context_path)

            metadata_file.write(json.dumps(record, ensure_ascii=False) + "\n")

            if written >= num_examples:
                break

    return written


def main() -> None:
    args = parse_args()
    input_jsonl = resolve_input_path(args)

    output_dir = Path(args.output_dir).expanduser().resolve() / input_jsonl.stem
    count = export_examples(
        input_jsonl=input_jsonl,
        output_dir=output_dir,
        num_examples=args.num_examples,
        include_context=args.include_context,
        queries_only=args.queries_only,
    )

    print(f"Input: {input_jsonl}")
    print(f"Output: {output_dir}")
    print(f"Exported examples: {count}")


if __name__ == "__main__":
    main()
