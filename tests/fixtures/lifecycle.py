import sys, json, os, subprocess, pathlib
root=pathlib.Path(sys.argv[2])
cli=sys.argv[1]
os.environ['PATH']=str(root)+os.pathsep+os.environ['PATH'];os.environ['FAKE_GH_ROOT']=str(root)
state={'version':1,'revision':0,'tasks':{},'qa':None,'last_operation':None}
(root/'state.json').write_text(json.dumps(state))
meta={'issue_state':'open','head':'a'*40,'base':'b'*40};
def save(): (root/'meta.json').write_text(json.dumps(meta))
save(); results=[]; tok=None
def run(*args,ok=True):
 p=subprocess.run([sys.executable,cli,'--repo','test/project',*args],capture_output=True,text=True)
 result=json.loads(p.stdout if p.returncode==0 else p.stderr.strip().splitlines()[-1]);results.append({'args':args,'exit':p.returncode,'result':result})
 assert (p.returncode==0)==ok,(args,p.stdout,p.stderr)
 return result

def claim(role,actor):return run('claim','--issue','1','--actor',actor,'--role',role)['token']
def finish(actor,token,target,extra=None,ok=True):
 e={'summary':'offline fixture','url':'https://example.test/fixture','pr':2,'head':meta['head']};e.update(extra or {});(root/'evidence.json').write_text(json.dumps(e))
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
(root/'results.json').write_text(json.dumps(results,indent=2));print('PASS',len(results),'CLI invocations; evidence:',root/'results.json')
