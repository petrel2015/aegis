import sys, json, os, subprocess, pathlib
root=pathlib.Path(sys.argv[2])
cli=sys.argv[1]
os.environ['PATH']=str(root)+os.pathsep+os.environ['PATH'];os.environ['FAKE_GH_ROOT']=str(root)
state={'version':1,'revision':0,'tasks':{},'qa':None,'last_operation':None}
(root/'state.json').write_text(json.dumps(state))
meta={'issue_state':'open','head':'a'*40,'base':'b'*40};
def save(): (root/'meta.json').write_text(json.dumps(meta))
save(); results=[]; tok=None
(root/'policy.json').write_text(json.dumps({'version':1,'intake_label':'aegis:intake',
 'trusted_issue_authors':['owner'],'max_issues_per_run':1,'max_rework_rounds':3,
 'max_run_minutes':30,'merge_mode':'manual','test_commands':[['python3','-m','unittest']],
 'required_checks':['test'],'review_mode':'agent-attestation'}))
body='\n'.join('### '+h+'\n'+v for h,v in [('Priority','P2'),('Background','Test feature'),
 ('Expected benefit','Useful change'),('Scope and exclusions','Small scope'),
 ('Acceptance criteria','AC-1: verified outcome'),('Alternatives and compatibility','No migration')])
(root/'issue.json').write_text(json.dumps({'number':1,'title':'[feature] Test','body':body,'user':{'login':'owner'},'labels':[]}))
def run(*args,ok=True):
 p=subprocess.run([sys.executable,cli,'--repo','test/project',*args],capture_output=True,text=True)
 result=json.loads(p.stdout if p.returncode==0 else p.stderr.strip().splitlines()[-1]);results.append({'args':args,'exit':p.returncode,'result':result})
 assert (p.returncode==0)==ok,(args,p.stdout,p.stderr)
 if p.returncode==0 and 'sync' in result: assert result['sync']['status']=='synced',result['sync']
 return result

def claim(role,actor):return run('claim','--issue','1','--actor',actor,'--role',role)['token']
def finish(actor,token,target,extra=None,ok=True):
 stage=json.loads((root/'state.json').read_text())['tasks']['1']['state']
 e={'summary':'offline fixture','url':'https://example.test/fixture','pr':2,'head':meta['head']};e.update({'schema':'aegis-evidence/v1','design_ref':'sha256:'+'e'*64,
 'acceptance':{'AC-1':{'result':'pass','evidence':'https://example.test/log'}},
 'kind':{'new':'design','design-review':'design-review','ready':'development','code-review':'code-review','testing':'qa','merge-ready':'merge'}[stage],
 'result':'approve' if stage in ('design-review','code-review') else 'pass',
 'reviewed_head':meta['head'], 'tests':[{'argv':['python3','-m','unittest'],'exit_code':0,'log_url':'https://example.test/log'}]})
 if target in ('blocked','ready','new') and stage!='design-review': e['result']='fail'
 e.update(extra or {});(root/'evidence.json').write_text(json.dumps(e))
 return run('finish','--issue','1','--actor',actor,'--token',token,'--to',target,'--evidence',str(root/'evidence.json'),ok=ok)
run('register','--issue','1','--actor','machine-a')
for role,actor,target in [('planner','machine-a','design-review'),('reviewer','machine-b','ready'),('developer','worker-a','code-review'),('reviewer','machine-b','testing')]:
 t=claim(role,actor);finish(actor,t,target)
t=claim('qa','machine-a'); meta['head']='d'*40;save(); finish('machine-a',t,'merge-ready',{'result':'pass','base':meta['base'],'tested_commit':'c'*40},ok=False)
finish('machine-a',t,'ready');t=claim('developer','worker-a');finish('worker-a',t,'code-review');t=claim('reviewer','machine-b');finish('machine-b',t,'testing')
t=claim('qa','machine-a');oldbase=meta['base'];meta['base']='e'*40;save();finish('machine-a',t,'merge-ready',{'result':'pass','base':oldbase,'tested_commit':'c'*40},ok=False)
finish('machine-a',t,'merge-ready',{'result':'pass','base':meta['base'],'tested_commit':'f'*40})
meta['issue_state']='closed';meta['merged']=True;save()
t=claim('qa','machine-a');finish('machine-a',t,'done')
ui=json.loads((root/'ui.json').read_text())
assert set(ui['labels'])=={'bug','aegis:intake','aegis:done'},ui
events=json.loads((root/'state.json').read_text())['tasks']['1']['issue_events']
assert len(ui['comments'])==len(events) and all(e['delivery']=='sent' for e in events)
assert len({c['body'].splitlines()[0] for c in ui['comments']})==len(events)
(root/'results.json').write_text(json.dumps(results,indent=2));print('PASS',len(results),'CLI invocations; evidence:',root/'results.json')
