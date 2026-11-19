"""Repeatable latency diagnostic for the three authorized candidate paths.

Results are hardware-specific diagnostics, not answer-quality or release gates.
"""

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import time
from datetime import date, datetime
from pathlib import Path

from api.app.auth import Actor
from api.app.config import load_settings
from api.app.db import connect
from api.app.embedding import PROFILE
from api.app.retrieval import (
    HYBRID_SEARCH_VERSION,
    SEARCH_VERSION,
    VECTOR_SEARCH_VERSION,
    full_text_chunks,
    hybrid_candidate_chunks,
    vector_chunks,
)


GOLD_PATH = Path(__file__).resolve().parents[1] / "corpus" / "gold.json"
PATHS = (
    ("full_text", SEARCH_VERSION, full_text_chunks),
    ("vector", VECTOR_SEARCH_VERSION, vector_chunks),
    ("hybrid", HYBRID_SEARCH_VERSION, hybrid_candidate_chunks),
)


def summarize(samples_ms: list[float]) -> dict:
    ordered = sorted(samples_ms)
    if not ordered:
        raise ValueError("no timing samples")
    return {
        "count": len(ordered),
        "p50_ms": round(ordered[math.ceil(0.50 * len(ordered)) - 1], 3),
        "p95_ms": round(ordered[math.ceil(0.95 * len(ordered)) - 1], 3),
        "mean_ms": round(statistics.mean(ordered), 3),
        "max_ms": round(ordered[-1], 3),
    }


def benchmark(database_url: str, iterations: int) -> dict:
    if not 1 <= iterations <= 20:
        raise ValueError("iterations must be from 1 to 20")
    gold_bytes = GOLD_PATH.read_bytes()
    corpus = json.loads(gold_bytes)
    cases = corpus["cases"]
    measurements = {name: [] for name, _, _ in PATHS}
    hit_counts = {name: 0 for name, _, _ in PATHS}

    with connect(database_url) as connection:
        postgres_version = connection.execute("SHOW server_version").fetchone()[0]
        vector_version = connection.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        chunk_count = connection.execute("SELECT count(*) FROM source_chunks").fetchone()[0]
    if vector_version is None or chunk_count == 0:
        raise RuntimeError("seeded pgvector chunk index required")

    for item in cases:
        actor = Actor(f"benchmark-{item['id']}", item["tenant"], item["role"])
        recorded_as_of = datetime.fromisoformat(item["recorded_as_of"].replace("Z", "+00:00"))
        valid_on = date.fromisoformat(item.get("valid_on", recorded_as_of.date().isoformat()))
        args = (database_url, actor, item["question"], valid_on, recorded_as_of)
        for name, _, search in PATHS:
            # One unmeasured call warms imports, SQL plans, and local caches.
            search(*args, limit=5)
            for _ in range(iterations):
                started = time.perf_counter_ns()
                hits = search(*args, limit=5)
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
                measurements[name].append(elapsed_ms)
                hit_counts[name] += len(hits)

    if hit_counts["full_text"] == 0:
        raise RuntimeError("full-text candidate path returned no hits for the natural-language fixture")

    return {
        "kind": "candidate_latency_diagnostic",
        "gold_version": corpus["gold_version"],
        "gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
        "case_count": len(cases),
        "iterations_per_case": iterations,
        "warmup_calls_per_case_and_path": 1,
        "limit": 5,
        "valid_on_default": "recorded_as_of date when case omits valid_on",
        "postgres_version": postgres_version,
        "pgvector_version": vector_version[0],
        "embedding_profile": PROFILE,
        "chunk_count": chunk_count,
        "machine": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "processor": platform.processor() or None,
        },
        "paths": {
            name: {"version": version, "total_hits": hit_counts[name], **summarize(measurements[name])}
            for name, version, _ in PATHS
        },
        "interpretation": "Timings only; no retrieval relevance or answer accuracy is claimed.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure authorized candidate-path latency on the synthetic corpus")
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()
    report = benchmark(load_settings().database_url, args.iterations)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
