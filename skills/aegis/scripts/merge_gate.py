"""Verify queue policy and enqueue once. Never bypass branch rules or infer completion."""
import json
import subprocess
import uuid
from urllib.parse import quote
import policy

def enqueue(store, actor, token, issue, api, held):
    p=policy.load_policy(store.repo,api)
    policy.require(p['merge_mode']=='merge-queue','MERGE_MANUAL: automatic merge is disabled')
    state,sha=store.read();task=state['tasks'][str(issue)]
    import time
    lease=held(task,actor,token,int(time.time()))
    policy.require(lease['role']=='qa' and task['state']=='merge-ready','MERGE_ROLE: owned QA merge-ready task required')
    e=task['history'][-1]['evidence']
    if task.get('requirements',{}).get('evidence_schema')=='aegis-evidence/v2':
        policy.evidence_gate(task,'done',e,p)
        issue_record=api(store.repo,f'/issues/{issue}')
        policy.require(task['requirements']['source_body']==(issue_record.get('body') or ''),'ISSUE_CHANGED: reconcile requirements before enqueue')
    pr=api(store.repo,f"/pulls/{e['pr']}")
    policy.require(pr['state']=='open' and not pr['draft'],'MERGE_PR: open non-draft required')
    policy.require(pr['head']['sha']==e['head'] and pr['base']['sha']==e['base'],'MERGE_STALE: re-review/retest changed candidate')
    policy.remote_gate(store.repo,task,'merge-ready',e,p,api)
    rules=api(store.repo,'/rules/branches/'+quote(p['default_branch'],safe=''))
    types={r['type'] for r in rules}
    policy.require('merge_queue' in types and 'required_status_checks' in types and 'pull_request' in types,
                   'MERGE_RULES: active merge queue, pull request and check rules required')
    check_rules=[r for r in rules if r['type']=='required_status_checks']
    enforced={c['context'] for r in check_rules for c in r.get('parameters',{}).get('required_status_checks',[])}
    policy.require(set(p['required_checks'])<=enforced,'MERGE_RULES: all configured checks must be server-enforced')
    policy.require(any(r.get('parameters',{}).get('required_approving_review_count',0)>=1 for r in rules if r['type']=='pull_request'),'MERGE_RULES: independent server approval required')
    policy.require(not task.get('merge_request'),'MERGE_REQUEST_EXISTS: inspect original request/PR; never enqueue blindly twice')
    op=uuid.uuid4().hex
    task['merge_request']={'operation':op,'pr':e['pr'],'head':e['head'],'status':'sending'}
    state['revision']+=1;store.write(state,sha,op)
    cmd=['gh','pr','merge',str(e['pr']),'--repo',store.repo,'--auto','--match-head-commit',e['head']]
    try:
        result=subprocess.run(cmd,text=True,capture_output=True,timeout=60)
    except subprocess.TimeoutExpired:
        return {'status':'remote_unknown','operation':op,'state':'merge-ready'}
    # Even a nonzero CLI response may follow a successful remote enqueue.
    return {'status':'queued' if result.returncode==0 else 'remote_unknown','operation':op,
            'state':'merge-ready','next_action':'Inspect PR queue/merge status; only observed merge permits finish done'}
