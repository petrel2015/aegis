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

## Field-trial repairs — 2026-10-08

101 local tests pass (`python3 -m unittest discover -s tests -v`). New coverage includes
read-only continuation, CAS-bound revision, retained requirements/history/contributors,
busy/completed/queued/stale revision rejection, exact requirement-epoch evidence, stage-specific
AC results, successful predecessor decisions, approved same-candidate QA retesting, configured
verification groups, unique QA run IDs, environment metadata, evidence tamper/symlink detection,
release-without-Issue records, pending/failed receipts with genuinely unknown artifacts,
public-version mismatch rejection, queue rejection after requirement changes, and preventing
host invocation when continuation diagnostics need reconciliation. The full fake-gh lifecycle
now exercises v2; unchanged legacy v1 evidence remains explicitly supported.

An independent offline forward test used the clarified map-polygon requirement through
resume → revise → design → review → development → review → QA, plus a pending Pages receipt.
It found a legitimate QA retest incorrectly rejected and a rejected review reusable after
recovery. Both were repaired and independently retested. It also found missing release
workflow linkage instructions, no-Issue external release friction, and failure receipts that
required nonexistent artifact hashes; these were repaired with dedicated regressions.

All seven Skill entrypoints pass skill-creator quick_validate.py using the existing Hermes
venv Python (system Python has no PyYAML; no dependency was added). Local Markdown links,
JSON resources, CLI help, fictional pending-release validation and git diff whitespace checks
pass. Receipt validation is structural; manifest verification establishes local integrity,
not trusted semantic truth or independent observation of a public deployment.

No live GitHub Issue, PR, state branch, merge queue or deployment was mutated for this repair.
ChronoAtlas's earlier successful public deployment is product evidence, not a complete remote
AEGIS workflow trial. The live acceptance list above remains open and requires an explicitly
designated sandbox destination. These changes are verified in the local working tree; no
remote publication of this AEGIS update is claimed here.

## Real ChronoAtlas monthly-playback task — 2026-10-08

At the user's explicit request to use AEGIS for a new ChronoAtlas requirement, the local
repaired framework was used against the authorized private target petrel2015/ChronoAtlas.
The previously absent aegis-state branch was initialized; this was real task coordination,
not an arbitrary live race/fault-injection test. Local framework file hashes are retained
under .aegis-local/chrono-monthly/framework-snapshot.json; no published framework version is claimed.

- Requirements: https://github.com/petrel2015/ChronoAtlas/issues/1
- Independent design approval: issue comment 6051317684.
- Candidate: https://github.com/petrel2015/ChronoAtlas/pull/2,
  head 64c8ed43a381f77e342b20c18db401630695d23a.
- Independent code approval: PR comment 6051482516. A CI-only virtual-clock race was
  identified, repaired in a new head, and the failed evidence retained.
- QA report: PR comment 6051543979. Actual integration commit
  47431072d8f9acf22d44c4862108e21bce165c93 has parents head above and base
  6f6f41d60a2afd8fbbe35b5c88b88f0888787ebf.
- 23 unit/API tests, normal/Pages builds, long monthly progression, minor-event fixture,
  real timers, phone panels, actual polygon colors, and 5,955 date-boundary checks passed.
  QA used its own checkout and an evidence-only orphan branch; artifact commit
  0b3afea2e030ae3061ea313d152d89298d2d2552 preserves independent logs/screenshots.
- Both final candidate CI runs passed: 37721718383 and 37721722405.
- Actual AEGIS finish to merge-ready: c3705402a1bd4d3c9906ec5dea2d4da9, Issue label synced.
  Manual-stage revalidation/report and release completed; no lease or QA slot remains.
  Manual-wait report: PR comment 6051569487. No merge or production deployment was performed.

This verifies one live requirement→design→independent review→development→independent review→
serialized QA→manual-ready path. It does not verify multi-machine claim races, live crash
recovery, merge-queue server gates, arbitrary-host native activation or public deployment.
Earlier local-only statements remain historical; this is the newer, bounded remote proof.

