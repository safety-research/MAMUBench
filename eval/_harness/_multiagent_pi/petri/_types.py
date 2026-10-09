# Derived from Petri (https://github.com/meridianlabs-ai/inspect_petri), MIT License; see THIRD_PARTY_NOTICES.md.
from __future__ import annotations

from typing import Any, Generic, TypeVar

from inspect_ai.model import (
    ChatMessage,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    ModelOutput,
)
from inspect_ai.tool import ToolError, ToolInfo
from pydantic import BaseModel, ConfigDict, model_validator
from shortuuid import uuid

ResponseT = TypeVar("ResponseT", bound="Response")
SlotT = TypeVar("SlotT")


class Slot(Generic[SlotT]):
    """Typed staging category.

    A `Slot` constant identifies a category of staged values in the target's staging store and binds the value type so that `Controller.stage(slot, value)` and `TargetContext.require(slot)` are statically typed end-to-end. Define one module-level constant per category and import it everywhere — slots are compared by **identity**, so two `Slot("x")` constructions are distinct, non-interchangeable categories even if their names match.

    Built-in slots are `SYSTEM`, `USER`, `TOOL_RESULT`, and `PREFILL`. Extensions add their own (e.g. ``REWRITE = Slot[str]("rewrite")``).
    """

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name
        """Display name for error messages. Slots are compared by instance identity (stricter than name), so two `Slot("x")` constructions are distinct even with matching names — always import the canonical constant rather than reconstructing."""


SYSTEM = Slot[ChatMessageSystem]("system")
"""Staging slot for the target's system message."""

USER = Slot[ChatMessageUser]("user")
"""Staging slot for the next user message."""

TOOL_RESULT = Slot[ChatMessageTool]("tool_result")
"""Staging slot for tool results. Keyed by tool call id."""

PREFILL = Slot[str]("prefill")
"""Staging slot for an assistant prefill for the next generation."""


class TargetError(ToolError):
    """Raised when the target responds with `ResponseError`.

    Subclasses `ToolError` so that auditor tool functions can let it propagate naturally — inspect's tool harness catches it and surfaces the error message to the auditor model. Non-tool callers should catch `TargetError` explicitly when they need to handle target-side protocol errors.
    """


class Command(BaseModel):
    """Base class for commands that can be sent to the target."""


class Stage(Command):
    """Stage a value for the target to consume via `TargetContext.require` or `TargetContext.take`.

    This is the wire-level staging command. The category is identified by `slot` (a `Slot` constant, used directly as the key into the target's staging store); the typed surface is `Controller.stage(slot, value)` on the auditor side and `TargetContext.require(slot)` / `TargetContext.take(slot)` on the target side. Both `slot` and `value` are passed by reference (in-process channel) and are never serialized.
    """

    slot: Slot[Any]
    """Category identifier."""

    key: str | None = None
    """Key within this category. ``None`` for singleton categories (one value per turn)."""

    value: Any
    """Staged value."""

    anchor_id: str = ""
    """Rollback anchor for this staging — `value.id` if it has one, else a fresh uuid."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def _derive_anchor(self) -> "Stage":
        if not self.anchor_id:
            vid = getattr(self.value, "id", None)
            self.anchor_id = vid if isinstance(vid, str) else uuid()
        return self


class Resume(Command):
    """Resume target. Zero-field control marker — data (including prefill) is staged separately."""


class EndConversation(Command):
    """End the conversation."""


class Response(BaseModel):
    """Base class for responses that can be yielded from the target."""


class ResponseOutput(Response):
    """Model output response."""

    output: ModelOutput
    """Output from model generation."""


class ResponseOK(Response):
    """Success response."""


class ResponseError(Response):
    """Error response."""

    error: str
    """Error description."""


class AuditState:
    """Observable state of the current audit."""

    def __init__(
        self,
        seed_instructions: str,
        seed_tools: list[ToolInfo] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._seed_instructions = seed_instructions
        self._seed_tools = seed_tools
        self._metadata = metadata or {}
        self._messages: list[ChatMessage] | None = None
        self._tools: list[ToolInfo] | None = None

    def connect(self, messages: list[ChatMessage], tools: list[ToolInfo]) -> None:
        """Connect live target state.

        Establishes shared references so that `messages` and `tools` reflect the target agent's current state. Called by `TargetContext.__init__` at the start of each trajectory; the target agent must mutate the `messages` list in place (no reassignment) to keep the auditor's view live.
        """
        self._messages = messages
        self._tools = tools

    @property
    def seed_instructions(self) -> str:
        """Seed instructions for the audit."""
        return self._seed_instructions
