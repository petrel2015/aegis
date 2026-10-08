# Coordination and operations

## State

| Current state | Owner role | Success | Rework |
|---|---|---|---|
| new | planner | design-review | blocked |
| design-review | reviewer | ready | new / blocked |
| ready | developer | code-review | blocked |
| code-review | reviewer | testing | ready / blocked |
| testing | qa | merge-ready | ready / blocked |
| merge-ready | qa | done | testing / ready / blocked |

`blocked` is terminal until a maintainer resolves the recorded problem and explicitly
restores the appropriate state. `done` requires the linked PR to be merged. Closing
an Issue is a final separate action; don't use automatic close keywords in PR bodies.
Each `finish` releases the claim. A subsequent role must claim afresh.

The shared JSON in `aegis-state` is authoritative for workflow ownership and transitions.
Every write supplies the previously read GitHub Contents SHA, which rejects stale writes.
The revision changes on every mutation to avoid returning to identical blob contents.
No automatic retries: reread, reevaluate eligibility, and issue a new operation only when
its previous outcome is known. Two contenders cannot both successfully update the same
snapshot. This is a cooperative lock, not a security boundary against repository writers.
A single file is intentionally simple for small teams; high traffic or 750 KB history
needs an explicitly designed migration/archive, not silently dropping audit history.

## Example CLI cycle

Here `AEGIS` is the absolute path to `scripts/aegis.py` and `REPO` is the target OWNER/REPO.

```bash
python3 "$AEGIS" --repo "$REPO" status
python3 "$AEGIS" --repo "$REPO" preflight
python3 "$AEGIS" --repo "$REPO" intake --actor planner-01
python3 "$AEGIS" --repo "$REPO" scan --role planner
python3 "$AEGIS" --repo "$REPO" claim --issue 12 --actor planner-01 --role planner
# Save returned token; renew before expiry, default 30 minutes.
python3 "$AEGIS" --repo "$REPO" heartbeat --issue 12 --actor planner-01 --token "$TOKEN"
python3 "$AEGIS" --repo "$REPO" finish --issue 12 --actor planner-01 --token "$TOKEN" --to design-review --evidence evidence.json
```

Use the selected role's `assets/evidence.json` as the machine-readable evidence contract.
New intake tasks and explicitly revised tasks require `schema: aegis-evidence/v2`,
including the current requirements version/digest, durable HTTPS report URL and summary.
Read [phase-specific evidence](evidence-v2.md) for each role's required AC results.
Unchanged legacy tasks without the v2 intake marker retain the v1 contract; do not
silently reinterpret or upgrade their history. Inspect the actual task snapshot first.
Forward handoffs require exact coverage of the Issue's explicit AC-1, AC-2… IDs.
Designs carry an immutable SHA-256 digest; review and implementation bind that digest.
Code reviews bind the exact PR head. QA includes configured command argv, actual exit code
and durable log URL, plus a two-parent integration commit of exact head and base.
For blocked/rework retain the task's schema and current requirement binding, summary, URL
and `result: blocked` or `fail`; include PR/head
if a PR already exists. Report semantic evidence honestly: structure is not factual proof.

Development, code-review and QA handoffs add `pr` (integer), `head` (full SHA).
QA success additionally needs `result: "pass"`, `base` and `tested_commit` (full SHAs).
The helper verifies the live PR candidate and preceding handoff when advancing to testing
or merge-ready. It validates structure/live identity, not the truth of natural-language
review or test results. The agent must inspect real evidence. `release` drops an owned
claim without transitioning; don't release while child processes still work.

Planner discovers Issues using `gh api --paginate repos/OWNER/REPO/issues?state=open`;
filter out PRs and require trusted intake. Register once after checking `status`; a scan
only lists registered tasks. Read all pages. Sort eligible work by P0→P3 then oldest.
For labels/comments/PR writes, reconcile ambiguous results using operation markers and
live objects; never blindly recreate a PR or repost after timeout.

## Failures and recovery

For expired claims, blocked work, ambiguous writes or operator recovery, read
[recovery](recovery.md). Do not automatically retry mutations or steal leases.

## Automatic Issue visibility

Successful `register`, `finish`, and `recover` persist a durable event with the workflow
change, then synchronize the Issue's `aegis:STATE` label and append a state-change comment.
Comments contain operation ID, actor, reason/result and evidence URL. Claim/heartbeat/release
do not create status comments. The CLI creates missing state label definitions as needed.
Other labels, including `aegis:intake`, are preserved.

A successful state write may return `sync.status: pending` if projection failed. The task
is already transitioned; do not run finish again. Use `sync --issue N` to reconcile.
Read [visibility and recovery details](issue-visibility.md) for concurrency, retries and
ambiguous comment delivery. Status labels do not authorize claims or change the state file.

## Executable gates and host invocation

Read [policy and runner](policy-and-runner.md) for trusted intake, strict evidence,
bounded host execution and optional merge-queue admission. `scan` remains a read-only
view; eligibility is rechecked at claim. Existing tasks without an intake snapshot
fail closed and need a deliberate maintainer migration; intake does not reset history.
