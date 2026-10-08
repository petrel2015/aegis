"""Derive release acceptance from bound local records and live GitHub observations."""
import base64
from pathlib import Path
import re
import release_build
import release_pipeline as pipeline
from release_support import api, fingerprint, read, require, reserve, write


def deployment(plan, commit, get=api):
    repo, run_id, deployment_id = plan['artifact_repo'], plan['deployment_run_id'], plan['deployment_id']
    require(type(run_id) is int and run_id > 0 and type(deployment_id) is int and deployment_id > 0, 'DEPLOYMENT_IDS')
    run = get(f'repos/{repo}/actions/runs/{run_id}')
    require(run.get('id') == run_id and run.get('repository', {}).get('full_name') == repo, 'DEPLOYMENT_REPO')
    require(run.get('head_sha') == commit and run.get('status') == 'completed' and run.get('conclusion') == 'success', 'DEPLOYMENT_RUN')
    require(run.get('path') == plan['workflow_path'], 'DEPLOYMENT_WORKFLOW')
    deployed = get(f'repos/{repo}/deployments/{deployment_id}')
    require(deployed.get('id') == deployment_id and deployed.get('sha') == commit and
            deployed.get('environment') == plan['deployment_environment'], 'DEPLOYMENT_IDENTITY')
    statuses = get(f'repos/{repo}/deployments/{deployment_id}/statuses?per_page=1')
    require(isinstance(statuses, list) and len(statuses) == 1, 'DEPLOYMENT_STATUS_MISSING')
    latest = statuses[0]  # GitHub returns latest first; never select an older success.
    require(latest.get('state') == 'success' and latest.get('environment_url') == plan['site_url'], 'DEPLOYMENT_STATUS')
    prefix = f'https://github.com/{repo}/actions/runs/{run_id}'
    require(re.fullmatch(re.escape(prefix) + r'(?:/job/[0-9]+)?/?', latest.get('log_url', '')), 'DEPLOYMENT_RUN_CORRELATION')
    return {'run': run, 'deployment': deployed, 'latest_status': latest}


def workflow(plan, source_sha, get=api):
    if plan['execution_mode'] == 'external':
        return {'execution_mode': 'external', 'proof': 'No AEGIS task lifecycle claimed.'}
    require(plan['execution_mode'] == 'aegis', 'EXECUTION_MODE')
    repo, issue, pr_number = plan['source_repo'], plan['issue'], plan['source_pr']
    require(type(issue) is int and issue > 0 and type(pr_number) is int and pr_number > 0, 'WORKFLOW_IDS')
    import json
    content = get(f'repos/{repo}/contents/aegis-state.json?ref=aegis-state')
    require(content.get('encoding') == 'base64', 'WORKFLOW_STATE_ENCODING')
    state = json.loads(base64.b64decode(content['content']))
    task = state['tasks'][str(issue)]
    require(task['state'] == 'done', 'WORKFLOW_NOT_DONE')
    history = task['history'][task.get('requirements_history_start', 0):]
    candidates = [item['evidence'] for item in history if item.get('from') == 'testing' and item.get('to') == 'merge-ready']
    require(candidates, 'WORKFLOW_QA_MISSING')
    qa = candidates[-1]
    require(qa.get('result') == 'pass' and qa.get('pr') == pr_number and qa.get('requirements_digest') == task['requirements']['digest'] and qa.get('requirements_version') == task['requirements']['version'], 'WORKFLOW_QA_BINDING')
    pr = get(f'repos/{repo}/pulls/{pr_number}')
    require(pr.get('merged') is True and pr.get('merge_commit_sha') == source_sha and
            pr.get('head', {}).get('sha') == qa.get('head') and pr.get('base', {}).get('repo', {}).get('full_name') == repo, 'WORKFLOW_MERGE_BINDING')
    integration = get(f'repos/{repo}/git/commits/{qa["tested_commit"]}')
    parents = [parent['sha'] for parent in integration['parents']]
    require(parents == [qa['base'], qa['head']], 'WORKFLOW_INTEGRATION')
    merged = get(f'repos/{repo}/git/commits/{source_sha}')
    require(merged['tree']['sha'] == integration['tree']['sha'], 'WORKFLOW_MERGED_TREE')
    completions = [item.get('evidence', {}) for item in history if item.get('to') == 'done']
    require(completions and completions[-1].get('pr') == pr_number and completions[-1].get('head') == qa['head'], 'WORKFLOW_COMPLETION_BINDING')
    return {'execution_mode': 'aegis', 'issue': issue, 'pr': pr, 'qa': qa,
            'integration': integration, 'state_blob': content.get('sha'), 'state_revision': state['revision']}


