#!/usr/bin/env python3
"""Source-bound release commands and read-only continuation; never an automatic deploy loop."""
import argparse
import json
from pathlib import Path
import subprocess
import release_build
import release_finalize
import release_pipeline
from release_support import api, fingerprint, guard_release_output, read, require, reserve, write

PATHS = ('source', 'build_output', 'build_record', 'artifact', 'publication_record',
         'verification_record', 'smoke_record', 'deployment_record')


def start(plan, output):
    for key in PATHS:
        require(key in plan and Path(plan[key]).is_absolute(), 'PLAN_PATH: explicit absolute ' + key)
    release_pipeline.valid_site(plan['site_url'])
    require(plan['authorization_ref'].strip(), 'AUTHORIZATION')
    guard_release_output(output, plan)
    return reserve(output, 'aegis-release-plan/v1', plan=plan)


def load_plan(manifest):
    record = read(manifest)
    require(record.get('schema') == 'aegis-release-plan/v1', 'PLAN_SCHEMA')
    return record['plan']


def observed_plan(manifest):
    plan = load_plan(manifest)
    observation = read(plan['deployment_record'])
    require(observation.get('status') == 'observed' and observation['manifest_digest'] == fingerprint(manifest), 'DEPLOYMENT_PLAN_BINDING')
    return dict(plan, release_manifest=str(Path(manifest).resolve()),
                deployment_run_id=observation['deployment_run_id'], deployment_id=observation['deployment_id'])


def observe(manifest, run_id, deployment_id):
    plan = load_plan(manifest)
    guard_release_output(plan['deployment_record'], plan, record_directories=False)
    publication = read(plan['publication_record'])
    bound = dict(plan, deployment_run_id=run_id, deployment_id=deployment_id)
    # IDs are supplied explicitly, then retrieved; no search for a convenient green run.
    record = dict(schema='aegis-deployment-observation/v1', status='remote_unknown',
                  manifest_digest=fingerprint(manifest), deployment_run_id=run_id, deployment_id=deployment_id)
    write(plan['deployment_record'], record, exclusive=True)
    try:
        record['observation'] = release_finalize.deployment(bound, publication['artifact_commit'])
        record['status'] = 'observed'
    except Exception as error:
        record['diagnostics'] = str(error)
        raise
    finally:
        write(plan['deployment_record'], record)
    return record


def resume(manifest, get=api):
    plan = load_plan(manifest)
    result = dict(status='pending', operation_id=read(manifest)['operation_id'],
                  proof='Read-only reconciliation; no push, comment, deployment, lock removal or old-record rewrite.')
    try:
        if not Path(plan['build_record']).exists():
            return dict(result, next_action='build', diagnostics='No recorded build; use a fresh build operation.')
        release_build.validate(plan['build_record'])
        if not Path(plan['artifact']).exists():
            return dict(result, next_action='prepare')
        artifact, _ = release_pipeline.load_artifact(plan['artifact'])
        if not Path(plan['publication_record']).exists():
            return dict(result, next_action='review_and_publish', diagnostics='Review exact destination, diff and existing authorization before one explicit publication.')
        publication = read(plan['publication_record'])
        require(publication['repo'] == plan['artifact_repo'] and publication['source_sha'] == artifact['source_sha'], 'PUBLICATION_BINDING')
        require(publication.get('artifact_commit'), 'PUBLICATION_COMMIT_UNKNOWN')
        remote = get(f'repos/{publication["repo"]}/git/ref/heads/{publication["branch"]}')
        require(remote['object']['sha'] == publication['artifact_commit'], 'PUBLICATION_REF_UNKNOWN_OR_MOVED')
        if not Path(plan['deployment_record']).exists():
            return dict(result, next_action='observe_original_deployment', artifact_commit=publication['artifact_commit'], diagnostics='Record original run and deployment IDs after read-only provider inspection; never redeploy automatically.')
        release_finalize.deployment(observed_plan(manifest), publication['artifact_commit'], get)
        for key, action in [('verification_record', 'verify_public_files'), ('smoke_record', 'observe_public_smoke')]:
            if not Path(plan[key]).exists():
                return dict(result, next_action=action)
        return dict(result, next_action='finalize_new_attempt', diagnostics='Revalidate all bindings in a fresh finalization directory; retained failed attempts remain unchanged.')
    except Exception as error:
        return dict(result, status='remote_unknown', diagnostics=str(error), next_action='reconcile_original',
                    instruction='Inspect original records and stop unresolved workers; do not replay an external write.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('build')
    for key in ('source', 'build-output', 'output', 'repo', 'argv-json', 'mode'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--timeout', type=int, default=600)
    p = sub.add_parser('prepare')
    for key in ('build-record', 'previous', 'output', 'site'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--allow-remove', action='append', default=[])
    p.add_argument('--protect', action='append', default=[])
    p = sub.add_parser('start'); p.add_argument('--plan', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('observe-deployment'); p.add_argument('--manifest', required=True)
    p.add_argument('--run-id', required=True, type=int); p.add_argument('--deployment-id', required=True, type=int)
    p = sub.add_parser('finalize'); p.add_argument('--manifest', required=True); p.add_argument('--output', required=True)
    sub.add_parser('resume').add_argument('--manifest', required=True)
    a = parser.parse_args()
    if a.action == 'build':
        result = release_build.build(a.source, a.build_output, a.output, a.repo, read(a.argv_json), a.mode, a.timeout)
    elif a.action == 'prepare':
        result = release_build.prepare(a.build_record, a.previous, a.output, a.site, a.allow_remove, a.protect)
    elif a.action == 'start':
        result = start(read(a.plan), a.output)
    elif a.action == 'observe-deployment':
        result = observe(a.manifest, a.run_id, a.deployment_id)
    elif a.action == 'finalize':
        result = release_finalize.finalize(observed_plan(a.manifest), a.output)
    else:
        result = resume(a.manifest)
    print(json.dumps(result, indent=2))
    return int(result.get('status') in ('failed', 'remote_unknown'))


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
