# pi 0.77.0 system prompts for four seats

The system prompts pi 0.77.0 built for four seats, launched with the seat's exact argv (`--no-context-files`,
`*_off.txt`) and with that one flag removed (`*_on.txt`), captured by an extension that writes
`ctx.getSystemPrompt()` at `session_start`. No prompt was sent and no model was called.

Three substitutions make the text read as it does inside the Modal container: pi's documentation paths point
at the image's global npm root (`/usr/local/lib/node_modules/@earendil-works/pi-coding-agent`), the
`Current working directory` line (and the `<project_instructions path=...>` attribute) is the seat's
container cwd `/home/<username>/dinner` or `/home/<username>/trip`, and `Current date` is the capture date.

| file prefix | formation | scenario | seat |
|---|---|---|---|
| `food_team` | team | reg_food_silent_side_deadline | d2 |
| `food_coordinator` | coordinator | reg_food_silent_side_deadline | S |
| `food_team_silent` | team_silent | reg_food_silent_side_deadline | d2 |
| `trip_team` | team | group__double_share_snapback | t1 |

`tests/test_isolation.py` checks that each `*_on.txt` equals its `*_off.txt` plus exactly one
`<project_context>` block whose body is the AGENTS.md this eval stages for that seat, and that the root-host
seat launch gives pi the same cwd and AGENTS.md path.
