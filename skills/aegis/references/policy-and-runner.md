# Policy gates and bounded host execution

`preflight` reads `.github/aegis.json` from the remote default branch. Empty test commands
or required checks are unconfigured errors. The CLI does not execute commands found in
Issue text. Keep test argv in reviewed policy and inspect project code before execution.

`intake --actor ID` paginates open Issues, excludes PRs, accepts a trusted author or intake
label, validates the issue-form sections and unique AC-N identifiers, then registers up to
`max_issues_per_run`, ordered by priority and Issue number. Dependencies use `#N` in the
optional Dependencies field and must all be done before claiming. Closed/malformed/untrusted
Issues are reported, not silently promoted. Claim and forward finish detect edited Issue bodies.
A blocker can still be recorded after an edit. Changed requirements use the explicit [revision procedure](continuation.md); completed tasks need follow-up Issues.

`claim` enforces dependency and rework limits. Exhausted rounds require maintainer attention;
changing actor identity does not reset the budget. Labels alone are never ownership.

New tasks use `aegis-evidence/v2`; existing v1 tasks retain their declared legacy contract. See [phase meanings and migration](evidence-v2.md). Forward evidence includes exact AC coverage
with HTTPS report links. Design review and development bind the SHA-256 of the approved
design file. Review binds PR head. QA includes every configured command, exit code and log,
plus a real remote integration commit whose parents include the reviewed head and current
base. Required GitHub Actions checks must succeed on that head; older successful reruns cannot
mask a newer failed run. Passing data validates structure, not the truth of an agent report.

`review_mode: agent-attestation` is cooperative independent-role review, allowing one GitHub
account to host distinct actors. It cannot prove different humans or prevent a repository
writer forging evidence. `github-review` additionally requires current-head GitHub approval
by an account other than PR author and no outstanding changes requested.

## One-shot runner

Use `scripts/run_once.py --help` for host invocation. Supply a JSON argv file under operator
control (never from Issue content), for example:

```json
["hermes", "chat", "--in", "{workspace}", "--query-file", "{prompt_file}", "--oneshot"]
```

The same adapter can invoke Codex, ZCode or Claude through their locally verified CLI syntax;
AEGIS does not assume identical flags. Placeholders are substituted as argv, without a shell.
The runner preflights, optionally intakes for planner, scans, runs read-only `resume`, and claims at most one Issue,
then invokes only that role. A local lock prevents duplicate host execution. It maintains
heartbeats, enforces `max_run_minutes`, terminates the worker process group on loss of ownership
or timeout, and saves request/prompt/log/result under `.aegis-local/runs`. Unavailable token
or cost usage remains null. A successful process exit is not a workflow handoff.

Schedule this one-shot command with the chosen host's scheduler. Installing a scheduler,
provider credentials and deployment are separate operator configuration. No always-on daemon
or model-specific dependencies are added to AEGIS. Inspect an uncertain operation before
retrying; the runner must not reset stale leases or automatically invent a blocked handoff.

## Optional queue admission

`queue-merge --issue N --actor ID --token TOKEN` is disabled in manual mode. It requires
owned QA merge-ready state, unchanged head/base, QA/check gates, and active GitHub rules for
merge queue, required checks and independent pull-request approval. Intent is saved before
calling `gh pr merge --auto --match-head-commit`. No admin bypass. Timeout/nonzero status is
remote_unknown; inspect the original PR rather than resubmitting. Queue admission leaves
merge-ready unchanged. Only observed merged PR permits `finish --to done`.

Offline tests do not prove a particular account/plan supports merge queues. Unsupported
server rules fail closed; keep manual mode until the destination is configured and verified.

Optional `verification_groups` maps names to nonempty arrays of argv commands. All configured groups are required by QA in addition to `test_commands`; none are silently skipped. The helper validates command evidence; it does not execute commands found in Issue text. Browser runtime, viewport, build mode and target URL belong in the evidence environment.

`resume` diagnostics prevent the runner from claiming/spawning a host until reconciled. The role then checks the actual workspace before edits. Optional `verification_environment` lists additional QA metadata fields required by policy (for example browser_version and viewport). A viewport, when supplied, must have positive integer width/height.
