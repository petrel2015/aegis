# Source-bound GitHub Pages release

Use the core `skills/aegis/scripts/release_workflow.py` CLI. Each command is bounded;
none schedules jobs or automatically retries external effects. Paths below are fictional
absolute examples. Supply actual trusted project argv/configuration and existing user
authorization. Do not copy build commands or expected workflow identity from an Issue.

## Records and fresh execution

Create a trusted plan JSON with these fields before publication:

```json
{
  "source_repo": "OWNER/SOURCE", "artifact_repo": "OWNER/SITE",
  "source": "/ABS/SOURCE", "build_output": "/ABS/FRESH_DIST",
  "build_record": "/ABS/BUILD_RUN/operation.json", "artifact": "/ABS/ARTIFACT_RUN",
  "publication_record": "/ABS/ARTIFACT_RUN/publish.json",
  "verification_record": "/ABS/VERIFY_RUN/verification.json",
  "smoke_record": "/ABS/OBSERVATIONS/SMOKE.json",
  "deployment_record": "/ABS/OBSERVATIONS/DEPLOYMENT.json",
  "site_url": "https://OWNER.github.io/SITE/",
  "workflow_path": "dynamic/pages/pages-build-deployment",
  "deployment_environment": "github-pages",
  "execution_mode": "aegis", "issue": 42, "source_pr": 57,
  "authorization_ref": "Actual user authorization for this exact destination",
  "rollback": "Previous verified artifact commit and established rollback procedure"
}
```

`workflow_path` is a trusted configured expectation, not a name guessed from a green job.
The legacy Pages provider uses `dynamic/pages/pages-build-deployment`; custom Actions
must pin their actual deployment workflow path. `execution_mode: external` omits the
Issue/PR lifecycle claim; it still requires source, deployment, files and browser bindings.
The plan is explicit local operator policy, not signed attestation. Keep source, build,
artifact, observation records and each release/finalization run in separate directories.
Start/finalize reject overlapping record directories, including resolved symlink aliases,
before creating files; deployment observations cannot be written into source/build/artifact.

```text
python3 skills/aegis/scripts/release_workflow.py start --plan /ABS/PLAN.json --output /ABS/RELEASE_RUN
python3 skills/aegis/scripts/release_workflow.py build --source /ABS/SOURCE --build-output /ABS/FRESH_DIST --output /ABS/BUILD_RUN --repo OWNER/SOURCE --argv-json /ABS/BUILD_ARGV.json --mode pages --timeout 600
python3 skills/aegis/scripts/release_workflow.py prepare --build-record /ABS/BUILD_RUN/operation.json --previous /ABS/PREVIOUS_ARTIFACT_CHECKOUT --output /ABS/ARTIFACT_RUN --site https://OWNER.github.io/SITE/
```

The source must be a clean Git root with matching GitHub origin. The output directory
must not exist. The trusted argv runs from the source root with `AEGIS_BUILD_OUTPUT` set;
configure the project build to actually write there (for example a project-owned Python
build command can read that environment variable; a Vite argv can explicitly supply the
same output directory). The record directory must be outside source and build output.
An ignored, initially absent output directory within source is allowed. Before/after
HEAD, tree and cleanliness plus output hashes bind the build. Failed/timeout logs and
elapsed time survive; a retry requires a new run/output. Ignored dependencies, installed
compiler versions and environment inputs are not hermetically attested.

Review the artifact diff and supply each actual `--allow-remove PATH`/`--protect PATTERN`
when needed. Use existing [static publication](static-git.md) `publish` exactly once.
The publication record preserves its original commit/ref and authorization before push.
After inspecting the original deployment operation, record its actual IDs:

```text
python3 skills/aegis/scripts/release_workflow.py observe-deployment --manifest /ABS/RELEASE_RUN/operation.json --run-id ACTUAL_RUN_ID --deployment-id ACTUAL_DEPLOYMENT_ID
python3 skills/aegis/scripts/release_pipeline.py verify --artifact /ABS/ARTIFACT_RUN --output /ABS/VERIFY_RUN
```

Observation requires exact repository, artifact commit, configured workflow, completed
successful Actions run, explicit deployment environment and latest successful status at
the exact site. Its log URL must correlate to that same Actions run. A test workflow,
older success followed by failure or different environment/run cannot substitute.
A failed observation is retained; inspect it, then start a linked new plan with a fresh
observation path for an explicitly chosen retry. Do not overwrite the original record.

