# Derived from Petri (https://github.com/meridianlabs-ai/inspect_petri), MIT License; see THIRD_PARTY_NOTICES.md.
import functools
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, ParamSpec, TypeVar

from inspect_ai.event import AnchorEvent
from inspect_ai.log import transcript
from shortuuid import uuid

from ._types import Stage

P = ParamSpec("P")
R = TypeVar("R")


def _extract_anchor_id(value: Any) -> str | None:
    """Return the rollback anchor for a recorded step value, or `None` if not rollback-able."""
    if isinstance(value, Stage):
        return value.anchor_id
    msg = getattr(value, "message", None)
    return getattr(msg, "id", None) if msg is not None else None


@dataclass(slots=True, eq=False)
class _Step:
    """One recorded replayable call: its result (value or exception) and anchor."""

    value: Any
    source: str
    error: BaseException | None = None
    deterministic: bool = False
    anchor_id: str | None = field(init=False)

    def __post_init__(self) -> None:
        self.anchor_id = None if self.error else _extract_anchor_id(self.value)


class Trajectory:
    """A recorded span of conversation history.

    Upstream Petri branches a child trajectory on rollback and replays the recorded steps into it; nothing here
    rolls back, so the only trajectory is the root, which records every wrapped call live.
    """

    def __init__(self) -> None:
        self.span_id: str = uuid()
        """Unique identifier for this trajectory span."""

        self.span_counters: dict[tuple[str, str], int] = defaultdict(int)
        """Per-(parent, name) span occurrence counter for `make_span_id_provider`."""

        self._steps: list[_Step] = []

    def replayable(
        self, fn: Callable[P, Awaitable[R]], *, deterministic: bool = False
    ) -> Callable[P, Awaitable[R]]:
        """Wrap `fn` so each call's result is recorded, emitting an `AnchorEvent` when the result has an anchor.

        Args:
            fn: The async function to wrap.
            deterministic: True if `fn`'s result is fully determined by the preceding step (recorded on the step).
        """
        steps = self._steps
        source = fn.__qualname__

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:
                steps.append(
                    _Step(None, source=source, error=exc, deterministic=deterministic)
                )
                raise
            step = _Step(result, source=source, deterministic=deterministic)
            if step.anchor_id is not None:
                transcript()._event(  # pyright: ignore[reportPrivateUsage]
                    AnchorEvent(anchor_id=step.anchor_id, source=source)
                )
            steps.append(step)
            return result

        return wrapper


class History:
    def __init__(self) -> None:
        self._root = Trajectory()

    @property
    def root(self) -> Trajectory:
        return self._root
