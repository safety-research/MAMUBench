"""Deterministic per-sample world seeding (shared by every env)."""

from __future__ import annotations

import zlib


def world_seed(name: str, epoch: int) -> int:
    """The canonical per-sample seed: `crc32("<scenario>|e<epoch>")` — drives all world jitter.

    Identical to the helper both `api_budget_contention` and `gpu_contention` originally duplicated, so
    reruns of shipped cells keep their exact seeded values.
    """
    return zlib.crc32(f"{name}|e{epoch}".encode())
