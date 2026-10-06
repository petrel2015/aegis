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
python3 "$AEGIS" --repo "$REPO" register --issue 12 --actor planner-01
python3 "$AEGIS" --repo "$REPO" scan --role planner
python3 "$AEGIS" --repo "$REPO" claim --issue 12 --actor planner-01 --role planner
# Save returned token; renew before expiry, default 30 minutes.
python3 "$AEGIS" --repo "$REPO" heartbeat --issue 12 --actor planner-01 --token "$TOKEN"
python3 "$AEGIS" --repo "$REPO" finish --issue 12 --actor planner-01 --token "$TOKEN" --to design-review --evidence evidence.json
```

Evidence file example for a design handoff:

```json
{"summary":"Design and acceptance criteria ready for independent review", "url":"https://github.com/OWNER/REPO/issues/12#issuecomment-123"}
```

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
