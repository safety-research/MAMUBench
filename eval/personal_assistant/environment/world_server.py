"""The dinner world as a REAL MCP server (streamable HTTP) + a driver-only admin surface.

One process = one episode's deterministic world. The PAs' pi processes reach it through the
`pi-mcp-bridge` extension; every dinner tool call (`dd_*`, `memory_*`, `find_agents`) dispatches
through `personal_assistant.environment.food`'s own `FoodOrderRouter` — imported, never re-implemented — so the
`action_log` schema, budget-cap rejections, `no_sharing` banner, and payoff inputs are identical
to the sim cells. The peer mailbox (`send_message`/`check_inbox`) is server-owned (the sim keeps
it in the harness), with delivery ledgered through the router's own `on_dm`/`on_deliver` hooks so
`message_log` parity holds.

Identity: each pi seat's bridge authenticates with a per-agent bearer token minted by the driver;
the seat is derived server-side from the token (never from self-report). The driver talks to
`/admin/*` with a separate admin token: world status (beat timing only), turn/diner-message
events (so message-volume is a measured covariate in the ledger), and finalize (settle the world
to horizon, persist `summary.json`).

Transports: MCP streamable HTTP at `/mcp` (stateless + JSON responses — the bridge is a plain
JSON-RPC-over-fetch client); admin is plain JSON over HTTP. Tool-call validation is deliberately
`validate_input=False`: malformed args must reach the router's own arg parsing so a mutating
arg-parse miss lands its `rejected_args` ledger row exactly as in the sim.
"""

from __future__ import annotations

import contextvars
import json
import threading
import time
from pathlib import Path
from typing import Any

from typing import TYPE_CHECKING  # noqa: E402

from inspect_ai.tool import ToolCall  # noqa: E402
from personal_assistant.environment.worlds import (  # noqa: E402
    CELLS,
    build_live_router,
    relativize_deadlines,
    seat_usernames,
    strip_unenforced_deadlines,
)

if TYPE_CHECKING:
    pass

#: The seat identity for the MCP request being served (set by the ASGI auth wrapper; tests set
#: it directly around in-memory calls).
seat_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "dinner_live_seat", default=None
)

#: token -> seat, populated by `build_asgi_app` (the fallback identity path in `current_seat`).
_token_seats: dict[str, str] = {}

#: The two mutually exclusive peer-comms surfaces; whichever the cell does not carry is
#: answered as absent from this console (as is both, in the comms ablation).
_MAILBOX_TOOLS = ("send_message", "check_inbox", "find_agents")
_DM_TOOLS = ("dm_send", "dm_history")


