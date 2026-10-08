# Continue work without losing the workflow

Use this procedure when a user continues, corrects or reopens a requirement. Source checkout,
workflow Skill checkout and deployment artifact checkout can be different repositories.

1. Resolve the authorized target from user context and verified Git origin. Read current
   policy and `status`. Do not infer an Issue solely from a similar title; list plausible
   tasks if the user context does not identify one. Missing state needs setup, not a bypass.
2. Run `aegis.py --repo OWNER/REPO resume --issue N --actor ID --role ROLE --workspace PATH`.
   This reads the live Issue, requirement snapshot, lease, candidate and local checkout.
   It never claims, resets, merges or marks acceptance passed. `workflow_verified: false`
   explicitly prevents treating a clean diagnostic as an end-to-end audit certificate.
3. `ready_to_claim` means claim normally; `resume_owned` means reuse and renew the existing
   claim. It does not authorize a second concurrent process under that identity. Expired,
   busy, blocked, closed, changed or untracked work needs reconciliation first. Local edits
   may be legitimate in-progress work: inspect them rather than deleting or auto-committing.
4. If implementation happened outside the recorded workflow, preserve its commits and files,
   record `execution_mode: external`, and send the actual candidate through fresh review/QA.
   Do not backdate a claim or label it an AEGIS pass. Human Git permissions can still bypass
   the helper; server protections and cooperative host adoption remain necessary.

## Requirement revision

A direct user clarification authorizes incorporating that change. Do not ask again merely
because the revision command is operator-controlled. It does not authorize silently changing
unrelated criteria, cancelling a queued merge or stopping another agent's live process.

Publish a revision decision using the format below and update the Issue with the clarified
requirements within existing authorization. Stop the old worker; release its claim, or use
explicit recovery only after confirmed termination. Then run:

```text
python3 skills/aegis/scripts/aegis.py --repo OWNER/REPO revise \
  --issue N --actor ID --expected-revision STATE_REVISION --confirm-stopped \
  --reason "User clarified the visible behavior" --affected-ac AC-1 \
  --evidence-url https://github.com/OWNER/REPO/issues/N#issuecomment-REAL_ID
```

The command uses live Issue intake and the state blob's CAS guard. It requires no active
lease/QA ownership/queue request, retains old requirements and evidence, increments the
requirement version, and returns to `new` for a fresh design and independent review. All
prior design/review/QA evidence is conservatively invalidated for forward progress; the
reported affected IDs explain impact but never permit reusing old approvals. Contributor
identities and rework counts are retained. Old claim tokens stay invalid. Concurrent state
writes fail; ambiguous writes are reconciled by operation ID, never blindly retried.

Completed work stays `done`: create a linked follow-up Issue. A recorded queue request must
be resolved before a follow-up; `revise` cannot cancel or pretend to retract an external merge.
For a legacy v1 task, a genuine revision upgrades it to v2. Do not perform no-op migrations
or overwrite old evidence; unchanged v1 tasks can finish under their existing contract.

## Revision decision format

```text
record_id: <new UUID>
issue: <actual Issue URL>
source_request: <user clarification reference>
previous_requirements_version: <integer>
reason: <what was misunderstood or changed>
affected_acceptance: <AC IDs, including added or removed IDs>
before: <old observable behavior>
after: <new observable behavior>
invalidated: <design, reviews and QA candidate references>
retained: <prior records and implementation commits>
next_role: planner
```

Example (fictional): AC-1 formerly described “faction colors”; clarification requires
administrative polygons to change fill. Event rings and legend changes are counterexamples,
so earlier marker screenshots cannot establish acceptance. The new design must explain
polygon sourcing, temporal coverage and a browser comparison of actual map fills.
