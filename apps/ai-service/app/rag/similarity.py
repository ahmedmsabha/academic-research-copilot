"""Similarity helpers for in-memory retrieval (tests / memory store)."""

from __future__ import annotations

import math


def cosine_distance(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vector dimensions must match.")
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for left, right in zip(a, b, strict=True):
        dot += left * right
        norm_a += left * left
        norm_b += right * right
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    similarity = dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
    # Clamp numerical noise into [-1, 1].
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity
