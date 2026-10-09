"""The part of Petri's target runtime the simulated harness runs: the auditor-to-target channel and the target agent.

`Channel` carries commands from the auditor seat (here the scripted driver and the escalation handler, through
`Controller`) to each target, and responses back. `TargetContext` is the target-side end, and `target_agent` is the
model the target seat runs. `Trajectory` records the target's turns as anchor events in the eval log.
`with_empty_retry` retries contentless (empty-200) generations, and `_formatting` renders a target turn as text.

Derived from a fork of Petri (https://github.com/meridianlabs-ai/inspect_petri, MIT License; see
THIRD_PARTY_NOTICES.md). Only the code the released runs reach is kept. Upstream's auditor tools, rollback and
replay, tool creation and audit continuation are not here.
"""

from ._agent import target_agent
from ._channel import Channel
from ._context import TargetContext
from ._controller import Controller, channel, controller, init_controller
from ._empty_retry import with_empty_retry
from ._history import History, Trajectory
from ._span_provider import make_span_id_provider
from ._types import PREFILL, ResponseOutput, TargetError

__all__ = [
    "Channel",
    "Controller",
    "History",
    "PREFILL",
    "ResponseOutput",
    "TargetContext",
    "TargetError",
    "Trajectory",
    "channel",
    "controller",
    "init_controller",
    "make_span_id_provider",
    "target_agent",
    "with_empty_retry",
]
