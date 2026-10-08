import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/aegis/scripts'))
import policy

P={'version':1,'intake_label':'aegis:intake','trusted_issue_authors':['trusted'],
 'test_commands':[['npm','test']],'required_checks':['test'],'max_issues_per_run':1,
 'max_rework_rounds':2,'max_run_minutes':30,'merge_mode':'manual'}
BODY='\n'.join('### '+h+'\n'+v for h,v in [('Priority','P2'),('Background','Need feature'),
 ('Expected benefit','Useful'),('Scope and exclusions','Small'),('Acceptance criteria','AC-1: result\nOutcome: visible result\nCounterexample: only label changed\nVerification: inspect rendered output'),
 ('Alternatives and compatibility','No migration')])
I={'number':1,'state':'open','title':'[feature] A','body':BODY,'user':{'login':'trusted'},'labels':[]}
E={'schema':'aegis-evidence/v2','requirements_version':1,'requirements_digest':policy.requirements_digest(BODY),'summary':'Done','url':'https://example.test/report',
 'acceptance':{'AC-1':{'result':'covered','observation':'Design covers the observable result and negative example','evidence':'https://example.test/log'}},'kind':'design','design_ref':'sha256:'+'a'*64}
class PolicyTests(unittest.TestCase):
 def test_empty_tests_fail_closed(self):
  with self.assertRaises(policy.PolicyError):policy.validate_policy(dict(P,test_commands=[]))
 def test_empty_checks_fail_closed(self):
  with self.assertRaises(policy.PolicyError):policy.validate_policy(dict(P,required_checks=[]))
 def test_reject_boolean_budget(self):
  with self.assertRaises(policy.PolicyError):policy.validate_policy(dict(P,max_run_minutes=True))
 def test_trusted_intake_and_acceptance(self):
  r=policy.intake_issue(I,P);self.assertEqual(r['acceptance_ids'],['AC-1'])
 def test_untrusted_issue_rejected(self):
  with self.assertRaises(policy.PolicyError):policy.intake_issue(dict(I,user={'login':'outsider'}),P)
 def test_maintainer_label_allows_intake(self):
  policy.intake_issue(dict(I,user={'login':'outsider'},labels=[{'name':'aegis:intake'}]),P)
 def test_missing_acceptance_or_duplicate_rejected(self):
  for text in ('Nothing', 'AC-1: a; AC-1: b'):
   with self.assertRaises(policy.PolicyError):policy.intake_issue(dict(I,body=BODY.replace('AC-1: result',text)),P)
 def test_self_dependency_rejected(self):
  with self.assertRaises(policy.PolicyError):policy.intake_issue(dict(I,body=BODY+'\n### Dependencies\n#1'),P)
 def test_dependency_and_rework_gate(self):
  t={'requirements':dict(policy.intake_issue(I,P),dependencies=[2]),'history':[]}
  with self.assertRaises(policy.PolicyError):policy.validate_claim({'tasks':{}},t,P)
  policy.validate_claim({'tasks':{'2':{'state':'done'}}},t,P)
  t['history']=[{'from':'code-review','to':'ready'}]*2
  with self.assertRaises(policy.PolicyError):policy.validate_claim({'tasks':{'2':{'state':'done'}}},t,P)
 def test_acceptance_gate_rejects_missing_and_false_pass(self):
  t={'state':'new','requirements':policy.intake_issue(I,P),'history':[]}
  policy.evidence_gate(t,'design-review',E,P)
  for e in (dict(E,acceptance={}),dict(E,acceptance={'AC-1':{'result':'unverified','evidence':'https://example.test'}})):
   with self.assertRaises(policy.PolicyError):policy.evidence_gate(t,'design-review',e,P)
 def test_blocked_cannot_say_pass(self):
  with self.assertRaises(policy.PolicyError):policy.evidence_gate({'state':'testing'},'blocked',dict(E,result='pass'),P)
 def test_design_review_digest_binding(self):
  t={'state':'design-review','requirements':policy.intake_issue(I,P),'history':[{'from':'new','to':'design-review','evidence':E}]}
  e=copy.deepcopy(E);e.update(kind='design-review',result='approve');e['acceptance']['AC-1']['result']='reviewed'
  policy.evidence_gate(t,'ready',e,P)
  with self.assertRaises(policy.PolicyError):policy.evidence_gate(t,'ready',dict(e,design_ref='sha256:'+'b'*64),P)
 def test_latest_check_must_pass_and_trusted_app(self):
  head='a'*40
  valid={'id':1,'name':'test','head_sha':head,'status':'completed','conclusion':'success','app':{'slug':'github-actions'}}
  policy.required_checks('o/r',head,P,lambda *a:{'check_runs':[valid]})
  for runs in ([],[dict(valid,app={'slug':'other'})],[valid,dict(valid,id=2,conclusion='failure')]):
   with self.assertRaises(policy.PolicyError):policy.required_checks('o/r',head,P,lambda *a:{'check_runs':runs})
 def test_qa_requires_all_commands_and_logs(self):
  t={'state':'testing','requirements':policy.intake_issue(I,P),'history':[{'from':'code-review','to':'testing','evidence':dict(E,kind='code-review',result='approve')}]}
  e=dict(E,kind='qa',result='pass',run_id='a'*32,environment={'runtime':'python','build_mode':'test','target':'local fixture'},acceptance={'AC-1':{'result':'verified','observation':'actual output checked','evidence':'https://example.test/log'}},tests=[{'argv':['npm','test'],'exit_code':0,'log_url':'https://example.test/log'}])
  policy.evidence_gate(t,'merge-ready',e,P)
  with self.assertRaises(policy.PolicyError):policy.evidence_gate(t,'merge-ready',dict(e,tests=[]),P)
if __name__=='__main__':unittest.main()
