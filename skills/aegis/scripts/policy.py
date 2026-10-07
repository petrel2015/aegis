"""Deterministic policy, intake and evidence gates. No model or shell execution."""
import base64
import json
import re
import shlex
from urllib.parse import quote, urlparse

class PolicyError(ValueError):
    pass

def require(ok, message):
    if not ok: raise PolicyError(message)

def validate_policy(p):
    require(isinstance(p, dict) and p.get('version') == 1, 'POLICY_VERSION: expected version 1')
    for key in ('max_issues_per_run','max_rework_rounds','max_run_minutes'):
        require(type(p.get(key)) is int and 1 <= p[key] <= 1440, f'POLICY_INVALID: {key}')
    require(p.get('merge_mode') in ('manual','merge-queue'), 'POLICY_INVALID: merge_mode')
    require(isinstance(p.get('intake_label'),str) and p['intake_label'], 'POLICY_INVALID: intake_label')
    require(isinstance(p.get('trusted_issue_authors'),list) and all(isinstance(x,str) for x in p['trusted_issue_authors']), 'POLICY_INVALID: trusted_issue_authors')
    commands=p.get('test_commands')
    require(isinstance(commands,list) and commands, 'POLICY_UNCONFIGURED: test_commands must not be empty')
    for cmd in commands:
        argv=shlex.split(cmd) if isinstance(cmd,str) else cmd
        require(isinstance(argv,list) and argv and all(isinstance(x,str) and x for x in argv), 'POLICY_INVALID: test command argv')
    require(isinstance(p.get('required_checks'),list) and p['required_checks'] and all(isinstance(x,str) and x for x in p['required_checks']), 'POLICY_UNCONFIGURED: required_checks must not be empty')
    require(p.get('review_mode','agent-attestation') in ('agent-attestation','github-review'), 'POLICY_INVALID: review_mode')
    require(p.get('check_app','github-actions') == 'github-actions', 'POLICY_INVALID: currently only GitHub Actions checks supported')
    return p

def load_policy(repo, api):
    meta=api(repo)
    branch=meta['default_branch']
    raw=api(repo, '/contents/.github/aegis.json?ref='+quote(branch,safe=''))
    p=validate_policy(json.loads(base64.b64decode(raw['content'])))
    p=dict(p, policy_sha=raw['sha'], default_branch=branch)
    return p

FIELDS={
 'feature':['background','expected benefit','scope and exclusions','acceptance criteria','alternatives and compatibility'],
 'bug':['environment','reproduction','expected behavior','actual behavior','impact','acceptance criteria'],
 'improvement':['background','expected benefit','scope and exclusions','acceptance criteria']}

def intake_issue(issue, p):
    require('pull_request' not in issue and issue.get('state') == 'open', 'INTAKE_INELIGIBLE: expected open Issue')
    labels={x['name'] for x in issue.get('labels',[])}
    author=issue.get('user',{}).get('login')
    require(p['intake_label'] in labels or author in p['trusted_issue_authors'], 'INTAKE_UNTRUSTED: maintainer label or trusted author required')
    match=re.match(r'^\[(feature|bug|improvement)\]', issue.get('title',''), re.I)
    require(match, 'INTAKE_FORMAT: title needs [feature], [bug] or [improvement]')
    kind=match.group(1).lower()
    parts=re.split(r'^#{2,3}\s+(.+?)\s*$', issue.get('body') or '', flags=re.M)
    sections={parts[i].strip().lower():parts[i+1].strip() for i in range(1,len(parts)-1,2)}
    for field in FIELDS[kind]+['priority']:
        require(sections.get(field) and sections[field].lower() not in ('_no response_','n/a','tbd'),f'INTAKE_MISSING: {field}')
    priority=re.search(r'\bP([0-3])\b',sections['priority'])
    require(priority,'INTAKE_FORMAT: priority P0..P3 required')
    ac=re.findall(r'\bAC-[1-9][0-9]*\b',sections['acceptance criteria'])
    require(ac and len(ac)==len(set(ac)), 'INTAKE_FORMAT: unique AC-1, AC-2 acceptance IDs required')
    deps=[int(n) for n in re.findall(r'#([1-9][0-9]*)',sections.get('dependencies',''))]
    require(issue['number'] not in deps,'DEPENDENCY_CYCLE: Issue depends on itself')
    return {'kind':kind,'priority':int(priority.group(1)),'acceptance_ids':ac,
            'dependencies':sorted(set(deps)), 'issue_updated_at':issue.get('updated_at'),
            'source_body':issue.get('body') or '', 'policy_sha':p.get('policy_sha')}

def validate_claim(state, task, p):
    req=task.get('requirements')
    require(req, 'LEGACY_TASK: missing intake contract; maintainer migration required; do not reset history')
    missing=[n for n in req.get('dependencies',[]) if state['tasks'].get(str(n),{}).get('state')!='done']
    require(not missing, f'DEPENDENCY_BLOCKED: {missing}')
    rounds=sum(e['to'] in ('new','ready') and e['from'] in ('design-review','code-review','testing') for e in task['history'])
    require(rounds < p['max_rework_rounds'], 'REWORK_LIMIT: maintainer must review; no further automatic claim')

