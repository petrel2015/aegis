"""Read-only continuation diagnostics and explicit versioned requirement revisions."""
import copy
import subprocess
import time
import policy


def revise(source, issue, requirements, actor, reason, affected, evidence_url, expected, operation):
    import aegis
    policy.require(source['revision']==expected, 'REVISION_STALE: reread before revising')
    task=source['tasks'].get(str(issue))
    policy.require(task is not None,'Register issue first')
    policy.require(task['state']!='done','TASK_COMPLETE: register a follow-up Issue; preserve completed work')
    policy.require(task.get('lease') is None,'BUSY: release or explicitly recover the stopped worker before revising')
    policy.require(not (source.get('qa') and source['qa']['issue']==str(issue)), 'QA_BUSY: recover inconsistent QA ownership first')
    policy.require(not task.get('merge_request'),'MERGE_PENDING: resolve original queue request before creating a follow-up Issue')
    old=task['requirements']
    policy.require(old['source_body']!=requirements['source_body'],'NO_CHANGE: no new requirement body')
    policy.require(isinstance(reason,str) and reason.strip() and policy.durable_url(evidence_url),'REVISION_EVIDENCE: reason and durable decision URL required')
    policy.require(affected and set(affected)<=set(old['acceptance_ids'])|set(requirements['acceptance_ids']),'REVISION_AC: affected IDs must belong to old or new contract')
    changed={k for k in set(old.get('criteria',{}))|set(requirements.get('criteria',{})) if old.get('criteria',{}).get(k)!=requirements.get('criteria',{}).get(k)}
    policy.require(changed<=set(affected),'REVISION_AC: all changed/added/removed criteria must be declared')
    result=copy.deepcopy(source);t=result['tasks'][str(issue)]
    revision=old.get('version',1)+1
    t.setdefault('requirement_revisions',[]).append({'previous':copy.deepcopy(old),'from_state':t['state'],
        'reason':reason,'affected_acceptance':sorted(set(affected)),'decision_url':evidence_url,
        'actor':actor,'operation':operation,'at':int(time.time()),'superseded_history_end':len(t['history'])})
    t['requirements']=dict(requirements,version=revision)
    t['requirements_history_start']=len(t['history'])
    t['state']='new'
    # Contributor identities and all previous evidence remain for audit and independence.
    aegis.enqueue(t,task['state'],actor,operation,int(time.time()),
                  {'summary':reason,'url':evidence_url},kind='requirements-revision')
    result['revision']+=1;result['last_operation']=operation
    return result


def resume(repo,state,issue,actor,role,live_issue,api,workspace=None):
    import aegis
    task=state['tasks'].get(str(issue));diagnostics=[]
    result={'repo':repo,'issue':issue,'role':role,'actor':actor,'workflow_verified':False,
            'state_revision':state['revision'],'diagnostics':diagnostics}
    if not task:
        return dict(result,status='unregistered',next_action='Planner must validate and register this Issue before implementation.')
    req=task.get('requirements',{})
    result.update(state=task['state'],requirements_version=req.get('version',1),requirements_digest=req.get('digest'),
                  expected_role=aegis.ROLES.get(task['state']),lease=task.get('lease'))
    if req.get('source_body')!=(live_issue.get('body') or ''):diagnostics.append('REQUIREMENTS_CHANGED')
    if live_issue.get('state')!='open' and task['state'] not in ('done','merge-ready'):diagnostics.append('ISSUE_CLOSED')
    lease=task.get('lease')
    if lease and lease['expires']<=int(time.time()):diagnostics.append('LEASE_EXPIRED')
    elif lease and (lease['actor']!=actor or lease['role']!=role):diagnostics.append('OWNED_BY_OTHER')
    if task['state']=='blocked':diagnostics.append('TASK_BLOCKED')
    if task['state'] not in ('done','blocked') and aegis.ROLES.get(task['state'])!=role:diagnostics.append('ROLE_MISMATCH')
    candidates=[h['evidence'] for h in policy.current_history(task) if h.get('evidence',{}).get('pr')]
    candidate=candidates[-1] if candidates else None
    if candidate:
        pr=api(repo,f"/pulls/{candidate['pr']}")
        result['candidate']={'pr':candidate['pr'],'recorded_head':candidate.get('head'),'live_head':pr['head']['sha'],'base':pr['base']['sha'],'merged':pr.get('merged',False)}
        if candidate.get('head')!=pr['head']['sha']:diagnostics.append('CANDIDATE_CHANGED')
        if task['state']=='merge-ready' and candidate.get('base')!=pr['base']['sha']:diagnostics.append('BASE_CHANGED')
        if task['state']!='done' and pr['state']=='closed' and not pr.get('merged'):diagnostics.append('PR_CLOSED')
    if workspace:
        def git(*args):
            return subprocess.run(['git','-C',str(workspace),*args],text=True,capture_output=True,timeout=15,check=True).stdout.strip()
        try:
            origin=git('remote','get-url','origin')
            normalized=origin.removeprefix('git@github.com:').removeprefix('https://github.com/').rstrip('/').removesuffix('.git')
            if normalized.lower()!=repo.lower():diagnostics.append('WORKSPACE_REPO_MISMATCH')
            result['workspace']={'head':git('rev-parse','HEAD'),'dirty':bool(git('status','--porcelain'))}
            if result['workspace']['dirty']:diagnostics.append('LOCAL_CHANGES_REQUIRE_RECONCILIATION')
            if candidate and result['workspace']['head']!=candidate.get('head'):diagnostics.append('LOCAL_HEAD_DIFFERS')
        except (OSError,subprocess.SubprocessError):diagnostics.append('WORKSPACE_UNVERIFIED')
    if task['state']=='done':
        return dict(result,status='done' if not diagnostics else 'needs_attention',next_action='Follow-up work requires a new Issue; merge completion is not deployment proof.')
    return dict(result,status='needs_attention' if diagnostics else 'resume_owned' if lease else 'ready_to_claim',
                next_action='Resolve diagnostics; preserve prior work and evidence.' if diagnostics else 'Renew the existing claim before continuing.' if lease else 'Claim the eligible task before doing work.')
