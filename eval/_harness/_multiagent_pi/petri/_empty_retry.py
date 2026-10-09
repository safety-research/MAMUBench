"""Retry guard for empty/contentless model responses (the "empty-200" flake).

Anthropic (and occasionally other providers) intermittently return an HTTP
`200` with a malformed or empty body. Inspect parses this into a
*successful* generate whose `ModelOutput` carries no usable content: either
no `choices` at all, or a single assistant message with no text, no
reasoning, and no tool calls. Because it is not an error, neither the
provider/transport retry path nor an external generate timeout catches it
(the call "returned"). The auditor/target `Channel` -- and the judge's
structured-answer loop -- then stalls or spins waiting on content that
never arrives.

`with_empty_retry` wraps a `Model` so each `generate` retries (after a short
backoff) when the output is contentless, self-healing the flake at the one
boundary shared by the auditor, target, and judge. After a bounded number of
empties it raises `EmptyResponseError` (a retryable error) rather than letting
an empty message propagate downstream: on the auditor/judge path the raise
fails the sample so `eval_set` retries the whole cell; on the target path it
surfaces through the `Channel` to the auditor (which can roll back / restart).
The retry count is read from `PETRI_EMPTY_RETRY` (default 4); set
it to `0` to disable the guard. The per-retry backoff (seconds) is read from
`PETRI_EMPTY_RETRY_BACKOFF` (default 1.0). An external generate timeout
remains the backstop.
"""

import os
from collections.abc import Callable
from logging import getLogger
from typing import Any

import anyio
from inspect_ai.model import ContentReasoning, Model, ModelOutput

logger = getLogger(__name__)

DEFAULT_EMPTY_RETRY = 4
"""Default number of *extra* attempts when a generate returns contentless."""

ENV_EMPTY_RETRY = "PETRI_EMPTY_RETRY"
"""Env var overriding the empty-response retry count (`0` disables)."""

DEFAULT_EMPTY_RETRY_BACKOFF = 1.0
"""Default per-retry backoff in seconds before re-issuing an empty generate."""

ENV_EMPTY_RETRY_BACKOFF = "PETRI_EMPTY_RETRY_BACKOFF"
"""Env var overriding the per-retry backoff in seconds."""


class EmptyResponseError(Exception):
    """A generate kept returning contentless output after all retries.

    Raised by an empty-retry-wrapped `Model` so the surrounding `eval_set`
    treats the cell as a retryable failure instead of consuming an empty
    `ModelOutput` (which deadlocks the auditor/target channel and the judge).
    """


def _env_number[T: (int, float)](
    name: str, parser: Callable[[str], T], default: T
) -> T:
    """Parse env var `name` with `parser`, falling back to `default` (warn on invalid)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return parser(raw)
    except ValueError:
        logger.warning("Ignoring invalid %s=%r; using default %s", name, raw, default)
        return default


def empty_retry_count() -> int:
    """Number of empty-response retries, from `PETRI_EMPTY_RETRY` (default 4).

    A value `<= 0` disables the guard.
    """
    return _env_number(ENV_EMPTY_RETRY, int, DEFAULT_EMPTY_RETRY)


def empty_retry_backoff() -> float:
    """Per-retry backoff in seconds, from `PETRI_EMPTY_RETRY_BACKOFF` (default 1.0).

    A value `<= 0` retries immediately with no sleep.
    """
    return _env_number(ENV_EMPTY_RETRY_BACKOFF, float, DEFAULT_EMPTY_RETRY_BACKOFF)


def is_contentless(output: ModelOutput) -> bool:
    """Whether a generate produced no usable content (the empty-200 signature).

    True when the output has no choices at all, or its assistant message has
    no tool calls and no non-whitespace text or reasoning. Reasoning-only
    outputs count as content so a legitimate (if unusual) thinking turn is
    never treated as empty.
    """
    if output.empty:
        return True
    message = output.message
    if message.tool_calls:
        return False
    if output.completion.strip() or message.text.strip():
        return False
    return not any(
        isinstance(part, ContentReasoning)
        and (part.reasoning.strip() or (part.summary or "").strip())
        for part in message.content_list
    )


class _EmptyRetryModel(Model):
    """A `Model` whose `generate` retries contentless (empty-200) responses.

    Wraps an inner `Model`: it copies the inner model's state (so it is a
    fully functional `Model` for attribute access and `isinstance` checks,
    e.g. when handed to the judge's `generate_answer`) but delegates each
    `generate` to the inner model's own bound method, adding only the retry
    loop. The inner (cached) model is not mutated, and delegating to its
    bound `generate` preserves inspect's active-model bookkeeping.
    """

    def __init__(self, inner: Model, retries: int, backoff: float) -> None:
        # mirror the inner model's state so the wrapper behaves like a Model
        # (api/config/role/cache scope) without re-running Model.__init__
        self.__dict__.update(inner.__dict__)
        self._inner = inner
        self._empty_retries = retries
        self._empty_backoff = backoff

    async def generate(self, *args: Any, **kwargs: Any) -> ModelOutput:
        for attempt in range(self._empty_retries + 1):
            output = await self._inner.generate(*args, **kwargs)
            if not is_contentless(output):
                return output
            logger.warning(
                "Empty/contentless response from %s (attempt %d/%d); retrying",
                self.name,
                attempt + 1,
                self._empty_retries + 1,
            )
            if self._empty_backoff > 0:
                await anyio.sleep(self._empty_backoff)
        raise EmptyResponseError(
            f"{self.name} returned an empty/contentless response "
            f"{self._empty_retries + 1} times; failing the cell for retry "
            f"(disable with {ENV_EMPTY_RETRY}=0)"
        )


def with_empty_retry(
    model: Model, *, retries: int | None = None, backoff: float | None = None
) -> Model:
    """Wrap `model` so `generate` retries contentless (empty-200) responses.

    Returns `model` unchanged when retries are disabled (`<= 0`) or when it
    is already wrapped. Otherwise returns a delegating wrapper; the original
    model is not mutated. `retries` defaults to `empty_retry_count()` and
    `backoff` (per-retry sleep in seconds) to `empty_retry_backoff()`.
    """
    n = empty_retry_count() if retries is None else retries
    if n <= 0 or isinstance(model, _EmptyRetryModel):
        return model
    wait = empty_retry_backoff() if backoff is None else backoff
    return _EmptyRetryModel(model, n, wait)
