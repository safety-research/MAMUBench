# Derived from Petri (https://github.com/meridianlabs-ai/inspect_petri), MIT License; see THIRD_PARTY_NOTICES.md.
import functools
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any, Literal, ParamSpec, TypeVar, overload

from inspect_ai._util.exception import TerminateSampleError
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    ModelOutput,
)
from inspect_ai.tool import ToolCall, ToolInfo
from inspect_ai.util import LimitExceededError

from ._channel import Channel
from ._history import Trajectory
from ._types import (
    PREFILL,
    SYSTEM,
    TOOL_RESULT,
    USER,
    Command,
    EndConversation,
    ResponseError,
    ResponseOK,
    ResponseOutput,
    Resume,
    Slot,
    SlotT,
    Stage,
)

P = ParamSpec("P")
R = TypeVar("R")

_DEFAULT_RECOVERY_HINT = (
    "If you have the rollback_conversation or restart_conversation tools, roll back "
    "to any earlier message — the failed call will be retried. Otherwise, call "
    "end_conversation."
)


class TargetContext:
    """Target-side handle for receiving auditor commands.

    Wraps `Channel` with the staging store and command-dispatch loop. The target agent constructs one per trajectory. Subclass to add extension-specific accessors (e.g. ``DishTargetContext.rewrites``).
    """

    def __init__(
        self,
        channel: Channel,
        trajectory: Trajectory,
        *,
        messages: list[ChatMessage] | None = None,
        tools: list[ToolInfo] | None = None,
    ) -> None:
        """Create a target context.

        Immediately connects `messages` and `tools` to the channel's `AuditState` so the auditor can observe the target's live conversation. The target must **mutate** the passed list (e.g. `messages.append(...)`) rather than reassigning — the auditor holds the same reference.

        Args:
            channel: The transport channel shared with the auditor.
            trajectory: Beginning trajectory.
            messages: The target's live conversation messages. The auditor observes this list through `channel.state.messages`. If omitted, the auditor sees an empty conversation.
            tools: Pre-registered tool definitions available to the target from the start of conversation. Also observable by the auditor.
        """
        # initialize state
        self._channel = channel
        self._trajectory = trajectory
        self._staged: dict[Slot[Any], dict[str | None, Any]] = {}
        self._tools: list[ToolInfo] = list(tools) if tools else []
        # Stage-acceptance policy: per-slot allowed-key sets. A slot absent
        # from the dict is unrestricted. Seeded so that tool-result staging
        # before the first `send_output()` is rejected.
        self._expected: dict[Slot[Any], set[str | None]] = {TOOL_RESULT: set()}

        # share live references with the channel's AuditState so the auditor
        # can observe the target's conversation and tools
        channel.state.connect(
            messages=messages if messages is not None else [], tools=self._tools
        )

        # create replay-aware functions for auditor interactions
        self._next_command = trajectory.replayable(channel.next_command)
        self._send_response = trajectory.replayable(
            channel.send_response, deterministic=True
        )

    @property
    def tools(self) -> list[ToolInfo]:
        """Current tool definitions for target."""
        return self._tools

    def replayable(
        self,
        fn: Callable[P, Awaitable[R]],
        *,
        deterministic: bool = False,
        surface_errors: bool = False,
        label: str | None = None,
        recovery_hint: str | None = None,
    ) -> Callable[P, Awaitable[R]]:
        """Wrap `fn` so its results are recorded and replayed by this trajectory.

        Use this to make per-turn side-effecting calls (typically `model.generate`) participate in rollback replay alongside the auditor protocol calls already wrapped internally.

        Args:
            fn: The async function to wrap.
            deterministic: Whether `fn` is deterministic given prior steps (skips re-recording during replay verification).
            surface_errors: If True, exceptions from `fn` are reported to the auditor via `send_error()` — looping until the auditor ends the conversation — instead of propagating and crashing the sample. The control-flow signal `ExitSignal` and inspect's `LimitExceededError` / `TerminateSampleError` always propagate.
            label: Name for the wrapped call in surfaced error messages (defaults to `fn.__name__`).
            recovery_hint: Recovery guidance appended to surfaced error messages. Defaults to toolset-agnostic guidance (rollback/restart if available, otherwise end the conversation); pass a task-specific hint when the available tools are known.
        """
        wrapped = self._trajectory.replayable(fn, deterministic=deterministic)

        @functools.wraps(fn)
        async def surfacing(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await wrapped(*args, **kwargs)
            except (
                ExitSignal,
                LimitExceededError,
                TerminateSampleError,
            ):
                raise
            except Exception as ex:
                while True:
                    await self.send_error(
                        f"Target {label or fn.__name__} failed: "
                        f"{type(ex).__name__}: {ex}. "
                        f"{recovery_hint or _DEFAULT_RECOVERY_HINT}"
                    )

        return surfacing if surface_errors else wrapped

    # ---- generic staging primitives ----

    @overload
    async def require(
        self,
        slot: Slot[SlotT],
        *,
        missing_msg: str | Callable[[set[str | None]], str] | None = None,
    ) -> SlotT: ...

    @overload
    async def require(
        self,
        slot: Slot[SlotT],
        keys: set[str],
        *,
        missing_msg: str | Callable[[set[str | None]], str] | None = None,
    ) -> dict[str, SlotT]: ...

    async def require(
        self,
        slot: Slot[SlotT],
        keys: set[str] | None = None,
        *,
        missing_msg: str | Callable[[set[str | None]], str] | None = None,
    ) -> SlotT | dict[str, SlotT]:
        """Block until the auditor has staged the requested values, then consume them.

        Loops `send_error` → `wait_for_resume` until every wanted key is present in `slot`'s bucket. Reports keys that are staged in the same bucket but were not requested (typically wrong IDs from the auditor). Assumes a `wait_for_resume()` has already happened — i.e. the auditor has had at least one chance to stage.

        Args:
            slot: The `Slot` constant identifying the category.
            keys: Keys to require within the category. Omit for singleton categories (one value per turn, staged with ``key=None``).
            missing_msg: Optional formatter for the error sent to the auditor when keys are missing. Receives the set of missing keys.

        Returns:
            For singleton categories, the staged value. For keyed categories, a dict mapping each requested key to its staged value.
        """
        await self.await_staged(slot, keys, missing_msg=missing_msg)
        bucket = self._staged[slot]
        if keys is None:
            return bucket.pop(None)
        return {k: bucket.pop(k) for k in keys}

    def take(self, slot: Slot[SlotT], *, key: str | None = None) -> SlotT | None:
        """Consume a staged value if present (non-blocking).

        Use for optional per-turn inputs (prefill, optional follow-up user message) or to pop a single keyed entry from a keyed category without awaiting others.

        Args:
            slot: The `Slot` constant identifying the category.
            key: Key within the category. ``None`` for singleton categories.

        Returns:
            The staged value, or ``None`` if nothing is staged at that key.
        """
        return self._staged.get(slot, {}).pop(key, None)

    def expect(self, policy: Mapping[Slot[Any], Iterable[str | None]]) -> None:
        """Restrict which `(slot, key)` stages the next `wait_for_resume` cycle will accept.

        Each entry constrains one slot to exactly the given key set; slots not in `policy` are unrestricted. A `Stage` command for a restricted slot whose key is not in its set is rejected with `ResponseError` at stage time, so the auditor's offending `stage_*` call raises `TargetError` immediately rather than the value landing as a stray. The policy persists until changed — call this before each `send_output`/`send_response` to declare what the upcoming auditor turn may stage.

        Args:
            policy: Map of slot → allowed keys. ``{}`` clears all restrictions. ``{SLOT: {None}}`` restricts a singleton slot to its one key. ``{SLOT: set()}`` rejects every stage in that slot.
        """
        self._expected = {slot: set(keys) for slot, keys in policy.items()}

    # ---- typed convenience wrappers ----

    @overload
    async def system_message(
        self, required: Literal[True] = ...
    ) -> ChatMessageSystem: ...

    @overload
    async def system_message(
        self, required: Literal[False]
    ) -> ChatMessageSystem | None: ...

    async def system_message(self, required: bool = True) -> ChatMessageSystem | None:
        """Receive a system message.

        Args:
           required: Is a system message required? If `True` will prompt the auditor to provide one if none is staged. If `False` will return `None` if none is available.

        Returns:
           System message (can return `None` when `required=False`).
        """
        if not required:
            return self.take(SYSTEM)
        return await self.require(
            SYSTEM,
            missing_msg="You must stage a system message to the target to continue the conversation.",
        )

    @overload
    async def user_message(self, required: Literal[True] = ...) -> ChatMessageUser: ...

    @overload
    async def user_message(
        self, required: Literal[False]
    ) -> ChatMessageUser | None: ...

    async def user_message(self, required: bool = True) -> ChatMessageUser | None:
        """Receive a user message.

        Args:
           required: Is a user message required? If `True` will prompt the auditor to provide one if none is staged. If `False` will return `None` if none is available.

        Returns:
           User message (can return `None` when `required=False`).
        """
        if not required:
            return self.take(USER)
        return await self.require(
            USER,
            missing_msg="You must stage a user message to the target to continue the conversation.",
        )

    def prefill(self) -> str | None:
        """Receive a staged prefill for the next assistant message, if any."""
        return self.take(PREFILL)

    def _staged_prefill(self) -> list[ChatMessageAssistant]:
        """Any staged prefill as the tagged assistant message to offer one generation (else empty)."""
        prefill = self.prefill()
        if not prefill:
            return []
        return [ChatMessageAssistant(content=prefill, metadata={"prefill": True})]

    async def generate_turn(
        self,
        generate: Callable[..., Awaitable[ModelOutput]],
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> ModelOutput:
        """Run one target generation, applying any staged prefill, and append the turn to `messages`.

        Use this in a target driver in place of calling `generate` directly: it owns two rules a driver should not have to re-derive.

        A staged prefill is *offered* to the model as a trailing assistant message, but joins `messages` only **after** the generation returns. A provider that rejects assistant prefill (newer Anthropic models 400 with "the conversation must end with a user message") would otherwise leave the auditor's words in the target's history, and in the auditor's live view of it.

        The offered copy is tagged `metadata={"prefill": True}` — the key transcript renderers read to attribute the text to the auditor rather than to the target — but what joins `messages` is an **untagged** copy. Providers that require it (Anthropic among them) collapse consecutive assistant messages *before* the generation is recorded, and that merge keeps the first message's metadata: a committed tag would spread over the target's own continuation and render the target's words as the auditor's. So the tag rides only on the copy offered to the generation it belongs to, where the prefill still stands alone.

        Args:
            generate: The generation to run, called as `generate(input=..., **kwargs)` — typically the `replayable`-wrapped `model.generate`.
            messages: The driver's live conversation. Mutated in place (the auditor observes the same list).
            **kwargs: Forwarded to `generate` — `tools`, `cache`, and anything else it accepts.

        Returns:
            The model output. Its message has already been appended to `messages`.
        """
        prefill = self._staged_prefill()
        output = await generate(input=[*messages, *prefill], **kwargs)
        messages.extend(m.model_copy(update={"metadata": None}) for m in prefill)
        messages.append(output.message)
        return output

    async def tool_results(self, tool_calls: list[ToolCall]) -> list[ChatMessageTool]:
        """Receive tool results.

        Validates that all results are staged (re-prompting the auditor if needed), then unstages and returns them in the order of `tool_calls`. Fills in each result's `function` field from the originating call so providers that require it (notably Gemini's `FunctionResponse.name`) get the correct name regardless of how the result was staged.

        Args:
            tool_calls: Tool calls to receive results for.

        Returns:
            List with tool messages.
        """
        results = await self.require(
            TOOL_RESULT,
            {tc.id for tc in tool_calls},
            missing_msg=lambda m: (
                f"Missing tool results for tool call ids: {', '.join(sorted(k or '' for k in m))}"
            ),
        )
        for tc in tool_calls:
            results[tc.id].function = tc.function
        return [results[tc.id] for tc in tool_calls]

    async def send_output(self, output: ModelOutput) -> None:
        """Send model output to the auditor and wait for the next `Resume`.

        Call `expect()` first to restrict which stages are accepted while waiting (typically ``{TOOL_RESULT: <output's tool_call_ids>}``).
        """
        await self._send_response(ResponseOutput(output=output))
        await self.wait_for_resume()

    async def send_error(self, error: str) -> None:
        """Send an error to the auditor and wait for the next `Resume`.

        The auditor's pending `resume()` call will raise `TargetError`.
        """
        await self._send_response(ResponseError(error=error))
        await self.wait_for_resume()

    async def next_command(self) -> Command:
        return await self._next_command()

    # TODO(naming): consider renaming `wait_for_resume` / `send_*` around a
    # `yield`-style verb — `send_*` are the target's turn-handoff primitives
    # (reply to the pending Resume, then block until the next one), and
    # "yield" captures that better than "send X then wait for resume".
    async def wait_for_resume(self) -> None:
        """Dispatch auditor commands until the next `Resume`.

        On return the auditor is blocked awaiting a response — the precondition for `require()` and the `send_*` methods. Call this directly only for the initial wait (before the first `Resume`); thereafter use `send_output` / `send_response` / `send_error`, which send the reply and then call this.
        """
        while True:
            # get the next command track it
            command = await self.next_command()

            # dispatch
            match command:
                case Stage(slot=slot, key=key, value=value):
                    if err := self._reject_stage(slot, key):
                        await self._send_response(ResponseError(error=err))
                    else:
                        self._staged.setdefault(slot, {})[key] = value
                        await self._send_response(ResponseOK())

                case Resume():
                    break

                case EndConversation():
                    raise ExitSignal()

                case _:
                    raise TypeError(f"Unknown command type: {type(command).__name__}")

    def _reject_stage(self, slot: Slot[Any], key: str | None) -> str | None:
        """Return an error message if `(slot, key)` is outside the current `expect()` policy."""
        allowed = self._expected.get(slot)
        if allowed is None or key in allowed:
            return None
        if not allowed:
            return f"Not expecting {slot.name} at this point in the conversation."
        pending = ", ".join(sorted(k or "<none>" for k in allowed))
        return f"Unknown {slot.name} key {key!r}. Pending: {pending}."

    async def await_staged(
        self,
        slot: Slot[Any],
        keys: set[str] | None = None,
        *,
        missing_msg: str | Callable[[set[str | None]], str] | None = None,
    ) -> None:
        """Block until all wanted keys are present in `slot`'s bucket (no consume).

        Reports strays — keys staged in the same bucket that were not requested — alongside the missing-keys error so the auditor can self-correct typos and wrong IDs. Use `require()` when you want to consume; use this when a separate consumer will pop entries later (e.g. one-at-a-time from a keyed category).

        Args:
            slot: The `Slot` constant identifying the category.
            keys: Keys to wait for. Omit for singleton categories.
            missing_msg: Error sent to the auditor when keys are missing. A string is used verbatim; a callable receives the set of missing keys and returns the message.
        """
        wanted: set[str | None] = {None} if keys is None else set(keys)
        bucket = self._staged.setdefault(slot, {})
        while missing := wanted - bucket.keys():
            if isinstance(missing_msg, str):
                err = missing_msg
            elif missing_msg is not None:
                err = missing_msg(missing)
            else:
                err = f"Missing {slot.name}: {sorted(k or '<no key>' for k in missing)}"
            if strays := bucket.keys() - wanted:
                err += f" Staged but not expected for {slot.name}: {sorted(k or '<no key>' for k in strays)}."
            await self.send_error(err)


class ExitSignal(Exception):
    """Signal indicating that the conversation has ended."""

    pass