class DinnerWorldCore:
    """One episode's world + mailbox + ledger, transport-free (the offline-testable core)."""

    def __init__(
        self, cell: str, epoch: int, out_dir: Path, git_sha: str = "unknown"
    ) -> None:
        self.cell = CELLS[cell]
        self.epoch = epoch
        self.git_sha = git_sha
        self.router, self.diners = build_live_router(self.cell, epoch)
        self.ids: tuple[str, ...] = self.router.world.seat_ids
        self.usernames: dict[str, str] = seat_usernames(self.cell, self.diners)
        self.recipients: dict[str, str] = {
            username.lower(): seat for seat, username in self.usernames.items()
        }
        if self.cell.topology == "mesh":
            for d in self.diners:
                self.recipients[f"{d.first}'s assistant".lower()] = d.id
        self.mailbox: dict[str, list[tuple[str, str]]] = {i: [] for i in self.ids}
        #: Push-DM mode (`cell.dm`): rendered `[dm from <u>] body` lines
        #: awaiting the recipient's next wake, plus the pairwise history log.
        self.dm_pending: dict[str, list[str]] = {i: [] for i in self.ids}
        self.dm_log: list[dict[str, Any]] = []
        self._preview_revision: dict[str, int] = {}
        #: Seats whose bridge has completed a tools/list (the driver's bridge-up readiness gate).
        self.listed: set[str] = set()
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = out_dir / "ledger.jsonl"
        self._events: list[dict[str, Any]] = []
        self._seq = 0
        self._summary: dict[str, Any] | None = None
        self._lock = threading.RLock()

    # ── ledger ───────────────────────────────────────────────────────────────────────────────────────
    def log(self, kind: str, seat: str | None, payload: dict[str, Any]) -> None:
        with self._lock:
            self._seq += 1
            row = {
                "seq": self._seq,
                "wall_ts": round(time.time(), 3),
                "clock": int(self.router.world.clock),
                "n_actions": len(self.router.world.action_log),
                "n_orders": len(self.router.world.orders),
                "kind": kind,
                "seat": seat,
                **payload,
            }
            self._events.append(row)
            with self._ledger_path.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ── tool dispatch (the MCP surface) ──────────────────────────────────────────────────────────────
    def dispatch(self, seat: str, tool: str, args: dict[str, Any]) -> str:
        """Answer one PA tool call mechanically; always returns rendered text."""
        comms = self.cell.comms and self.cell.topology == "mesh"
        available = (_DM_TOOLS if self.cell.dm else _MAILBOX_TOOLS) if comms else ()
        with self._lock:
            if tool in _MAILBOX_TOOLS + _DM_TOOLS and tool not in available:
                result = f"error: '{tool}' is not available on this console."
            elif tool == "send_message":
                result = self._send_message(seat, args)
            elif tool == "check_inbox":
                result = self._check_inbox(seat)
            elif tool == "dm_send":
                result = self._dm_send(seat, args)
            elif tool == "dm_history":
                result = self._dm_history(seat, args)
            else:
                if (
                    self.cell.fresh_checkout
                    and tool == "dd_checkout_confirm"
                    and self._preview_revision.get(seat) != self._cart_revision()
                    and self._seat_is_cart_creator(seat)
                ):
                    result = (
                        "dd: error: the cart changed since your last checkout preview. "
                        "Run dd_checkout_preview again, then confirm."
                    )
                    self.log("checkout_bounced_stale", seat, {})
                    self.log(
                        "tool_call",
                        seat,
                        {"tool": tool, "args": args, "result_head": result[:200]},
                    )
                    return result
                call = ToolCall(id=f"dl-{self._seq + 1}", function=tool, arguments=args)
                routed = self.router.route(seat, call)
                result = (
                    routed
                    if routed is not None
                    else f"error: '{tool}' is not available on this console."
                )
                if self.cell.fresh_checkout and tool == "dd_checkout_preview":
                    self._preview_revision[seat] = self._cart_revision()
            if self.cell.simultaneous:
                result = strip_unenforced_deadlines(result)
            if self.cell.relative_deadlines:
                result = relativize_deadlines(
                    result, self.router.clock_marker(), self._order_minutes_left()
                )
            self.log(
                "tool_call",
                seat,
                {"tool": tool, "args": args, "result_head": result[:200]},
            )
            return result

    def _seat_is_cart_creator(self, seat: str) -> bool:
        """True when `seat` created the open cart (or no cart is open).

        The stale-preview guard applies only then, so a non-creator confirm falls
        through to the router's `not_creator` rejection and is ledgered as an
        authority block instead of being masked as a stale preview.
        """
        cart = getattr(self.router.world, "cart", None)
        if cart is None:
            return True
        return str(getattr(cart, "creator", seat)) == seat

    def _cart_revision(self) -> int:
        """Count applied cart mutations; the checkout race guard's revision clock."""
        return sum(
            1
            for row in self.router.world.action_log
            if row.get("tool")
            in {"dd_cart_create", "dd_cart_add", "dd_cart_remove", "dd_cart_cancel"}
            and row.get("outcome") == "applied"
        )

    def _peer_usernames(self, seat: str) -> list[str]:
        """The other seats' in-fiction usernames — what a recipient error may name."""
        return sorted(u for i, u in self.usernames.items() if i != seat)

    def _order_minutes_left(self) -> int | None:
        """The world's own place-by window, mechanically (relative-deadline cells)."""
        window = self.router.world.comfort_window_min
        if window is None:
            return None
        return max(int(window) - int(self.router.world.clock), 0)

    def _send_message(self, seat: str, args: dict[str, Any]) -> str:
        """The server-owned mailbox: validate, enqueue, ledger; never claim a false delivery.

        Mirrors `_multiagent_pi.routing._validate_send_message` semantics (unknown recipient
        lists valid usernames; self-send refused) without importing the harness stack into the
        world container.
        """
        to_raw = args.get("to")
        text = args.get("text")
        valid = self._peer_usernames(seat)
        if not isinstance(to_raw, str) or not to_raw.strip():
            return "error: missing required argument 'to'."
        if not isinstance(text, str) or not text.strip():
            return "error: missing required argument 'text'."
        to_id = self.recipients.get(to_raw.strip().lower())
        if to_id is None or to_id not in self.ids:
            self.router.on_dm_undeliverable(seat, to_raw.strip(), text)
            return (
                f"error: unknown recipient '{to_raw.strip()}' — no assistant by that name. "
                f"Valid recipients: {valid}."
            )
        if to_id == seat:
            return "error: that's your own username — message another assistant."
        self.mailbox[to_id].append((self.usernames[seat], text))
        self.router.on_dm(seat, to_id, text)
        self.log("mail_sent", seat, {"to": to_id, "chars": len(text), "text": text})
        return "Delivered to their inbox."

    def _check_inbox(self, seat: str) -> str:
        drained = self.mailbox[seat]
        self.mailbox[seat] = []
        for sender_username, text in drained:
            sender_id = self.recipients.get(sender_username.lower(), sender_username)
            self.router.on_deliver(seat, sender_id, text)
        self.log("inbox_checked", seat, {"n": len(drained)})
        if not drained:
            return "No new messages."
        return "\n\n".join(f"[message from {s}] {t}" for s, t in drained)

    # ── push DMs (`dm_send`: delivered at the recipient's next wake) ────────────────
    def _dm_send(self, seat: str, args: dict[str, Any]) -> str:
        to_raw = args.get("to")
        body = args.get("body")
        contacts = self._peer_usernames(seat)
        if not isinstance(to_raw, str) or not to_raw.strip():
            return "dm: error: missing required argument 'to'."
        if not isinstance(body, str) or not body.strip():
            return "dm: error: empty message body."
        to_id = self.recipients.get(to_raw.strip().lower())
        if to_id is None or to_id not in self.ids:
            self.router.on_dm_undeliverable(seat, to_raw.strip(), body)
            return (
                f"dm: error: no assistant '{to_raw.strip()}' in your contacts. "
                f"Contacts: {', '.join(contacts)}."
            )
        if to_id == seat:
            return "dm: error: that's your own handle."
        sender_u, to_u = self.usernames[seat], self.usernames[to_id]
        self.dm_log.append(
            {
                "t": self.router.clock_marker(),
                "sender": seat,
                "to": to_id,
                "body": body,
                "delivered": False,
            }
        )
        self.dm_pending[to_id].append(f"[dm from {sender_u}] {body}")
        self.router.on_dm(seat, to_id, body)
        self.log("dm_sent", seat, {"to": to_id, "chars": len(body), "text": body})
        return f"dm: sent to {to_u}. The platform will push it when they are idle."

    def _dm_history(self, seat: str, args: dict[str, Any]) -> str:
        with_raw = args.get("with")
        if not isinstance(with_raw, str) or not with_raw.strip():
            return "dm: error: missing required argument 'with'."
        other = self.recipients.get(with_raw.strip().lower())
        if other is None or other not in self.ids:
            contacts = self._peer_usernames(seat)
            return (
                f"dm: error: no assistant '{with_raw.strip()}' in your contacts. "
                f"Contacts: {', '.join(contacts)}."
            )
        limit = args.get("limit")
        limit = limit if isinstance(limit, int) and limit >= 1 else 20
        rows = [r for r in self.dm_log if {r["sender"], r["to"]} == {seat, other}][
            -limit:
        ]
        other_u = self.usernames[other]
        self.log("dm_history", seat, {"with": other, "n": len(rows)})
        if not rows:
            return f"dm: no messages with {other_u} yet."
        out = [f"dm thread with {other_u} (latest {len(rows)}):"]
        for r in rows:
            who = "you" if r["sender"] == seat else other_u
            out.append(f"- [{r['t']}] {who}: {r['body']}")
        return "\n".join(out)

    def dm_drain(self, seat: str) -> list[str]:
        """Pop the seat's pending DM lines for wake render; mark their log rows delivered."""
        with self._lock:
            lines = self.dm_pending.get(seat, [])
            self.dm_pending[seat] = []
            if lines:
                for r in self.dm_log:
                    if r["to"] == seat and not r["delivered"]:
                        r["delivered"] = True
                        self.router.on_deliver(seat, r["sender"], r["body"])
                self.log("dm_delivered", seat, {"n": len(lines)})
            return lines

    def dm_requeue(self, seat: str, lines: list[str]) -> None:
        """Re-pend drained lines after a wake that failed to render (delivery never happened)."""
        with self._lock:
            self.dm_pending[seat] = list(lines) + self.dm_pending.get(seat, [])
            if lines:
                self.log("dm_requeued", seat, {"n": len(lines)})

    # ── admin surface ────────────────────────────────────────────────────────────────────────────────
    def status(self) -> dict[str, Any]:
        """World status for the DRIVER (beat timing + resume nudges) — never diner-visible."""
        with self._lock:
            world = self.router.world
            cart = world.cart
            cart_row = None
            if cart is not None:
                by_slot: dict[str, int] = {}
                for item in cart.items:
                    slot = item.for_first or "(unattributed)"
                    by_slot[slot] = by_slot.get(slot, 0) + 1
                cart_row = {
                    "store": cart.store_id,
                    "creator": cart.creator,
                    "subtotal_cents": cart.subtotal_cents(),
                    "cap_cents": cart.cap_cents,
                    "items_by_diner": by_slot,
                }
            orders = [
                {
                    "id": o.id,
                    "store": o.store_id,
                    "placed_by": o.placed_by,
                    "status": o.status_at(world.clock),
                    "items_by_diner": self._order_slots(o),
                }
                for o in world.orders
            ]
            return {
                "clock": world.clock,
                "clock_hhmm": self.router.clock_marker(),
                "orders_placed": len(orders),
                "orders": orders,
                "cart_open": cart_row,
                "unread": {i: len(self.mailbox[i]) for i in self.ids},
                "dm_pending": {i: len(self.dm_pending[i]) for i in self.ids},
                "order_minutes_left": self._order_minutes_left(),
                "rendered_turns": dict(world.rendered_turns),
                "bridges_listed": sorted(self.listed),
            }

    @staticmethod
    def _order_slots(order: Any) -> dict[str, list[str]]:
        slots: dict[str, list[str]] = {}
        for item in order.items:
            slots.setdefault(item.for_first or "(unattributed)", []).append(
                item.item_id
            )
        return slots

    def record_turn(
        self, seat: str, *, text_bearing: bool, payload: dict[str, Any]
    ) -> None:
        """A rendered pi turn (driver-reported): feeds `rendered_turns` + the ledger."""
        with self._lock:
            self.router.world.note_rendered_turn(seat)
            if text_bearing:
                self.router.world.note_text_answer(seat)
            self.log("turn_rendered", seat, {"text_bearing": text_bearing, **payload})

    def record_diner_msg(self, seat: str, *, diner: str, beat: str, text: str) -> None:
        """A delivered diner->PA message (driver-reported): beat counts become ledger data."""
        self.log(
            "diner_msg",
            seat,
            {"diner": diner, "beat": beat, "chars": len(text), "text": text},
        )

    def finalize(self) -> dict[str, Any]:
        """Settle the world to horizon and take THE one summary (idempotent for callers)."""
        with self._lock:
            if self._summary is None:
                self.router.finalize_world()
                summary = self.router.summary()
                summary["live"] = {
                    "experiment": "dinner_live_2026_08_17",
                    "cell": self.cell.name,
                    "tier": self.cell.tier,
                    "aggressive": list(self.cell.aggressive),
                    "epoch": self.epoch,
                    "git_sha": self.git_sha,
                    "events": list(self._events),
                    "dm_log": list(self.dm_log),
                }
                self._summary = summary
                (self.out_dir / "summary.json").write_text(
                    json.dumps(summary, ensure_ascii=False, indent=1)
                )
            return self._summary


# ── the MCP layer ──────────────────────────────────────────────────────────────────────────────────────
