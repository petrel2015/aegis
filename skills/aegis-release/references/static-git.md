# Static Git publication helpers

Use `skills/aegis/scripts/release_pipeline.py` from the Skill repository root. Helpers use the standard library, Git and gh. They do not infer permission from an Issue, run deployment automatically, or certify browser observations from a zero exit code.

Prepare an isolated build and a clean checkout of the existing artifact repository. Run the configured build and tests. Use `environment_check.py` when localhost tests fail or the host is unknown; preserve original failure and associate any approved retry with its evidence run.

```text
python3 skills/aegis/scripts/release_pipeline.py prepare \
  --build /ABS/SOURCE/dist --previous /ABS/ARTIFACT_CHECKOUT \
  --output /ABS/FRESH_RELEASE_RUN --source-sha FULL_SOURCE_SHA \
  --site https://OWNER.github.io/PROJECT-pages/
```

Inspect `artifact.json` before publication. Existing `CNAME`, `.nojekyll`, `ATTRIBUTION*`, `LICENSE*` and `COPYING*` are preserved byte-for-byte. Changes to these need separate review before preparing the release. Add project-specific retained files using `--protect PATH_PATTERN`. Every deletion, including replaced hashed assets, requires individual reviewed `--allow-remove PATH` arguments; filenames cannot establish that an old file is disposable. The archive includes only build files and protected public files; `.env*`, workflow config, node_modules and local evidence are rejected. Review other content for secrets; filenames alone cannot detect secrets.

Use the user's exact existing authorization and the observed artifact checkout commit:

```text
python3 skills/aegis/scripts/release_pipeline.py publish \
  --artifact /ABS/FRESH_RELEASE_RUN --checkout /ABS/ARTIFACT_CHECKOUT \
  --repo OWNER/PROJECT-pages --expected-base FULL_ARTIFACT_BASE_SHA \
  --authorization-ref 'Actual user request authorizing this destination'
```

It checks origin, clean checkout, remote base, file/ZIP integrity and retained files. It acquires an exclusive checkout-local Git lock, reserves the attempt, then commits and pushes once without force. A failed attempt retains its lock: inspect the original run, stop any running process and reconcile the commit/ref before removing that lock. `publish.json` starts as remote_unknown before push, becomes pending on push success. Never rerun an ambiguous publish; reconcile the recorded commit against the original remote ref. This checks cooperative publication conditions, not an atomic server deployment lock. Observe the provider job for this exact artifact commit separately.

After the provider confirms successful deployment:

```text
python3 skills/aegis/scripts/release_pipeline.py verify \
  --artifact /ABS/FRESH_RELEASE_RUN --output /ABS/FRESH_ONLINE_CHECK
```

All public files must equal the retained ZIP bytes. There are no implicit exclusions. A changed file or connection failure records unknown with diagnostics, retaining partial observations. A retry uses a new verification directory. `files_verified` does not mean deployed acceptance: additionally inspect actual deployment success and browser smoke.

Put the trusted project-specific browser command in a JSON argv array (no shell), targeting the exact site and writing its own date/viewport/screenshots observations:

```text
python3 skills/aegis/scripts/release_pipeline.py smoke \
  --argv-json /ABS/PROJECT_SMOKE_ARGV.json --output /ABS/FRESH_SMOKE_RUN \
  --target https://OWNER.github.io/PROJECT-pages/ --timeout 180
```

The helper saves stdout, stderr, exit/timeout; it cannot verify that arbitrary commands actually exercised the site. Use a bounded project browser runner, inspect observations, and link durable evidence. Finish the fixed release receipt using `release_record.py`; do not turn files_verified or a queued job into verified release status.
