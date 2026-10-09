# Derived from Petri (https://github.com/meridianlabs-ai/inspect_petri), MIT License; see THIRD_PARTY_NOTICES.md.
from collections.abc import Awaitable, Callable

from inspect_ai.agent import Agent, AgentState, agent
from inspect_ai.model import CachePolicy, ModelOutput, get_model

from ._context import ExitSignal, TargetContext
from ._empty_retry import with_empty_retry
from ._types import TOOL_RESULT

_Generate = Callable[..., Awaitable[ModelOutput]]
"""The `TargetContext.replayable`-wrapped `model.generate`, called as `generate(input=..., tools=..., cache=...)`."""


@agent(name="target")
def target_agent(
    *,
    cache: bool | CachePolicy = False,
    recovery_hint: str | None = None,
    model_role: str = "target",
) -> Agent:
    """Create a target agent that runs under auditor control.

    Args:
        cache: Response caching policy for target generations, passed to the model's `generate` unchanged.
        recovery_hint: Recovery guidance appended to the error surfaced to the auditor when a target generation fails. Defaults to toolset-agnostic guidance (rollback/restart if available, otherwise end the conversation); pass a task-specific hint when the auditor's tools are known.
        model_role: The Inspect model role this target resolves its model from (default `"target"`). Override it to run several targets on distinct models in one audit — a mixed-model roster — by binding each role via `--model-role role=provider/model`.
    """

    async def execute(state: AgentState, context: TargetContext) -> AgentState:

        # resolve model and wrap generate for trajectory replay; the
        # empty-response retry guards against contentless "empty-200"
        # responses that would otherwise stall the auditor/target channel
        target_model = with_empty_retry(get_model(role=model_role))
        generate = context.replayable(
            target_model.generate, surface_errors=True, recovery_hint=recovery_hint
        )

        try:
            # collect initial system + user message from auditor
            await context.wait_for_resume()
            state.messages[:] = [
                await context.system_message(),
                await context.user_message(),
            ]
            await _target_loop(state, context, generate, cache)
        except ExitSignal:
            return state

        return state

    return execute


async def _target_loop(
    state: AgentState,
    context: TargetContext,
    generate: _Generate,
    target_cache: bool | CachePolicy,
) -> None:
    """The target's generate/respond loop.

    Precondition: `state.messages` is ready to generate from (ends in a user or tool message). Each iteration generates, sends the output to the auditor, then consumes the auditor's reply (tool results and/or the next user message) — leaving `state.messages` ready to generate again. Runs until `ExitSignal` propagates from an awaited context call when the auditor ends the conversation.
    """
    while True:
        # do the generation — `generate_turn` applies any staged prefill and appends
        # the turn to state.messages
        state.output = await context.generate_turn(
            generate, state.messages, tools=context.tools, cache=target_cache
        )

        # send output to auditor; expect() restricts what the auditor may stage so
        # a wrong/unsolicited tool result is rejected immediately at stage time
        if tool_calls := state.output.message.tool_calls:
            context.expect({TOOL_RESULT: {tc.id for tc in tool_calls}})
            await context.send_output(state.output)

            # execute tools
            state.messages.extend(await context.tool_results(tool_calls))

            # see if there is a user message
            if user_message := await context.user_message(required=False):
                state.messages.append(user_message)

        # no tool calls — auditor must send a user message
        else:
            context.expect({TOOL_RESULT: set()})
            await context.send_output(state.output)
            state.messages.append(await context.user_message())