def finalize(plan, output, get=api):
    # Plan is explicit trusted operator configuration, never inferred from Issue text.
    result = reserve(output, 'aegis-release-finalization/v1', plan=plan, status_detail='Inputs not yet verified')
    observations = {}
    try:
        for field in ('source_repo', 'artifact_repo'):
            require(re.fullmatch(r'[\w.-]+/[\w.-]+', plan[field]), 'RELEASE_REPO')
        require(plan['authorization_ref'].strip() and plan['rollback'].strip(), 'RELEASE_AUTHORIZATION')
        require(plan['workflow_path'].strip() and plan['deployment_environment'] == 'github-pages', 'RELEASE_DEPLOYMENT_CONFIG')
        manifest, _ = pipeline.load_artifact(plan['artifact'])
        build = release_build.validate(plan['build_record'])
        binding = manifest.get('build_binding', {})
        require(binding.get('record_digest') == fingerprint(plan['build_record']) and binding.get('operation_id') == build['operation_id'], 'BUILD_BINDING')
        require(manifest['source_sha'] == build['source_sha'] and build['source_repo'] == plan['source_repo'], 'SOURCE_BINDING')
        require(manifest['site_url'] == plan['site_url'], 'SITE_BINDING')
        publication = read(plan['publication_record'])
        require(publication.get('status') == 'pending' and publication.get('repo') == plan['artifact_repo'] and publication.get('source_sha') == build['source_sha'], 'PUBLICATION_BINDING')
        commit = publication.get('artifact_commit')
        require(isinstance(commit, str) and re.fullmatch('[a-f0-9]{40}', commit), 'ARTIFACT_COMMIT')
        # Validate published commit's complete Git tree against the retained exact files.
        tree = get(f'repos/{plan["artifact_repo"]}/git/trees/{commit}?recursive=1')
        require(not tree.get('truncated'), 'ARTIFACT_TREE_TRUNCATED')
        blobs = {entry['path']: entry for entry in tree['tree'] if entry['type'] == 'blob'}
        require(set(blobs) == set(manifest['files']), 'ARTIFACT_COMMIT_FILES')
        import hashlib
        _, files = pipeline.load_artifact(plan['artifact'])
        for name, data in files.items():
            require(blobs[name]['mode'] in ('100644', '100755') and blobs[name]['sha'] == hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(), 'ARTIFACT_COMMIT_CONTENT')
        observations['artifact_tree'] = tree
        observations['deployment'] = deployment(plan, commit, get)
        observations['workflow'] = workflow(plan, build['source_sha'], get)
        verification = read(plan['verification_record'])
        require(verification.get('status') == 'files_verified' and verification.get('site_url') == plan['site_url'] and verification.get('observed_source_sha') == build['source_sha'] and verification.get('observed_artifact_digest') == manifest['artifact_digest'] and verification.get('files') == manifest['files'] and verification.get('exclusions') == [], 'PUBLIC_FILES_BINDING')
        smoke = read(plan['smoke_record'])
        require(smoke.get('schema') == 'aegis-smoke-observations/v1', 'SMOKE_OBSERVATIONS_REQUIRED')
        require(smoke.get('target') == plan['site_url'] and smoke.get('observed_source_sha') == build['source_sha'] and smoke.get('artifact_digest') == manifest['artifact_digest'], 'SMOKE_BINDING')
        require(smoke.get('run_id') and smoke.get('runtime') and smoke.get('provenance') in ('project-runner', 'human-observation') and smoke.get('recorded_at'), 'SMOKE_PROVENANCE')
        checks = smoke.get('checks')
        require(isinstance(checks, list) and checks and any(check.get('kind') == 'browser' for check in checks), 'SMOKE_BROWSER_REQUIRED')
        for check in checks:
            require(check.get('id') and check.get('result') == 'pass' and check.get('initial_state') and check.get('action') and check.get('expected') and check.get('actual') and check.get('evidence_url', '').startswith('https://'), 'SMOKE_CHECK')
            if check.get('kind') == 'browser':
                require(check.get('viewport') and check.get('browser_version'), 'SMOKE_BROWSER_ENVIRONMENT')
        inputs = {key: fingerprint(plan[key]) for key in ('build_record', 'publication_record', 'verification_record', 'smoke_record')}
        inputs['artifact_manifest'] = fingerprint(Path(plan['artifact']) / 'artifact.json')
        result.update(status='verified', source_repo=plan['source_repo'], source_sha=build['source_sha'],
                      artifact_repo=plan['artifact_repo'], artifact_commit=commit, artifact_digest=manifest['artifact_digest'],
                      site_url=plan['site_url'], inputs=inputs, build_operation_id=build['operation_id'], smoke_run_id=smoke['run_id'],
                      proof='Live deployment and Git/workflow bindings plus supplied project/human browser observations; not independent browser semantics or hostile-writer attestation.')
    except Exception as error:
        result.update(status='remote_unknown' if not isinstance(error, ValueError) else 'failed', diagnostics=str(error))
        raise
    finally:
        write(Path(output) / 'observations.json', observations, exclusive=True)
        write(Path(output) / 'operation.json', result)
    return result
