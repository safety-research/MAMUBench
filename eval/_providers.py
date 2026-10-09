"""Provider + key resolution shared by every eval: Anthropic, OpenAI and OpenRouter through pi.

pi (`@earendil-works/pi-coding-agent` 0.77.0) speaks to each provider natively and accepts any model
id for it (an unknown id runs through pi's custom-model-id fallback on that provider's API). The
evals only need to know two things per run: which provider the model id belongs to, and which
environment variable holds that provider's key.

    --model claude-sonnet-5                        -> anthropic  (ANTHROPIC_API_KEY)
    --model gpt-5.6-sol / o3 / o4-mini             -> openai     (OPENAI_API_KEY)
    --model anthropic/claude-sonnet-4.5             -> openrouter (OPENROUTER_API_KEY / OPEN_ROUTER_KEY)
    --model qwen/qwen3-235b-a22b --provider openrouter

A model id with a `/` is an OpenRouter id (its ids are `<vendor>/<model>`); `--provider` overrides
every inference; `--api-key` / `--key-env` override the key lookup. The key is handed to pi through
its per-seat auth file, never a seat's process environment.
"""

from __future__ import annotations

import os

#: Every provider the evals run. The personal_assistant runtime's thinking gate is patched to the same set.
PROVIDERS: tuple[str, ...] = ("anthropic", "openai", "openrouter")

#: Provider -> the conventional key variable(s), first non-empty wins.
KEY_ENV_VARS: dict[str, tuple[str, ...]] = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY", "OPEN_ROUTER_KEY"),
}

#: Model-id prefixes pi's native providers own.
PROVIDER_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("claude-", "anthropic"),
    ("gpt-", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
)

#: pi 0.77.0's thinking levels (`--thinking`).
PI_THINKING_LEVELS: tuple[str, ...] = (
    "off",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
)

#: Default pi thinking level per provider. Anthropic seats run thinking OFF (the paper's
#: surface, byte-identical prompts); OpenAI seats run reasoning effort `medium` (as in the paper's
#: GPT runs); OpenRouter models have no reference and default to off. pi clamps an unsupported level up to the
#: model's next supported one: a catalog model that cannot switch reasoning off (`thinkingLevelMap.off: null`) runs
#: at its lowest level, while an id missing from pi's catalog (its custom-model-id fallback, a reasoning model) is
#: sent `reasoning.effort: none`, which a model that requires reasoning refuses on every turn (Qwen3.8-max:
#: "Reasoning is mandatory for this endpoint"); such a model needs `--thinking minimal`.
THINKING_BY_PROVIDER: dict[str, str] = {
    "anthropic": "off",
    "openai": "medium",
    "openrouter": "off",
}


def provider_for(model: str, explicit: str | None = None) -> str:
    """The pi provider a model id runs on (`explicit` wins; `/` means OpenRouter)."""
    if explicit:
        if explicit not in PROVIDERS:
            raise SystemExit(
                f"unknown provider {explicit!r}; the evals run {', '.join(PROVIDERS)}"
            )
        return explicit
    if "/" in model:
        return "openrouter"
    for prefix, provider in PROVIDER_BY_PREFIX:
        if model.startswith(prefix):
            return provider
    raise SystemExit(
        f"cannot infer a pi provider for model {model!r}; pass --provider "
        f"({', '.join(PROVIDERS)}). OpenRouter ids look like <vendor>/<model>."
    )


def resolve_api_key(
    provider: str, key_env: str | None = None, explicit: str | None = None
) -> str:
    """The provider key: `explicit`, else `key_env`, else the provider's conventional variable(s)."""
    if explicit:
        return explicit
    names = (key_env,) if key_env else KEY_ENV_VARS.get(provider, ())
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        f"no API key for provider {provider!r}: set {' or '.join(names) or '--key-env'} "
        "(or pass --api-key)"
    )


def path_safe_model(model: str) -> str:
    """A model id as a path component (`anthropic/claude-sonnet-4.5` -> `anthropic__claude-sonnet-4.5`)."""
    return model.replace("/", "__")
