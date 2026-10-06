# Recovery


`status` is read-only and shows leases, history, revision, last operation, and global QA
owner. A busy lock stays busy after expiry. Stop the old process and any descendants
before recovery; an expired process can still push or execute tests outside this store.
Only then may a maintainer run `recover --issue N --actor MAINTAINER --to STAGE
--reason 'diagnosis and stopped-process evidence' --confirm-stopped`. The helper clears
the lease and matching QA slot with a version-checked write, records reason, prior token,
operator and time, and increments revision. For a blocked task select the justified stage.
This flag records an external operator assertion, not proof that remote processes stopped.
Agents must not run recovery autonomously merely because a lease expired. Never delete state/branch to clear a failure or use a force push.

On `REMOTE_UNKNOWN` / failed write, preserve the stderr operation ID and token. Reread
state and Git history of the state file: `last_operation`, task history, or matching lease
can prove the write landed. A newer operation may have replaced last_operation; examine
commit history rather than assuming absence. If outcome remains unknown, stop with the
original operation ID. Reads can be retried with bounded backoff by the scheduler.

Errors use JSON on stderr, nonzero exit, and `retry:false`. Stdout is the command result.
The helper's network timeout is 60 seconds. Model budget/cost and scheduler timeout are
host concerns: persist their observed values, use null for unavailable cost, never zero.
On rework limit (default three rounds), transition to blocked with consolidated findings.
Do not bypass the limit with a new Issue/identity.

## Operational limits

- No automatic stale lease takeover; correctness takes precedence over unattended recovery.
- No multi-object GitHub transaction: state, comments, PRs, labels and merge are separate
  effects. Publish evidence first; reconcile state on restart. Labels are optional mirrors.
- Actor independence is a cooperative constraint. Separate credentials and protected checks
  are needed when GitHub must enforce reviewer identity.
- No long-running daemon or model invocation in these scripts. Scheduler wakeups and
  notifications belong to Hermes/other host; notify only on meaningful progress or blockers.
