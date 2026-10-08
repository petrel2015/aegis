import sys,time,signal,subprocess,unittest,tempfile,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/aegis/scripts'))
import run_once as r
class Guards(unittest.TestCase):
 def test_lost_claim_is_not_grace(self):
  cfg=SimpleNamespace(repo='o/r',actor='a')
  for lease in [None,{'actor':'other','token':'new'},{'actor':'a','token':'t','expires':9999}]:
   call=lambda *a,**kw:{'tasks':{'1':{'state':'ready','lease':lease}}}
   self.assertTrue(r.handle_heartbeat_failure(cfg,1,'t',100,200,call,None,'ready')['terminate'])
 def test_confirmed_handoff_grants_only_bounded_exit(self):
  cfg=SimpleNamespace(repo='o/r',actor='a')
  call=lambda *a,**kw:{'tasks':{'1':{'state':'code-review','lease':None}}}
  result=r.handle_heartbeat_failure(cfg,1,'t',100,150,call,None,'ready')
  self.assertFalse(result['terminate']);self.assertEqual(result['lease_floor'],150)
 def test_completed_requires_success_and_own_handoff(self):
  cfg=SimpleNamespace(repo='o/r',actor='a')
  task={'state':'code-review','lease':None,'history':[{'from':'ready','actor':'a','claim_token':'t'}]}
  call=lambda *a,**kw:{'tasks':{'1':task}}
  self.assertEqual(r.inspect_after_exit(cfg,1,'t','ready',0,call,None,0)['status'],'completed')
  self.assertEqual(r.inspect_after_exit(cfg,1,'t','ready',1,call,None,0)['status'],'incomplete')
  task['history'][0]['actor']='other'
  self.assertEqual(r.inspect_after_exit(cfg,1,'t','ready',0,call,None,0)['status'],'incomplete')
 def test_release_requires_matching_token_and_success(self):
  cfg=SimpleNamespace(repo='o/r',actor='a');calls=[]
  def call(repo,args,**kw):
   calls.append(args[0]);return {'tasks':{'1':{'state':'ready','lease':{'actor':'a','token':'t'}}}}
  result=r.inspect_after_exit(cfg,1,'t','ready',0,call,None)
  self.assertTrue(result['released']);self.assertEqual(calls,['status','release'])
 def test_tree_killed_even_when_leader_already_exited(self):
  proc=Mock(pid=123);proc.wait.return_value=0
  with patch.object(r.os,'killpg') as kill:
   r.kill_tree(proc)
  self.assertEqual([x.args[1] for x in kill.call_args_list],[signal.SIGTERM,signal.SIGKILL])
 def test_planner_intake_passes_actor(self):
  from tests.test_runner import make_cfg,scripted_call
  with tempfile.TemporaryDirectory() as tmp:
   cfg=make_cfg(tmp,role='planner');calls=[]
   def call(repo,args,**kw):
    calls.append(args)
    return {'policy':{'max_run_minutes':1,'max_issues_per_run':1}} if args[0]=='preflight' else {'tasks':[]}
   r.run_once(cfg,call=call)
   self.assertIn(['intake','--actor','dev-1'],calls)

 def test_old_round_does_not_complete_new_claim(self):
  cfg=SimpleNamespace(repo='o/r',actor='a')
  task={'state':'code-review','lease':None,'history':[{'from':'ready','actor':'a','claim_token':'old'},{'from':'code-review','actor':'reviewer'},{'from':'ready','actor':'other','claim_token':'new'}]}
  call=lambda *a,**kw:{'tasks':{'1':task}}
  self.assertEqual(r.inspect_after_exit(cfg,1,'current','ready',0,call,None,2)['status'],'incomplete')
 def test_coord_timeout_keeps_attempt_and_kills_group(self):
  with tempfile.TemporaryDirectory() as tmp:
   script=Path(tmp)/'cli.py';script.write_text("import sys,json,time\nprint(json.dumps({'phase':'attempt','operation':'op','token':'tok'}),file=sys.stderr,flush=True)\ntime.sleep(60)\n")
   with patch.object(r,'AEGIS',script):
    with self.assertRaises(r.RemoteUnknown) as caught:r.call_aegis('o/r',['claim'],timeout=.15)
   self.assertEqual(caught.exception.attempt['token'],'tok')

class ContinuationGuardTests(unittest.TestCase):
 def test_changed_requirements_never_claim_or_spawn(self):
  from tests.test_runner import make_cfg
  with tempfile.TemporaryDirectory() as tmp:
   cfg=make_cfg(tmp);calls=[]
   def call(repo,args,**kwargs):
    calls.append(args[0])
    return {'preflight':{'policy':{'max_run_minutes':1,'max_issues_per_run':1}},'scan':{'tasks':[{'issue':1}]},'resume':{'status':'needs_attention','diagnostics':['REQUIREMENTS_CHANGED']}}[args[0]]
   spawn=Mock();result=r.run_once(cfg,call=call,spawn=spawn)
   self.assertEqual(result['status'],'blocked');self.assertNotIn('claim',calls);spawn.assert_not_called()
