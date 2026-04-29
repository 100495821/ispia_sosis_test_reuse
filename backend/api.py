"""
FastAPI server for the SEAI retrieval + generation pipeline.

Starts once, preloads:
  - embedding model (fine-tuned by default)
  - candidate embeddings and metadata index

Then serves `/generate` requests from the frontend.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import numpy as np
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import Field

from embedder import configure_model
from generator import extract_test_method_name
from loader import load_candidates_from_hf_index
from loader import load_candidates_from_hf_jsonl
from models import Feature
from pipeline import run


HF_DATASET_REPO = os.getenv("SEAI_HF_DATASET_REPO", "EthanS38/test_case_dataset")
HF_MODEL_REPO = os.getenv("SEAI_HF_MODEL_REPO", "EthanS38/test_case_retreival")
HF_EMB_FILENAME = os.getenv("SEAI_HF_EMB_FILENAME", "candidate_embeddings.npy")
HF_META_PRIMARY = os.getenv("SEAI_HF_META_FILENAME", "candidate_metadata-002.jsonl")
HF_META_FALLBACK = os.getenv("SEAI_HF_META_FALLBACK", "candidate_metadata.jsonl")
HF_VANILLA_JSONL = os.getenv("SEAI_HF_VANILLA_JSONL", "methods2test_eval_embedded.jsonl")

TOP_K_DEFAULT = 5
TOP_K_MAX = 20
DESCRIPTION_MAX_CHARS = 160


@dataclass
class RuntimeState:
    use_vanilla: bool
    corpus_embeddings: np.ndarray
    test_cases: list


class GenerateRequest(BaseModel):
    focalMethod: str = Field(..., min_length=1)
    topK: int = Field(default=TOP_K_DEFAULT, ge=1, le=TOP_K_MAX)
    skipGeneration: bool = False


def _build_feature(focal_method: str) -> Feature:
    return Feature(name="user_feature", description="", code=focal_method)


def _truncate(text: str, max_chars: int = DESCRIPTION_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _display_name(source_name: str, code: str) -> str:
    method_name = extract_test_method_name(code or "")
    if method_name != "test_unknown":
        return method_name
    return os.path.basename(source_name)


def _load_candidate_pool(use_vanilla: bool):
    if use_vanilla:
        return load_candidates_from_hf_jsonl(
            dataset_repo=HF_DATASET_REPO,
            jsonl_filename=HF_VANILLA_JSONL,
            max_items=None,
        )

    return load_candidates_from_hf_index(
        dataset_repo=HF_DATASET_REPO,
        emb_filename=HF_EMB_FILENAME,
        meta_filenames=(HF_META_PRIMARY, HF_META_FALLBACK),
    )


app = FastAPI(title="SEAI Backend API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    use_vanilla = os.getenv("SEAI_USE_VANILLA", "0") == "1"

    configure_model(use_vanilla=use_vanilla, model_repo=HF_MODEL_REPO)
    corpus_embeddings, test_cases = _load_candidate_pool(use_vanilla=use_vanilla)

    app.state.runtime = RuntimeState(
        use_vanilla=use_vanilla,
        corpus_embeddings=corpus_embeddings,
        test_cases=test_cases,
    )


@app.get("/health")
def health():
    runtime = getattr(app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Runtime not initialized")

    return {
        "ok": True,
        "useVanilla": runtime.use_vanilla,
        "candidateCount": len(runtime.test_cases),
    }


@app.post("/generate")
def generate(request: GenerateRequest):
    runtime = getattr(app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Runtime not initialized")

    focal_method = request.focalMethod.strip()
    if not focal_method:
        raise HTTPException(status_code=400, detail="focalMethod cannot be empty")

    feature = _build_feature(focal_method)
    output = run(
        feature=feature,
        test_cases=runtime.test_cases,
        top_k=request.topK,
        corpus_embeddings=runtime.corpus_embeddings,
        feature_embedding=None,
        skip_generation=request.skipGeneration,
    )

    reusable = []
    for index, result in enumerate(output.ranked_tests[: request.topK]):
        test_case = result.test_case
        reusable.append(
            {
                "id": f"r{index + 1}",
                "kind": "reusable",
                "name": _display_name(test_case.name, test_case.code),
                "description": _truncate(test_case.description or test_case.name),
                "code": test_case.code,
                "score": float(result.score),
            }
        )

    amplified_code = output.generated_test.strip()
    if not amplified_code:
        amplified_code = "// No generated test available"

    response = {
        "focalMethod": focal_method,
        "reusable": reusable,
        "amplified": {
            "id": "a1",
            "kind": "amplified",
            "name": _display_name("generated", amplified_code),
            "description": "AI-generated JUnit test suggestion from retrieved context.",
            "code": amplified_code,
        },
        "generatedAt": int(time.time() * 1000),
    }
    return response