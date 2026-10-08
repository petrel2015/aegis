import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/aegis/scripts'))
import aegis, continuation, policy, evidence_store, release_record
from test_policy import P,I,BODY,E

class ContinuationTests(unittest.TestCase):
 def state(self):
  s=aegis.mutate(aegis.new_state(),'register',1,'planner',op='register')
  s['tasks']['1']['requirements']=policy.intake_issue(I,P)
  return s
 def revision(self,s,**kw):
  req=policy.intake_issue(dict(I,body=BODY.replace('visible result','territory polygon changes')),P)
  return continuation.revise(s,1,req,'operator','User clarified territory fill',['AC-1'],'https://example.test/decision',kw.get('expected',s['revision']),'revision')
 def test_revision_preserves_audit_and_invalidates_old_approval(self):
  s=self.state();t=s['tasks']['1'];t['state']='ready'
  t['history']=[{'from':'design-review','to':'ready','evidence':dict(E,design_ref='sha256:'+'a'*64)}]
  t['contributors']={'developer':['author-1']};before=copy.deepcopy(s)
  new=self.revision(s);t=new['tasks']['1']
  self.assertEqual(s,before);self.assertEqual(t['state'],'new');self.assertEqual(t['requirements']['version'],2)
  self.assertEqual(t['history'],before['tasks']['1']['history']);self.assertEqual(t['contributors'],{'developer':['author-1']})
  self.assertEqual(t['requirement_revisions'][0]['previous']['source_body'],BODY)
  with self.assertRaisesRegex(policy.PolicyError,'REQUIREMENTS_STALE'):policy.evidence_gate(t,'design-review',E,P)
  t['state']='ready';e=copy.deepcopy(E);e.update(kind='development',requirements_version=2,requirements_digest=t['requirements']['digest']);e['acceptance']['AC-1']['result']='implemented'
  with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_CHAIN'):policy.evidence_gate(t,'code-review',e,P)
 def test_revision_refuses_busy_done_queued_and_stale_state(self):
  for field,value in [('lease',{'token':'x'}),('state','done'),('merge_request',{'status':'sending'})]:
   s=self.state();s['tasks']['1'][field]=value
   with self.assertRaises(policy.PolicyError):self.revision(s)
  with self.assertRaisesRegex(policy.PolicyError,'REVISION_STALE'):self.revision(self.state(),expected=99)
 def test_resume_reports_edits_without_mutation(self):
  s=self.state();before=copy.deepcopy(s)
  r=continuation.resume('o/r',s,1,'planner','planner',dict(I,body=BODY+' changed'),lambda *a:None)
  self.assertEqual(r['status'],'needs_attention');self.assertIn('REQUIREMENTS_CHANGED',r['diagnostics']);self.assertFalse(r['workflow_verified']);self.assertEqual(s,before)
 def test_resume_candidate_and_role_drift(self):
  s=self.state();t=s['tasks']['1'];t['state']='testing';t['history']=[{'evidence':{'pr':4,'head':'a'*40}}]
  api=lambda *a:{'head':{'sha':'b'*40},'base':{'sha':'c'*40},'state':'open'}
  result=continuation.resume('o/r',s,1,'worker','developer',I,api)
  self.assertEqual(set(result['diagnostics']),{'ROLE_MISMATCH','CANDIDATE_CHANGED'})
 def test_resume_owned_expired_and_unregistered(self):
  s=self.state();self.assertEqual(continuation.resume('o/r',s,1,'a','planner',I,None)['status'],'ready_to_claim')
  s['tasks']['1']['lease']={'actor':'a','role':'planner','expires':9999999999}
  self.assertEqual(continuation.resume('o/r',s,1,'a','planner',I,None)['status'],'resume_owned')
  s['tasks']['1']['lease']['expires']=0
  self.assertIn('LEASE_EXPIRED',continuation.resume('o/r',s,1,'a','planner',I,None)['diagnostics'])
  self.assertEqual(continuation.resume('o/r',s,2,'a','planner',I,None)['status'],'unregistered')
 def test_resume_cli_is_read_only(self):
  s=self.state()
  with patch.object(aegis.Store,'read',return_value=(s,'sha')),patch.object(aegis.Store,'write') as write,patch.object(aegis,'gh_api',return_value=I),patch.object(policy,'load_policy',return_value=P):
   result=aegis.main(['--repo','o/r','resume','--issue','1','--actor','a','--role','planner'])
   self.assertEqual(result['status'],'ready_to_claim');write.assert_not_called()
 def test_cli_revision_uses_cas_and_syncs(self):
  s=self.state();changed=dict(I,body=BODY.replace('visible result','territory polygon changes'))
  with patch.object(aegis.Store,'read',return_value=(s,'expected-blob')),patch.object(aegis.Store,'write') as write,patch.object(aegis,'gh_api',return_value=changed),patch.object(policy,'load_policy',return_value=P),patch.object(aegis,'sync_issue',return_value={'status':'synced'}):
   result=aegis.main(['--repo','o/r','revise','--issue','1','--actor','operator','--reason','clarified','--affected-ac','AC-1','--evidence-url','https://example.test/decision','--expected-revision',str(s['revision']),'--confirm-stopped'])
   self.assertEqual(write.call_args.args[1],'expected-blob');self.assertEqual(result['task']['state'],'new');self.assertEqual(result['sync']['status'],'synced')