## Structured browser observation

The project browser runner (or an identified human observer) writes this versioned format:

```json
{
  "schema": "aegis-smoke-observations/v1",
  "run_id": "actual-unique-run", "recorded_at": "actual UTC timestamp",
  "provenance": "project-runner", "runtime": "actual runtime version",
  "target": "https://OWNER.github.io/SITE/",
  "observed_source_sha": "actual full SHA observed at the public site",
  "artifact_digest": "sha256:actual retained archive digest",
  "checks": [{
    "id": "F-1-retest", "kind": "browser", "result": "pass",
    "initial_state": "panel expanded, same date and selection as failed run",
    "action": "ordinary junction click, then ordinary popup close",
    "expected": "source link and close control remain clickable",
    "actual": "observed collapse, unobscured link and successful close",
    "viewport": "390x844", "browser_version": "actual browser version",
    "evidence_url": "https://actual-durable-evidence-url"
  }]
}
```

The above is a format illustration, not a passing record. Retain failed original steps,
normal user input and fresh screenshots/logs. A wrapper's zero exit status does not supply
these observations. The helper checks fields and bindings; independent QA must assess
whether the runner/human really tested the behavior. It does not autonomously drive a browser.

```text
python3 skills/aegis/scripts/release_workflow.py finalize --manifest /ABS/RELEASE_RUN/operation.json --output /ABS/FRESH_FINALIZE_RUN
```

Finalization revalidates source/output/archive, retrieves the published commit tree,
re-queries deployment, checks all public file hashes and structured browser observations,
and hashes each input record. In AEGIS mode it retrieves the task's current completed
requirement, original passing QA head/base/two-parent integration, actual merged PR/source
commit and matching integration/merged trees. A receipt URL alone cannot establish this.
If an original push returned `remote_unknown`, finalization first retrieves its original
branch/ref and requires the exact recorded artifact commit. It records this reconciliation
in the new observations, then applies every normal deployment/file/smoke gate. It never
changes the original unknown record, repushes, or removes its retained lock. An absent or
moved ref still requires investigation.

It writes a new versioned finalization receipt plus retrieved observations; legacy
`release_record.py` remains a structure-only v1 validator. Do not feed the new receipt to
that legacy validator or upgrade older records silently.

## Recovery and evidence delivery

```text
python3 skills/aegis/scripts/release_workflow.py resume --manifest /ABS/RELEASE_RUN/operation.json
python3 skills/aegis/scripts/evidence_publish.py resume --output /ABS/ORIGINAL_EVIDENCE_OPERATION
python3 skills/aegis/scripts/report_publish.py resume --output /ABS/ORIGINAL_REPORT_OPERATION
```

Resume is read-only. It reports `build`, `prepare`, `review_and_publish`,
`observe_original_deployment`, `verify_public_files`, `observe_public_smoke`,
`finalize_new_attempt` or `reconcile_original`. The suggested action is never executed
implicitly. A published ref proves the Git operation, not deployment or acceptance.

| Observation | Required next step |
|---|---|
| Build failure, dirty source, changed output | Preserve attempt; repair cause and use fresh build/output |
| Push timeout or ref absent/moved | Inspect original commit/ref and stopped process; no automatic repush/lock stealing |
| Missing/wrong/failed deployment | Retain observation; inspect original operation; no automatic redeploy |
| Partial or mismatched public files | Keep failed verification, diagnose cache/deployment, explicitly retry into fresh directory |
| Smoke exit zero without structured observations | Supply actual project/human browser observations; not a pass |
| Report timeout or incomplete pagination | Reconcile all pages by original record ID; no repost on absence/error |
| Sealed evidence changed | Reject upload; retain original and create explicitly linked new evidence run |

Use [sealed evidence publication](../../aegis/references/evidence-v2.md) to publish only
an explicit run, then publish its fixed report with the bounded report publisher. Preserve
operation records outside sealed source. Separate operation directories are not atomic
server exactly-once protection: cooperative agents must not concurrently publish the
same identity. Local bare-remote/provider-fixture tests remain offline proof; live proof
must name the actual repository/commit/deployment and durable URL observed.
