#!/usr/bin/env python3
"""Unique local evidence directories and immutable integrity manifests. No network."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid
import policy


def new_run(root, repo, issue, role, retry_of=None):
    policy.require((type(issue) is int and issue>0) or (issue is None and role=='release'),'RUN_ISSUE: positive Issue required except optional for release')
    policy.require(role in ('planner','developer','reviewer','qa','release'),'RUN_ROLE: invalid role')
    policy.require(re.fullmatch(r'[\w.-]+/[\w.-]+',repo),'RUN_REPO: OWNER/REPO required')
    policy.require(retry_of is None or re.fullmatch(r'[a-f0-9]{32}',retry_of),'RUN_RETRY: original run UUID hex required')
    run_id=uuid.uuid4().hex
    directory=Path(root)/run_id;directory.mkdir(parents=True,exist_ok=False)
    data={'schema':'aegis-run/v1','run_id':run_id,'repo':repo,'issue':issue,'role':role,'retry_of':retry_of}
    with (directory/'run.json').open('x') as f:json.dump(data,f,indent=2)
    return dict(data,directory=str(directory.resolve()))


def seal(directory,metadata):
    directory=Path(directory)
    policy.require(not directory.is_symlink(),'EVIDENCE_SYMLINK: run directory must not be a symlink')
    policy.require(not (directory/'run.json').is_symlink(),'EVIDENCE_SYMLINK: run identity must not be a symlink')
    identity=json.loads((directory/'run.json').read_text())
    policy.require(identity.get('run_id')==directory.name,'RUN_ID: directory must match run identity')
    policy.require(re.fullmatch(r'[0-9a-f]{40}',metadata.get('candidate_sha','')),'RUN_CANDIDATE: exact tested commit required')
    policy.require(isinstance(metadata.get('environment'),dict) and all(metadata['environment'].get(k) for k in ('runtime','build_mode','target')),'RUN_ENVIRONMENT: runtime, build_mode and target required')
    files={}
    for file in sorted(directory.rglob('*')):
        policy.require(not file.is_symlink(),'EVIDENCE_SYMLINK: evidence must be self-contained')
        policy.require(not any(part in ('.git','node_modules','.ssh') or part.startswith('.env') for part in file.relative_to(directory).parts),'EVIDENCE_PRIVATE_PATH: collect explicit logs/screenshots/results, not repositories or dependency trees')
        if file.is_file():files[file.relative_to(directory).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    policy.require(len(files)>1,'EVIDENCE_EMPTY: add actual logs/screenshots before sealing')
    result={'schema':'aegis-manifest/v1','run':identity,'metadata':metadata,'files':files}
    with (directory/'manifest.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
    return result


def verify(directory):
    directory=Path(directory)
    policy.require(not directory.is_symlink() and not (directory/'manifest.json').is_symlink(),'EVIDENCE_SYMLINK')
    manifest=json.loads((directory/'manifest.json').read_text());actual={}
    for file in directory.rglob('*'):
        policy.require(not file.is_symlink(),'EVIDENCE_SYMLINK')
        policy.require(not any(part in ('.git','node_modules','.ssh') or part.startswith('.env') for part in file.relative_to(directory).parts),'EVIDENCE_PRIVATE_PATH')
        if file.is_file() and file.relative_to(directory).as_posix()!='manifest.json':actual[file.relative_to(directory).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    policy.require(actual==manifest['files'],'EVIDENCE_CHANGED: missing, added or modified file')
    return {'status':'integrity_verified','run_id':manifest['run']['run_id'],'proof':'local file integrity only; not semantic acceptance or remote publication'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    new=sub.add_parser('new');new.add_argument('--root',type=Path,default=Path('.aegis-local/evidence'))
    new.add_argument('--repo',required=True);new.add_argument('--issue',type=int)
    new.add_argument('--role',required=True);new.add_argument('--retry-of')
    sealing=sub.add_parser('seal');sealing.add_argument('directory',type=Path);sealing.add_argument('--metadata',type=Path,required=True)
    check=sub.add_parser('verify');check.add_argument('directory',type=Path)
    args=p.parse_args()
    if args.command=='new':result=new_run(args.root,args.repo,args.issue,args.role,args.retry_of)
    elif args.command=='seal':result=seal(args.directory,json.loads(args.metadata.read_text()))
    else:result=verify(args.directory)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError) as e:raise SystemExit(str(e))
