"""Model-role binding for the simulated harness's clinic driver (thinking summaries, request options, keys).

`role_model` binds a role to its key and request options. Importing this module installs a provider-level patch
that makes Claude Opus requests return readable thinking SUMMARIES alongside `speed: fast`.

Env knobs (all optional):
- `MAX_CONNECTIONS` (default 12) — pinned on each role's own GenerateConfig (eval_set's max_connections only
  sizes the active model's pool; a pre-bound role would otherwise fall back to the provider default 10).
- `PETRI_GENERATE_TIMEOUT` (default 900s) — per-generate retry budget, pinned per role (turns a hung target
  generate into a retryable error rather than an unbounded block).
- `PETRI_MAX_RETRIES` (default 0 = inspect default) — per-role max_retries.
- `OPUS_NO_FAST=1` / `GPT_FAST=0` — leave out `speed: fast` (Claude Opus) / `service_tier="priority"`
  (GPT-5.6-sol/terra); the simulated harness pins `OPUS_NO_FAST=0 GPT_FAST=1`, the clinic's setting of record.
"""

from __future__ import annotations

import os

from inspect_ai.model import GenerateConfig, get_model

FAST_BETA = "fast-mode-2026-02-01"

#: `max_tokens` for a role that thinks (here and in `_eval_runner.target_model`): room for adaptive thinking plus the reply.
ADAPTIVE_THINKING_MAX_TOKENS = 32_000


def _force_opus_thinking_summaries() -> None:
    """Force the opus roles to emit thinking SUMMARIES, compatibly with `speed: fast`.

    At the provider level, for opus requests, set `thinking={type:adaptive, display:summarized}` and drop
    `output_config`. This guarantees opus returns a readable thinking SUMMARY (`ContentReasoning.summary`,
    which Petri's `format_content` renders as `<thinking_summary>` inside the `<target_response>` the
    auditor sees), and it lets summarized thinking coexist with `speed:fast` (which rejects the
    `output_config` the effort param would otherwise set). Scoped to opus by model name, so non-opus
    auditor/judge are untouched.
    """
    from inspect_ai.model._providers import anthropic as _ap

    orig = _ap.AnthropicAPI.completion_config

    def patched(self, config):  # noqa: ANN001, ANN202
        out = orig(self, config)
        req = out[0] if isinstance(out, tuple) else out
        if isinstance(req, dict) and "opus" in str(getattr(self, "model_name", "")):
            if req.get("thinking"):
                req["thinking"] = {"type": "adaptive", "display": "summarized"}
            req.pop("output_config", None)
        return out

    _ap.AnthropicAPI.completion_config = patched


_force_opus_thinking_summaries()


def role_model(
    model_id: str,
    *,
    thinking: bool = False,
    thinking_effort: str = "high",
    api_key: str | None = None,
):  # noqa: ANN201
    """Bind a role to its key (`api_key`; None = the ambient `ANTHROPIC_API_KEY`) and request options.

    A thinking role runs with `reasoning_effort` (default high) so inspect requests adaptive thinking with
    `display="summarized"`. Claude Opus roles send `speed: fast` with the fast-mode beta header and GPT-5.6-sol/terra
    `service_tier="priority"`: part of the clinic's setting of record, since its time limit is wall-clock.
    """
    is_anthropic = model_id.startswith("anthropic/")
    # non-Anthropic providers read their own env key (OPENAI_API_KEY etc.); binding the Anthropic key
    # onto them would be passed through to the wrong API.
    key = api_key if is_anthropic else None
    # `speed: fast` and its beta header are Anthropic API options: an OpenRouter id naming an Opus model
    # (`openrouter/anthropic/claude-opus-*`) goes through the OpenAI-compatible client, which has neither.
    use_fast = (
        is_anthropic and "opus" in model_id and os.environ.get("OPUS_NO_FAST") != "1"
    )
    use_service_tier = (
        model_id.startswith(("openai/gpt-5.6-sol", "openai/gpt-5.6-terra"))
        and os.environ.get("GPT_FAST", "1") == "1"
    )
    # Pin this role model's OWN max_connections + timeout from the env: eval_set's max_connections only
    # sizes the active model's pool, and a pre-bound role whose config omits these falls back to the
    # provider defaults (10 connections, unbounded generate), silently capping throughput / hanging.
    conn = int(os.environ.get("MAX_CONNECTIONS", "12"))
    gen_timeout = int(os.environ.get("PETRI_GENERATE_TIMEOUT", "900"))
    cfg_kw: dict = {"max_connections": conn}
    if gen_timeout > 0:
        cfg_kw["timeout"] = gen_timeout
    max_retries = int(os.environ.get("PETRI_MAX_RETRIES", "0"))
    if max_retries > 0:
        cfg_kw["max_retries"] = max_retries
    if thinking:
        cfg_kw["reasoning_effort"] = thinking_effort
        cfg_kw["max_tokens"] = ADAPTIVE_THINKING_MAX_TOKENS
    cfg = GenerateConfig(**cfg_kw)
    kw: dict = {"memoize": False, "config": cfg}
    if key is not None:
        kw["api_key"] = key
    if use_fast:
        kw["betas"] = [FAST_BETA]
        kw["extra_body"] = {"speed": "fast"}
    if use_service_tier:
        # native provider model-arg (inspect openai provider __init__ takes service_tier)
        kw["service_tier"] = "priority"
    if model_id.startswith("openrouter/openai/"):
        # OpenAI routes validate function schemas in strict mode when inspect's default
        # strict_tools=True rides along; the pi/clinic tools declare optional params outside
        # `required`, which strict rejects wholesale ("Missing 'offset'" on gpt-5.6).
        # Lax validation sends the schemas byte-identical to every other model.
        kw["strict_tools"] = False
    if not thinking and model_id.startswith("openrouter/"):
        # qwen3.8-max reasons by DEFAULT; absent an explicit suppression the no-thinking
        # setting would silently not apply to it. OpenRouter's reasoning.enabled=false is
        # the provider-normalized off switch, sent through inspect's openrouter model arg (the
        # client forwards unknown model args to the OpenAI SDK, which takes no `extra_body` there).
        # (Anthropic: thinking is simply not requested; gpt-5.6 native: adaptive-minimal when no
        # effort is requested.)
        kw["reasoning_enabled"] = False
    return get_model(model_id, **kw)


def build_roles(
    auditor: str, target: str, judge: str, api_key: str | None = None
) -> dict:
    """The standard {auditor, target, judge} role map.

    The auditor reasons (so the world-author stays self-consistent; `AUDITOR_THINKING=0` turns it off); the
    target reasons at `TARGET_THINKING`. The judge runs without thinking.
    """
    return {
        "auditor": role_model(
            auditor,
            thinking=os.environ.get("AUDITOR_THINKING", "1") != "0",
            api_key=api_key,
        ),
        # TARGET_THINKING: "0" = off, "low"/"medium"/"high" = that reasoning effort, "1"/unset =
        # legacy high. Identity-bearing — never pool across thinking modes (the paper's clinic runs:
        # Anthropic targets off, GPT targets medium).
        "target": role_model(
            target,
            thinking=(_tt := os.environ.get("TARGET_THINKING", "1")) != "0",
            thinking_effort=_tt if _tt in ("low", "medium", "high") else "high",
            api_key=api_key,
        ),
        "judge": role_model(judge, api_key=api_key),
    }


__all__ = ["role_model", "build_roles", "FAST_BETA"]
