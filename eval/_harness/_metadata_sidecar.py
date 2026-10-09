"""Durable sidecars for large experiment sample-metadata values.

Inspect thins large metadata values in `EvalSampleSummary` objects. A resumed `eval_set` can copy completed samples through that lossy representation, so a large ground-truth value must not live only in sample metadata. This module keeps the ordinary metadata field for convenient single-pass reads and writes the same JSON value beside the eval logs for durable reads after a resume.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from inspect_ai.log import EvalSample

METADATA_SIDECAR_DIR_ENV = "PETRI_METADATA_SIDECAR_DIR"
THINNED_METADATA_PLACEHOLDER = "Key removed from summary (> 1k)"


def is_metadata_thinned(value: Any) -> bool:
    """Return whether `value` is Inspect's large-metadata summary placeholder."""
    return value == THINNED_METADATA_PLACEHOLDER


def _sidecar_path(
    root: str | Path, sample_id: str | int, epoch: int, field: str
) -> Path:
    """Return the canonical sidecar path for one sample metadata field."""
    filename = f"{quote(str(sample_id), safe='')}__e{epoch}.json"
    return Path(root) / f"{field}s" / filename


def _legacy_sidecar_path(root: str | Path, sample_id: str | int, field: str) -> Path:
    """Return the pre-convention path used by the original world-sidecar fix."""
    return Path(root) / f"{field}s" / f"{sample_id}.json"


def write_metadata_sidecar(
    sample_id: str | int, epoch: int, field: str, value: Any
) -> Path | None:
    """Atomically persist one metadata value beside the active eval log directory.

    The write is enabled by `PETRI_METADATA_SIDECAR_DIR`, which `_eval_runner.run_resumable(metadata_sidecars=...)` scopes to its `log_dir`. When the variable is unset this is a no-op, so task builders remain usable outside the shared experiment driver.
    """
    root = os.environ.get(METADATA_SIDECAR_DIR_ENV)
    if not root:
        return None

    destination = _sidecar_path(root, sample_id, epoch, field)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.stem}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _epoch_offset(sample: EvalSample) -> int:
    """The sample's `epoch_offset` metadata stamp (0 when absent).

    A top-up run regenerates a source run's missing epochs under a smaller epoch count by shifting the world-seed epoch (`ScenarioSpec.epoch_offset`); its sidecars are keyed by the TRUE (shifted) epoch so they merge with the source root's files. The task stamps the shift into the sample metadata, and every sidecar read applies it here so both plain and shifted samples resolve.
    """
    offset = (sample.metadata or {}).get("epoch_offset", 0)
    return offset if isinstance(offset, int) else 0


def read_metadata_sidecar(
    sample: EvalSample, eval_path: str | Path, field: str
) -> Any | None:
    """Read a sample's sidecar value, including the original legacy layout."""
    root = Path(eval_path).parent
    paths = (
        _sidecar_path(root, sample.id, sample.epoch + _epoch_offset(sample), field),
        _legacy_sidecar_path(root, sample.id, field),
    )
    for path in paths:
        try:
            return json.loads(path.read_text())
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            return None
    return None


def metadata_value(sample: EvalSample, eval_path: str | Path, field: str) -> Any | None:
    """Return intact inline metadata, falling back to its durable sidecar."""
    inline = sample.metadata.get(field)
    if inline is not None and not is_metadata_thinned(inline):
        return inline
    return read_metadata_sidecar(sample, eval_path, field)


def rehydrate_metadata(
    sample: EvalSample, eval_path: str | Path, *fields: str
) -> frozenset[str]:
    """Restore thinned metadata fields from sidecars in place.

    Returns:
        The names of fields restored on `sample`.
    """
    restored: set[str] = set()
    for field in fields:
        inline = sample.metadata.get(field)
        if not is_metadata_thinned(inline):
            continue
        value = read_metadata_sidecar(sample, eval_path, field)
        if value is None:
            continue
        sample.metadata[field] = value
        restored.add(field)
    return frozenset(restored)


__all__ = [
    "METADATA_SIDECAR_DIR_ENV",
    "THINNED_METADATA_PLACEHOLDER",
    "is_metadata_thinned",
    "metadata_value",
    "read_metadata_sidecar",
    "rehydrate_metadata",
    "write_metadata_sidecar",
]