class EvidenceV2Tests(unittest.TestCase):
 def test_intake_requires_observable_negative_and_verification(self):
  for label in ('Outcome:','Counterexample:','Verification:'):
   with self.assertRaisesRegex(policy.PolicyError,'INTAKE_ACCEPTANCE'):policy.intake_issue(dict(I,body=BODY.replace(label,'Omitted:')),P)
 def test_blank_outcome_cannot_consume_next_field(self):
  with self.assertRaisesRegex(policy.PolicyError,'INTAKE_ACCEPTANCE'):
   policy.intake_issue(dict(I,body=BODY.replace('Outcome: visible result','Outcome:')),P)
 def test_stage_cannot_claim_qa_pass_during_design(self):
  task={'state':'new','requirements':policy.intake_issue(I,P),'history':[]}
  e=copy.deepcopy(E);e['acceptance']['AC-1']['result']='verified'
  with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_AC'):policy.evidence_gate(task,'design-review',e,P)
 def test_legacy_evidence_remains_explicit_legacy(self):
  task={'state':'new','requirements':{'acceptance_ids':['AC-1']},'history':[]}
  e=copy.deepcopy(E);e['schema']='aegis-evidence/v1';e['acceptance']['AC-1']['result']='pass'
  policy.evidence_gate(task,'design-review',e,P)
 def test_qa_groups_environment_and_duplicate_run(self):
  p=dict(P,verification_groups={'browser':[['node','tests/browser.mjs']]});policy.validate_policy(p)
  task={'state':'testing','requirements':policy.intake_issue(I,p),'history':[{'from':'code-review','to':'testing','evidence':dict(E,kind='code-review',result='approve')}]}
  e=copy.deepcopy(E);e.update(kind='qa',result='pass',run_id='run123456',environment={'runtime':'node22','build_mode':'pages','target':'local preview'},tests=[{'group':x['group'],'argv':x['argv'],'exit_code':0,'log_url':'https://example.test/log'} for x in policy.verification_commands(p)])
  e['acceptance']['AC-1']['result']='verified';policy.evidence_gate(task,'merge-ready',e,p)
  for bad in (dict(e,tests=e['tests'][:1]),dict(e,environment={}),dict(e,tests=[dict(e['tests'][0],exit_code=True),e['tests'][1]])):
   with self.assertRaises(policy.PolicyError):policy.evidence_gate(task,'merge-ready',bad,p)
  task['history']=[{'from':'testing','to':'ready','evidence':e},{'from':'code-review','to':'testing','evidence':dict(E,kind='code-review',result='approve')}]
  with self.assertRaisesRegex(policy.PolicyError,'QA_RUN_REUSED'):policy.evidence_gate(task,'merge-ready',e,p)

 def test_qa_retest_keeps_approved_same_candidate_review(self):
  requirements=policy.intake_issue(I,P)
  reviewed=dict(E,kind='code-review',result='approve',head='a'*40,pr=2)
  e=copy.deepcopy(E);e.update(kind='qa',result='pass',head='a'*40,pr=2,run_id='newrun123',environment={'runtime':'python','build_mode':'test','target':'fixture'},tests=[{'argv':['npm','test'],'exit_code':0,'log_url':'https://example.test/log'}]);e['acceptance']['AC-1']['result']='verified'
  task={'state':'testing','requirements':requirements,'history':[{'from':'code-review','to':'testing','evidence':reviewed},{'from':'testing','to':'merge-ready','evidence':dict(e,run_id='oldrun123')},{'from':'merge-ready','to':'testing','evidence':{'summary':'base moved','pr':2,'head':'a'*40}}]}
  policy.evidence_gate(task,'merge-ready',e,P)
  with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_CHAIN'):policy.evidence_gate(task,'merge-ready',dict(e,head='b'*40),P)
  task['history'].append({'from':'code-review','to':'ready','evidence':dict(reviewed,result='changes_requested')})
  with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_CHAIN'):policy.evidence_gate(task,'merge-ready',e,P)
 def test_recovery_cannot_use_unsuccessful_development(self):
  task={'state':'code-review','requirements':policy.intake_issue(I,P),'history':[{'from':'ready','to':'blocked','evidence':dict(E,kind='development',result='blocked')}]}
  e=copy.deepcopy(E);e.update(kind='code-review',result='approve');e['acceptance']['AC-1']['result']='reviewed'
  with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_CHAIN'):policy.evidence_gate(task,'testing',e,P)

 def test_rejected_design_cannot_reuse_older_approval_after_recovery(self):
  req=policy.intake_issue(I,P)
  approval=dict(E,kind='design-review',result='approve')
  task={'state':'ready','requirements':req,'history':[{'from':'design-review','to':'ready','evidence':approval},{'from':'design-review','to':'new','evidence':dict(approval,result='changes_requested')}]}
  e=copy.deepcopy(E);e.update(kind='development');e['acceptance']['AC-1']['result']='implemented'
  with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_CHAIN'):policy.evidence_gate(task,'code-review',e,P)

