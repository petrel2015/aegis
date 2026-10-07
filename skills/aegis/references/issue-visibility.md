# Issue visibility and reconciliation

Authoritative stage lives in `aegis-state:aegis-state.json`. GitHub Issue open/closed state
is separate. A blocked task remains open; the synchronizer never opens/closes Issues.

The managed label set is exactly:
`aegis:new`, `aegis:design-review`, `aegis:ready`, `aegis:code-review`, `aegis:testing`,
`aegis:merge-ready`, `aegis:blocked`, `aegis:done`.
Only these labels are removed/replaced. Other labels, including `aegis:intake`, stay intact.
Filter Issues by `label:aegis:blocked` to find tasks needing attention. Manual label edits
never transition a task; the next synchronization restores the authoritative stage.

## What happens after a transition

`register`, `finish` and `recover` commit workflow state and an `issue_events` record in the
same version-checked write. Only afterward does the CLI synchronize labels and comments.
The comment identifies the historical from/to stages, operation, actor, time, summary/reason
and durable evidence URL. Blocked comments direct maintainers to resolve and recover the task.
Agent-authored full reports remain required: the automatic comment links them, not replaces them.
Do not post a second manual status-only comment for the same transition.

Claiming, renewal and release do not generate comments. Label writes use individual add/remove
operations rather than replacing the whole label list, preserving concurrent unrelated labels.
Labels are a repairable view, not an atomic transaction with state. Concurrent stage changes
can temporarily produce stale/multiple state labels; state is rechecked during sync and a
later bounded reconciliation converges. The CLI does not promise linearizable display.

## Repair command

```bash
python3 "$AEGIS" --repo OWNER/REPO sync --issue 42
```

Here AEGIS is the absolute path to scripts/aegis.py. This command reads the current state,
repairs its labels and processes at most 20 outstanding events. Run for another bounded
batch if `pending_events` remains. For existing installations without events, sync creates
one current-state snapshot including the latest recorded reason; it does not fabricate old
transition comments. Upgrading alone does not sweep every historical Issue: sync each
registered Issue when a backfill is desired.

`status: ok` from a business command means the state commit succeeded. Inspect `sync.status`:
`synced` means that pass completed; `pending` includes the error/resume command. Preserve the
original business operation ID; never replay register/finish/recover to fix presentation.
Permission/rate-limit/network failures are visible in the returned result and leave durable
pending work. The host should notify the operator of actionable pending sync and schedule a
bounded sync retry, not rerun the model's development work. No scheduler is installed here.

## Comment deduplication and uncertain results

Before a comment POST, a CAS write changes its event from `pending` to `sending`. Only one
worker can reserve a given event. Every comment includes a deterministic event marker;
reconciliation scans all comment pages and matches the complete expected body. A found
comment is acknowledged without another POST, including after a timeout or failed ack.
A marker inside a different comment body is not accepted as proof of delivery.

If `sending` has no matching comment, the original call may still be running or its response
may be lost. The CLI does not repost automatically. Later events wait behind that unresolved
event, while labels can still be repaired. Keep the event ID and original process/network
logs. After confirming the original process and request cannot still complete, an authorized
maintainer can reconcile against actual GitHub evidence: record the existing comment as sent,
or (only with positive evidence of non-delivery) reset the event to pending using a current-SHA
Contents update, preserving an audit reason and incrementing revision. Listing absence alone
is not positive evidence. Never delete the event or reset workflow state to clear a sync error.

Sent comments are historical records, not continually recreated if someone later deletes or
edits them. Cooperating repository writers are assumed; the marker is not an authentication
mechanism. Helpers do not include claim tokens or credentials in comments.

## Example: blocked → recovered

A planner reports missing dependency access in evidence.summary and links the Issue report
in evidence.url, then finishes to blocked. The Issue receives `aegis:blocked` and a comment:

```text
AEGIS: new → blocked
Operation: <persisted operation ID>
Actor: planner-01
Reason / result: Missing dependency access; maintainer must grant permission.
Evidence: <actual report URL>
Maintainer action required: resolve the blocker and use audited recovery.
```

After access is restored and prior work is confirmed stopped, audited recovery to new
replaces aegis:blocked with aegis:new and appends the recovery reason. The older blocked
comment remains visible as history. Merely removing aegis:blocked does not resume work.
