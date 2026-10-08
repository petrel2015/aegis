#!/usr/bin/env python3
"""Validate a release receipt without deploying or claiming independent remote proof."""
import argparse
import json
import re
import policy


def validate(record):
    policy.require(record.get('schema')=='aegis-release/v1','RELEASE_SCHEMA: aegis-release/v1 required')
    policy.require(record.get('execution_mode') in ('aegis','external'),'RELEASE_EXECUTION: declare aegis or external')
    if record['execution_mode']=='aegis':
        policy.require(policy.durable_url(record.get('workflow_evidence_url')),'RELEASE_WORKFLOW: durable current workflow/QA evidence required')
    for field in ('source_repo','artifact_repo'):
        policy.require(isinstance(record.get(field),str) and re.fullmatch(r'[\w.-]+/[\w.-]+',record[field]),f'RELEASE_REPO: {field}')
    policy.require(record.get('status') in ('pending','failed','remote_unknown','verified'),'RELEASE_STATUS')
    policy.require(isinstance(record.get('source_sha'),str) and re.fullmatch(r'[a-f0-9]{40}',record['source_sha']),'RELEASE_SHA: source_sha')
    for field,pattern in (('artifact_commit',r'[a-f0-9]{40}'),('artifact_digest',r'sha256:[a-f0-9]{64}')):
        value=record.get(field)
        policy.require((value is None and record['status']!='verified') or (isinstance(value,str) and re.fullmatch(pattern,value)),f'RELEASE_ARTIFACT: {field}')
    if record['status'] in ('failed','remote_unknown') or any(record.get(k) is None for k in ('artifact_commit','artifact_digest')):
        policy.require(isinstance(record.get('diagnostics'),str) and record['diagnostics'].strip(),'RELEASE_DIAGNOSTICS: explain failure or unknown artifact')
    for field in ('authorization_ref','environment','build_mode','run_id','rollback'):
        policy.require(isinstance(record.get(field),str) and record[field].strip(),f'RELEASE_FIELD: {field}')
    policy.require(policy.durable_url(record.get('site_url')),'RELEASE_URL: exact destination required')
    if record['status']=='verified':
        policy.require(policy.durable_url(record.get('deployment_url')),'RELEASE_DEPLOYMENT: durable successful deployment record required')
        policy.require(record.get('deployment_status')=='success','RELEASE_DEPLOYMENT: build alone is not publication')
        policy.require(record.get('observed_source_sha')==record['source_sha'],'RELEASE_STALE: online source version differs')
        policy.require(record.get('observed_artifact_digest')==record['artifact_digest'],'RELEASE_STALE: online artifact differs')
        policy.require(record.get('smoke',{}).get('result')=='pass' and record['smoke'].get('target')==record['site_url'] and policy.durable_url(record['smoke'].get('evidence_url')),'RELEASE_SMOKE: exact public target must be tested')
    return {'status':'record_valid','release_status':record['status'],'proof':'receipt structure and bindings only; supplied online observations require independent verification'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('record')
    args=parser.parse_args()
    try:
        with open(args.record) as f:print(json.dumps(validate(json.load(f)),indent=2))
    except (OSError,ValueError,KeyError,TypeError) as e:raise SystemExit(str(e))