A further operational issue was observed: inherited product workflows also ran on aegis-state
pushes (for example run 37721046528). Those runs are not PR candidate evidence and waste CI
capacity. Future initialization/migration should prevent inherited workflow execution on
coordination branches through a reviewed mechanism; this trial did not hand-edit state history.


## ChronoAtlas PR #2 merge and public release — 2026-10-08

This later record advances the previously recorded manual-ready stage; its earlier
no-merge/no-deployment statement remains a historical observation. After the user
explicitly requested GitHub Pages deployment, PR #2 was manually merged at
2026-10-08T04:56:02Z to source commit
`6554631600015b92c80e06261db44374365e46d1`. The retained merge observation is
[PR comment 6052606744](https://github.com/petrel2015/ChronoAtlas/pull/2#issuecomment-6052606744).
The approved head and preceding independent QA evidence remain attached to PR #2;
the merger did not claim a fresh independent review or a server-side merge-queue gate.

[Release acceptance](https://github.com/petrel2015/ChronoAtlas/pull/2#issuecomment-6052645744)
records the separate authorized public destination
[ChronoAtlas Pages](https://petrel2015.github.io/ChronoAtlas-pages/), artifact commit
`ed23d7cd3b04a2109126842626ad17bcda74f996`, and
[successful deployment run 37730028153](https://github.com/petrel2015/ChronoAtlas-pages/actions/runs/37730028153).
The sealed release receipt and browser evidence are retained at
[source evidence commit 0e0521d1](https://github.com/petrel2015/ChronoAtlas/tree/0e0521d1b17ea3975dd8817e80e4b64a9fcd3b57/c499e5c005954df9b6de673c51c73b14).
The receipt records matching observed source SHA and artifact digest, live-file comparison,
and public desktop/mobile playback smoke. This section is reconciled from those saved
observations and receipts; it does not claim a new online probe at documentation-update time.

The first artifact update omitted existing `ATTRIBUTION.md`; the final artifact corrected
it and retained the earlier attempt. The original sandbox API-test `EPERM` was also
retained before a separately authorized local-listener retry passed all 23 tests.
These findings motivate explicit release-file preservation and read-only environment
diagnostics. One public release is proof of this destination and candidate, not all
hosts, all deployment providers or live crash/race recovery.

## Publication and coordination isolation repairs — 2026-10-08

133 local tests pass after independent forward testing, including actual temporary Git publication and delayed concurrent invocations. No live Git/push occurred in those tests. Seven Skill entrypoints pass quick validation. Guarded static preparation preserves attribution/domain/license files, binds the exact previous inventory, and requires reviewed deletion paths. Checkout-local exclusion and post-lock revalidation prevent stale cooperating local publishers. Public verification rejects overlap and compares every file against the retained ZIP; project browser observations and provider status remain separate.

Environment checks classify dependency failures and localhost restrictions without automatically rerunning tests. Generic handoff docs now distinguish new v2 evidence from unchanged legacy v1.

The user authorized ChronoAtlas Issue #3 as a live field trial. Before intake, isolate-state-ci removed only inherited .github/workflows/pages.yml and test.yml at commit 23202a28bd6f20f645ba26ed6e96a0b4f4aa03b9; state blob 0d4df79ec16c317f9d759432b32486dfd401ea52 and revision29 remained unchanged. This is actual migration proof, not multi-machine crash/concurrency proof. State-only orphan initialization remains tested offline against a Git API fake; no new live repository was created to test initialization.

A read-only live verification of the existing ChronoAtlas Pages deployment used the new artifact helper. Two urllib downloads ended with IncompleteRead and retained remote_unknown observations. Explicit optional curl transport (existing host CLI, no automatic retry) subsequently verified all 10 public files and source6554631600015b92c80e06261db44374365e46d1 against the retained ZIP. No redeployment was performed for this check. Two transport/error regressions were added; full suite now has135 tests. This proves file verification for that deployed artifact, not acceptance or deployment of Issue#3.
