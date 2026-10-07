# Validation record

Date: 2026-10-06. Initial local implementation; no live repository mutated.

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 skills/aegis/scripts/aegis.py --help
```

The suite uses Python stdlib only. The Skill's frontmatter/scaffold validator also passed
using skill-creator's `quick_validate.py` (its own PyYAML dependency ran in an isolated uv
execution environment; the delivered helpers do not require it).

27 tests cover lifecycle/role transitions, competing claims, a simulated stale SHA write,
lease ownership/expiry, renewal, global QA serialization, immutable failed operations,
independent review across multiple authors and released claims, pre-PR blocking,
head/base mismatch, queue admission versus merge, closed-Issue reconciliation,
operator recovery and old-token rejection, no retry on timeout, URL parsing, and
non-overwriting/symlink-safe bootstrap.

An independent agent's forward test exposed pre-PR blocking, multi-author review exclusion,
and closed-Issue finalization gaps. These were repaired with regression tests, including recovery of an expired QA claim on an already closed Issue. Its full
subprocess fixture is retained in `tests/fixtures`: 21 CLI invocations exercise design,
development, review, a new head requiring rework/re-review, base drift requiring retest,
and a merged/closed Issue finalized as done. This fixture uses a fake `gh`; it never
contacts GitHub and must not be described as remote validation.

## Remaining live acceptance

On an explicitly selected sandbox repository:

1. Bootstrap policy, publish templates, initialize state branch.
2. Race two independent machines claiming the same Issue; verify exactly one wins.
3. Exercise crash, ambiguous write, operator recovery, and retained audit history.
4. Run all roles on a small actual change; retain PR, review, CI and state commit links.
5. Verify branch queue/rules, `merge_group` checks, separate-account approvals where
   required, and no bypass. Change base/head while tests run and verify fresh gates.
6. Test the chosen host's skill loading and scheduler with empty work returning idle.

These checks remain unperformed. No GitHub publication, scheduled worker, production
merge, or release/deployment is claimed. Semantic quality of tests and review, execution
budgets and trusted intake are agent/policy responsibilities; the helper validates the
mechanical state and candidate bindings, not the truth of a supplied evidence narrative.

## Role Skill restructuring

All six SKILL.md entrypoints (router, initializer, planner, developer, reviewer, QA) pass
quick_validate.py. Local Markdown links resolve after the split, and all 27 existing
helper tests still pass. CLI code was unchanged. Each role directly links shared rules
and its own playbook; initialization and recovery are conditional resources. Native
Codex/ZCode/Claude/Hermes loading and actual context/token savings remain unmeasured.

## Role deliverable contracts

Added per-role input/step/output runbooks, report templates and fictional filled examples;
execution roles also have CLI evidence templates. Reviewer includes separate design and
code examples. Developer/reviewer/QA include fixed Issue handoff comments; developer also
has a default product-document section format when the project has no existing convention.

All five filled report examples retain their template headings; local Markdown links resolve.
All six Skills pass quick_validate.py. Five evidence examples (planner, developer, design
review, code review, QA) were applied to the existing state engine at their documented
transitions successfully. The 27 helper tests remain passing; helper code was unchanged.

Independent read-only role simulation checked coder rework and pre-PR blocking, then review
and QA contracts. It found that copying the QA pass JSON for environment blocking could
retain result=pass. The QA runbook now specifies exact field sets for pass, failure, blocked,
base/head drift, queued/manual wait and merged outcomes. Formats remain agent requirements;
Markdown semantics and factual truth are not enforced by the state helper. No live task
was executed and no example URL or test result is real execution evidence.

## AEGIS rename

All 27 tests pass under the renamed `skills/aegis/scripts/aegis.py`; all six renamed
Skills pass format validation and local documentation links resolve. Active source,
examples and configuration use AEGIS naming. Earlier decision records preserve historical
names with a link to decision 0003. No remote state or repository was renamed.

## Automatic Issue projection — 2026-10-07

41 offline tests pass. The process-boundary fake GitHub lifecycle now asserts that each
successful transition returns synced, the final managed label is aegis:done, business/intake
labels remain, and each durable event has exactly one corresponding comment.

Fault-injection tests cover blocked reason/evidence, repeated reconciliation, permissions,
timeout before/after comment creation, CAS conflicts, concurrent send reservation,
paginated comments, legacy snapshots, manual label drift, recovery, stage changes during
label updates, silent heartbeat/release, and no projection after a failed state write.
Local Markdown links and git diff whitespace checks pass. No real GitHub Issue was modified.
Label projection is eventually consistent; ambiguous comment attempts remain pending for
reconciliation rather than automatic retransmission. See the Issue visibility reference.

API references checked for this implementation:
[labels](https://docs.github.com/en/rest/issues/labels) and
[Issue comments](https://docs.github.com/en/rest/issues/comments).

## Executable policy and host runner — 2026-10-07

79 offline tests pass. New coverage includes policy validation, trusted issue intake,
AC contracts, dependency/rework gates, design digests, current-head checks, QA command
records, and fail-closed queue admission. `agent-attestation` is cooperative role evidence;
it does not prove independent GitHub accounts or factual correctness.

The Hermes worker produced the initial runner in a bounded requested run. Its process
exceeded the requested 900-second budget and was explicitly stopped; its output/log was
preserved locally, not silently replaced by a new run. Independent acceptance repaired
CLI intake arguments, lost-lease behavior, descendant cleanup and completion reporting.
A second independent forward-test reproduced SIGTERM leaving a host alive, coordinator
timeout leaving a child alive and losing attempt IDs, and stale-round completion. Fixes
were independently retested using actual isolated processes. `test_runner_process.py`
asserts SIGTERM/SIGINT cleanup, preserved unknown-attempt IDs and exact current claim token.
No provider usage/cost was available; unknown is not recorded as zero.

All six Skills pass the bundled quick validator using the existing Hermes Python environment
(the system Python lacks PyYAML; no runtime dependency was added to AEGIS). `git diff --check`
passes. Added strict evidence/runbook guidance supersedes earlier minimal-field examples.

ChronoAtlas was used as a real local role-workflow application: independent design rejection
and revision, independent code review identifying two real HTTP/UTF-8 defects, repair,
14 unit/API tests, production build, desktop/390px browser smoke and real terrain tiles.
Target documentation preserves the exact approved design digest and local proof boundary.
Creating/pushing its GitHub repository was rejected by automatic approval review pending
explicit target authorization. No remote Issue/PR/CI/lease or merge is claimed by this trial.
Live queue plan/account permissions and real AI provider calls remain unverified.