class StorageAndReleaseTests(unittest.TestCase):
 def test_external_release_without_issue_and_failed_artifact(self):
  with tempfile.TemporaryDirectory() as d:
   record=evidence_store.new_run(d,'o/r',None,'release');self.assertIsNone(record['issue'])
   with self.assertRaises(policy.PolicyError):evidence_store.new_run(d,'o/r',None,'qa')
  example=json.loads((Path(__file__).resolve().parents[1]/'skills/aegis-release/examples/record.json').read_text())
  release_record.validate(example)
  release_record.validate(dict(example,status='failed',diagnostics='Build exited 1 before artifact creation'))
  with self.assertRaises(policy.PolicyError):release_record.validate(dict(example,status='verified'))
  with self.assertRaisesRegex(policy.PolicyError,'RELEASE_WORKFLOW'):release_record.validate(dict(example,execution_mode='aegis'))
 def test_nested_manifest_is_not_excluded_from_integrity(self):
  with tempfile.TemporaryDirectory() as d:
   record=evidence_store.new_run(d,'o/r',1,'qa');path=Path(record['directory']);(path/'nested').mkdir();(path/'nested/manifest.json').write_text('{}')
   evidence_store.seal(path,{'candidate_sha':'a'*40,'environment':{'runtime':'node','build_mode':'test','target':'local'}})
   evidence_store.verify(path)
   (path/'nested/manifest.json').write_text('changed')
   with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_CHANGED'):evidence_store.verify(path)
 def test_unique_runs_manifest_and_tamper_detection(self):
  with tempfile.TemporaryDirectory() as d:
   first=evidence_store.new_run(d,'o/r',1,'qa');second=evidence_store.new_run(d,'o/r',1,'qa',first['run_id'])
   self.assertNotEqual(first['run_id'],second['run_id'])
   directory=Path(first['directory']);(directory/'test.log').write_text('observed output')
   metadata={'candidate_sha':'a'*40,'environment':{'runtime':'node22','build_mode':'pages','target':'local preview'}}
   evidence_store.seal(directory,metadata);self.assertEqual(evidence_store.verify(directory)['status'],'integrity_verified')
   with self.assertRaises(FileExistsError):evidence_store.seal(directory,metadata)
   (directory/'test.log').write_text('replaced result')
   with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_CHANGED'):evidence_store.verify(directory)
 def test_symlink_evidence_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=evidence_store.new_run(d,'o/r',1,'qa');path=Path(r['directory']);(path/'external').symlink_to('/etc/hosts')
   with self.assertRaisesRegex(policy.PolicyError,'EVIDENCE_SYMLINK'):evidence_store.seal(path,{'candidate_sha':'a'*40,'environment':{'runtime':'node','build_mode':'test','target':'local'}})
 def test_release_build_is_not_live_verification(self):
  record={'execution_mode':'external','schema':'aegis-release/v1','source_repo':'o/source','artifact_repo':'o/pages','source_sha':'a'*40,'artifact_commit':'b'*40,'artifact_digest':'sha256:'+'c'*64,'status':'pending','authorization_ref':'user request in current task','environment':'production','build_mode':'pages','run_id':'r12345678','rollback':'revert artifact commit','site_url':'https://example.test/site/'}
  self.assertEqual(release_record.validate(record)['release_status'],'pending')
  with self.assertRaises(policy.PolicyError):release_record.validate(dict(record,status='verified'))
  record.update(status='verified',deployment_url='https://example.test/run/1',deployment_status='success',observed_source_sha='a'*40,observed_artifact_digest='sha256:'+'c'*64,smoke={'result':'pass','target':record['site_url'],'evidence_url':'https://example.test/evidence'})
  release_record.validate(record)
  with self.assertRaisesRegex(policy.PolicyError,'RELEASE_STALE'):release_record.validate(dict(record,observed_source_sha='d'*40))

if __name__=='__main__':unittest.main()