def durable_url(value):
    if not isinstance(value,str):return False
    u=urlparse(value)
    return u.scheme=='https' and bool(u.netloc) and not u.username and not u.password

def evidence_gate(task, target, e, p):
    require(e.get('schema')=='aegis-evidence/v1','EVIDENCE_SCHEMA: aegis-evidence/v1 required')
    require(durable_url(e.get('url')), 'EVIDENCE_URL: durable HTTPS report URL required')
    require(isinstance(e.get('summary'),str) and 0 < len(e['summary']) <= 6000, 'EVIDENCE_SUMMARY: nonempty bounded summary required')
    current=task['state']
    if target in ('blocked','new','ready') and not (current=='design-review' and target=='ready'):
        require(e.get('result') != 'pass', 'EVIDENCE_CONTRADICTION: rework/blocked is not pass')
        return
    if current=='merge-ready' and target=='testing':return
    require(task.get('requirements'), 'LEGACY_TASK: missing acceptance contract')
    acceptance=e.get('acceptance')
    require(isinstance(acceptance,dict) and set(acceptance)==set(task['requirements']['acceptance_ids']), 'EVIDENCE_AC: exact acceptance ID coverage required')
    for key, item in acceptance.items():
        require(isinstance(item,dict) and item.get('result')=='pass' and durable_url(item.get('evidence')),f'EVIDENCE_AC: {key} needs pass and HTTPS evidence')
    if current=='new':
        require(e.get('kind')=='design' and re.fullmatch(r'sha256:[0-9a-f]{64}',e.get('design_ref','')), 'DESIGN_REF: immutable sha256 design digest required')
    if current=='design-review':
        require(e.get('kind')=='design-review' and e.get('result')=='approve','REVIEW_REQUIRED: approved design review required')
        require(e.get('design_ref')==task['history'][-1]['evidence'].get('design_ref'), 'DESIGN_CHANGED: reviewed design digest differs')
    if current=='ready':
        require(e.get('kind')=='development','EVIDENCE_KIND: development required')
        approved=[h['evidence'] for h in task['history'] if h['from']=='design-review' and h['to']=='ready']
        require(approved and e.get('design_ref')==approved[-1].get('design_ref'),'DESIGN_REQUIRED: candidate must link approved design')
    if current=='code-review':
        require(e.get('kind')=='code-review' and e.get('result')=='approve', 'REVIEW_REQUIRED: approved code review required')
        require(e.get('reviewed_head')==e.get('head'),'REVIEW_STALE: exact reviewed head required')
    if current=='testing':
        require(e.get('kind')=='qa' and e.get('result')=='pass','QA_REQUIRED: passing QA report required')
        commands=e.get('tests',[])
        expected=[shlex.split(c) if isinstance(c,str) else c for c in p['test_commands']]
        require(len(commands)==len(expected), 'QA_TESTS: all configured commands required')
        for command,expected_argv in zip(commands,expected):
            require(command.get('argv')==expected_argv and type(command.get('exit_code')) is int and command['exit_code']==0 and durable_url(command.get('log_url')), 'QA_TESTS: command/result/log mismatch')

def required_checks(repo, head, p, api):
    runs=[]
    for page in range(1,101):
        result=api(repo,f'/commits/{head}/check-runs?per_page=100&page={page}')
        batch=result['check_runs'];runs+=batch
        if len(batch)<100:break
    else:raise PolicyError('CHECK_PAGINATION_LIMIT')
    for name in p['required_checks']:
        matches=[r for r in runs if r['name']==name and r.get('head_sha')==head and r.get('app',{}).get('slug')==p.get('check_app','github-actions')]
        latest=max(matches,key=lambda r:r['id'],default={})
        require(latest.get('status')=='completed' and latest.get('conclusion')=='success',f'CHECK_REQUIRED: latest trusted {name} must succeed for {head}')

def remote_gate(repo, task, target, evidence, p, api):
    if target not in ('testing','merge-ready','done'): return
    pr=api(repo,f"/pulls/{evidence['pr']}")
    require(pr['base'].get('ref')==p['default_branch'], 'PR_BASE: target default branch required')
    if target=='merge-ready':
        required_checks(repo,evidence['head'],p,api)
        commit=api(repo,f"/git/commits/{evidence['tested_commit']}")
        parents={x['sha'] for x in commit.get('parents',[])}
        require({evidence['head'],evidence['base']} <= parents, 'QA_INTEGRATION: tested commit must merge exact head and base')
    if p.get('review_mode','agent-attestation')=='github-review':
        reviews=[]
        for page in range(1,101):
            batch=api(repo,f"/pulls/{evidence['pr']}/reviews?per_page=100&page={page}");reviews+=batch
            if len(batch)<100:break
        else:raise PolicyError('REVIEW_PAGINATION_LIMIT')
        latest={}
        for r in sorted(reviews,key=lambda r:r['id']):
            if r['state'] in ('APPROVED','CHANGES_REQUESTED','DISMISSED'):latest[r['user']['login']]=r
        require(not any(r['state']=='CHANGES_REQUESTED' for r in latest.values()), 'REVIEW_CHANGES_REQUESTED')
        require(any(r['state']=='APPROVED' and r.get('commit_id')==evidence['head'] and user!=pr['user']['login'] for user,r in latest.items()), 'REVIEW_REQUIRED: independent GitHub approval of this head required')
