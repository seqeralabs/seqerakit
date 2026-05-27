# Wait for compute environment deletion before recreating (`on_exists: overwrite`)

Tracking: FD-7252 / COMP-1531 / COMP-1532

## Problem

A customer using `on_exists: overwrite` for Forge compute environments started
hitting the AWS Batch limit of 50 managed compute environments. Their CEs were
being orphaned in AWS instead of cleaned up.

Two separate bugs were involved. The Platform-side bug (silent disposal failures
leaving orphaned AWS resources) is fixed separately in platform PR #10683. This
change addresses the seqerakit-side bug.

Since December 2025, Platform deletes Forge CEs asynchronously. A delete marks
the CE as `DELETING` and tears down the backing cloud resources in the
background. For AWS Batch Forge this takes roughly 2-3 minutes. While the CE is
`DELETING`, its name stays reserved.

seqerakit's `on_exists: overwrite` deletes the existing CE and immediately
creates the replacement. Because the old CE is still `DELETING`, Platform
rejects the create with an "already exists" error, and the overwrite fails.

## Approaches considered

### A. Append `--wait` to the delete call

`tw compute-envs delete --wait` blocks until the CE reaches a terminal state.

Rejected on compatibility grounds. The `--wait` flag on `compute-envs delete`
was introduced in tower-cli **0.30.0**. seqerakit runs whatever `tw` is on the
PATH and documents support for tower-cli **>= 0.11.0**. Appending `--wait`
unconditionally turns the overwrite into a hard failure for every user on a tw
older than 0.30.0:

```
$ tw compute-envs delete --name <ce> -w <ws> --wait
Unknown option: '--wait'
```

That converts a race condition into a guaranteed break across the documented
supported range, which is worse than the bug being fixed.

### B. Poll the workspace listing until the CE disappears (chosen)

After issuing a plain `tw compute-envs delete`, poll `tw compute-envs list`
until the CE name no longer appears, then proceed to recreate.

This relies only on `compute-envs list`, which has existed since long before the
supported floor, so it works on any tw version.

## Why polling the listing is a correct signal

The condition that gates a safe recreate is "the name is free to reuse." The
listing was verified empirically against a live AWS Batch Forge CE in
`scidev/testing`:

| time after delete | in `compute-envs list` | name reserved (recreate probe) |
| --- | --- | --- |
| 1s – 184s (~3 min) | yes, status `DELETING` | yes, recreate rejected |
| 194s | no, absent | no, recreate succeeded |

Listing-absence and name-freedom coincide. The CE stays listed as `DELETING` for
the full disposal and leaves the listing in the same moment its name frees up,
so polling the listing waits exactly as long as the recreate needs and no
longer. An aws-cloud CE shows the same relationship on a much shorter timescale
(name freed ~7s).

The observed disposal time of ~194s also sets the timeout. A 180s timeout would
have failed a healthy deletion; the timeout is set to **300s** to leave headroom.

## Implementation

`seqerakit/overwrite.py`:

- `delete_resource` issues a plain delete (no `--wait`), then calls
  `_wait_for_ce_deletion` for the `compute-envs` block only. Other resource
  types are unaffected.
- `_wait_for_ce_deletion(sp_args, poll_interval=5, timeout=300)` polls
  `compute-envs list -w <workspace>` every 5s, using a `time.monotonic()`
  deadline, and returns as soon as the CE name is absent from the listing. It
  invalidates the cached listing for that workspace on each poll so it sees
  fresh data. If the deadline passes with the CE still listed, it raises
  `TimeoutError`.

### Behaviour when disposal fails (ERRORED)

With platform PR #10683, a failed disposal leaves the CE in `ERRORED` rather
than soft-deleting it. An `ERRORED` CE stays in the listing, so this poll runs
to the timeout and raises `TimeoutError` instead of recreating on top of a
half-disposed environment. The error message names both terminal states
(`DELETING` not finished, or `ERRORED`) so the cause is not misread as a
timeout-only condition.

## Testing

`tests/unit/test_overwrite.py`:

- `delete_resource` issues a plain delete and calls `_wait_for_ce_deletion` for
  `compute-envs`, and does not wait for other resource types.
- `_wait_for_ce_deletion` returns when the CE is absent on the first poll,
  returns after several polls once the CE disappears, and raises `TimeoutError`
  (naming both `DELETING` and `ERRORED`) when the CE never disappears.

`time` is patched in the polling tests so they run without real delays.

## Relationship to PR #267

PR #267 implemented approach A (`--wait`) and is already merged to `main` but not
yet released. This change replaces that implementation with approach B. The
`--wait` append and its tests are removed. No tagged release contains the
`--wait` behaviour, so there is no released regression to roll back.

## Rollout

- No tw version bump is required for users; the floor stays at `>= 0.11.0`.
- The customer can drop the `delete` / `sleep 150` / `create` workaround once a
  release containing this change is available.
