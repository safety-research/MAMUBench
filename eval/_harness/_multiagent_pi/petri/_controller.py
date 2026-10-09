# Derived from Petri (https://github.com/meridianlabs-ai/inspect_petri), MIT License; see THIRD_PARTY_NOTICES.md.
from contextvars import ContextVar
from typing import Literal, overload

from inspect_ai.model import ChatMessageSystem, ChatMessageTool, ChatMessageUser
from inspect_ai.tool import ToolCallError

from ._channel import Channel
from ._types import (
    SYSTEM,
    TOOL_RESULT,
    USER,
    AuditState,
    Response,
    ResponseOK,
    ResponseT,
    Resume,
    Slot,
    SlotT,
    Stage,
)


class AnchorMap:
    """Mapping from anchor IDs to short sequential IDs (M1, M2, ...).

    Short IDs are an auditor-presentation concern only.
    """

    def __init__(self) -> None:
        self._to_short: dict[str, str] = {}
        self._counter: int = 0

    def shorten(self, anchor_id: str) -> str:
        """Get or assign a short ID for an anchor ID."""
        if anchor_id not in self._to_short:
            self._counter += 1
            short = f"M{self._counter}"
            self._to_short[anchor_id] = short
        return self._to_short[anchor_id]


class Controller:
    """Auditor-side handle for driving the target.

    Wraps `Channel` with typed staging and convenience builders. Auditor tools obtain the current instance via `controller()`. Extensions add new staged categories via `Slot` constants and the generic `stage()` primitive (e.g. ``controller().stage(REWRITE, text, key=...)``) — no subclassing required.

    All methods raise `TargetError` if the target responds with `ResponseError`.
    """

    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._anchors = AnchorMap()

    @property
    def channel(self) -> Channel:
        """The underlying transport channel."""
        return self._channel

    @property
    def state(self) -> AuditState:
        """Observable audit state."""
        return self._channel.state

    def short_id(self, anchor_id: str | None) -> str:
        """Assign and return a short sequential ID (M1, M2, ...) for an anchor ID.

        Accepts ``str | None`` because `ChatMessage.id` is typed optional, but inspect always assigns one on construction — passing ``None`` is a bug.
        """
        assert anchor_id is not None
        return self._anchors.shorten(anchor_id)

    # ---- staging ----

    async def stage(
        self, slot: Slot[SlotT], value: SlotT, *, key: str | None = None
    ) -> ResponseOK:
        """Stage a value for the target.

        Typed staging primitive consumed by `TargetContext.require` / `TargetContext.take` on the target side. Use this from custom auditor tools to pass arbitrary keyed payloads (e.g. ``controller().stage(REWRITE, text, key="0")``) without defining new dispatch paths.

        Args:
            slot: The `Slot` constant identifying the category.
            value: Value to stage.
            key: Key within the category. ``None`` for singleton categories.
        """
        return await self._channel.request(
            Stage(slot=slot, key=key, value=value), ResponseOK
        )

    async def stage_with_anchor(
        self, slot: Slot[SlotT], value: SlotT, *, key: str | None = None
    ) -> str:
        """Stage a value and return its short anchor ID."""
        cmd = Stage(slot=slot, key=key, value=value)
        await self._channel.request(cmd, ResponseOK)
        return self.short_id(cmd.anchor_id)

    async def stage_user(self, content: str) -> str:
        """Build and stage a user message; returns its short anchor ID."""
        return await self.stage_with_anchor(USER, ChatMessageUser(content=content))

    async def stage_system(self, content: str) -> str:
        """Build and stage a system message; returns its short anchor ID."""
        return await self.stage_with_anchor(SYSTEM, ChatMessageSystem(content=content))

    async def stage_tool_result(
        self,
        tool_call_id: str,
        result: str,
        status: Literal["success", "error"] = "success",
    ) -> str:
        """Build and stage a tool result; returns its short anchor ID."""
        msg = ChatMessageTool(
            content=result if status == "success" else "",
            tool_call_id=tool_call_id,
            error=ToolCallError("unknown", result) if status == "error" else None,
        )
        return await self.stage_with_anchor(TOOL_RESULT, msg, key=tool_call_id)

    # ---- control ----

    @overload
    async def resume(self, *, expected: type[ResponseT]) -> ResponseT: ...
    @overload
    async def resume(self, *, expected: None = None) -> Response: ...

    async def resume(self, *, expected: type[ResponseT] | None = None) -> Response:
        """Resume target execution.

        Returns `ResponseOutput` for the standard target. Custom target drivers may return other `Response` types — for example, dish returns a notification when scaffold injections are detected. `ResponseError` is always raised as `TargetError` rather than returned.

        To prefill the target's next assistant message, call ``stage(PREFILL, text)`` before `resume()`.

        Args:
            expected: If provided, validates that the response is this type (raising `TypeError` otherwise) and narrows the return type for the caller.
        """
        return await self._channel.request(Resume(), expected)

    async def end_conversation(self) -> None:
        """End the conversation (idempotent)."""
        await self._channel.end_conversation()


def controller() -> Controller:
    """Auditor-side control handle for the current audit."""
    try:
        return _controller.get()
    except LookupError:
        raise RuntimeError(
            "Controller can only be accessed within a running audit."
        ) from None


def channel() -> Channel:
    """Transport channel for the current audit. Equivalent to ``controller().channel``."""
    return controller().channel


def init_controller(ctrl: Controller) -> Controller:
    """Set the current `Controller` for the running audit."""
    _controller.set(ctrl)
    return ctrl


_controller: ContextVar[Controller] = ContextVar("_audit_controller")
