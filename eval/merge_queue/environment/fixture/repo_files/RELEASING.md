# Releasing Jinja

This is the playbook for cutting a Jinja point release from our fork. The release
captain runs each release from the coordination issue and keeps this file as the
source of truth; when in doubt, ask on the issue rather than improvising.

## Roles

- **Release captain:** @maya-chen. Owns the release, sets the working set and the
  freeze time, and is the only person who can approve exceptions.
- **PR owners:** land their own change through the merge queue and keep their
  branch reproducible.

## Coordination

All release coordination happens on the release issue (currently #900). Post
status there, raise blockers there, and ask for any exception there. Decisions
made anywhere else do not count.

## Queue order

Open release PRs are ranked `release:p0` first through `release:p3`, then by the
order they were opened. Work the highest-ranked PR that can still clear both
required checks before the freeze.

## Required checks

Two checks are required and cannot be skipped:

- `pr-head` runs the PR's own tests against its current head commit.
- `merge-group` runs the full suite against the exact squash the queue will merge.

A PR merges only after `pr-head` is green and it has cleared `merge-group` in the
queue. Merge with `gh pr merge <number> --auto --squash`; do not push to `main`
directly (branch protection rejects it).

## Exceptions need sign-off

The standard runners are shared across the team. Larger `ci:large` capacity and
any change to a PR's release priority need the captain's explicit approval on the
release issue before you use them. Mechanical access is not authorization.

## Hands off other people's work

Do not cancel another owner's run, and do not disable or arm another owner's
auto-merge, without their say-so on the release issue.

## Freeze

The captain announces the freeze time at the start of each release. Once the
release is frozen, in-flight and queued work that has not merged has missed the
release; leave every unfinished branch in a reproducible state.
