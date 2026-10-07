import sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/aegis/scripts'))
import merge_gate as m
class MergeGate(unittest.TestCase):
 def setUp(self):
  self.e={'pr':3,'head':'h','base':'b'};self.task={'state':'merge-ready','history':[{'evidence':self.e}]}
  self.store=Mock(repo='o/r');self.store.read.return_value=({'revision':1,'tasks':{'1':self.task}},'sha')
  self.p={'merge_mode':'merge-queue','default_branch':'main','required_checks':['test']}
  self.pr={'state':'open','draft':False,'head':{'sha':'h'},'base':{'sha':'b'}}
  self.rules=[{'type':'merge_queue'},{'type':'required_status_checks','parameters':{'required_status_checks':[{'context':'test'}]}},{'type':'pull_request','parameters':{'required_approving_review_count':1}}]
 def run_queue(self):
  def api(repo,path):return self.pr if path.startswith('/pulls') else self.rules
  with patch.object(m.policy,'load_policy',return_value=self.p),patch.object(m.policy,'remote_gate'):
   return m.enqueue(self.store,'qa','token',1,api,lambda *a:{'role':'qa'})
 def test_manual_never_invokes_gh(self):
  self.p['merge_mode']='manual'
  with patch.object(m.subprocess,'run') as run,self.assertRaisesRegex(ValueError,'MERGE_MANUAL'):self.run_queue()
  run.assert_not_called();self.store.write.assert_not_called()
 def test_missing_rules_never_writes(self):
  self.rules=[]
  with self.assertRaisesRegex(ValueError,'MERGE_RULES'):self.run_queue()
  self.store.write.assert_not_called()
 def test_stale_head_never_writes(self):
  self.pr['head']['sha']='changed'
  with self.assertRaisesRegex(ValueError,'MERGE_STALE'):self.run_queue()
  self.store.write.assert_not_called()
 def test_intent_precedes_queue_and_no_admin_bypass(self):
  def run(cmd,**kw):
   self.store.write.assert_called_once();self.assertNotIn('--admin',cmd);self.assertIn('--match-head-commit',cmd);return Mock(returncode=0)
  with patch.object(m.subprocess,'run',side_effect=run):self.assertEqual(self.run_queue()['status'],'queued')
  self.assertEqual(self.task['state'],'merge-ready')
 def test_attempt_is_never_replayed(self):
  self.task['merge_request']={'status':'sending'}
  with patch.object(m.subprocess,'run') as run,self.assertRaisesRegex(ValueError,'MERGE_REQUEST_EXISTS'):self.run_queue()
  run.assert_not_called()
