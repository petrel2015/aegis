"""Small shared primitives for append-only release observations and bounded effects."""
import json
import os
from pathlib import Path
import subprocess
import uuid
from datetime import datetime, timezone
from release_pipeline import require, digest, command


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value, exclusive=False):
    path = Path(path)
    if exclusive:
        with path.open('x') as stream:
            json.dump(value, stream, indent=2)
    else:
        temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(value, indent=2) + '\n')
        os.replace(temporary, path)


def fingerprint(path):
    return 'sha256:' + digest(Path(path).read_bytes())


def reserve(output, schema, **fields):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = dict(schema=schema, operation_id=uuid.uuid4().hex,
                  recorded_at=now(), status='reserved', **fields)
    write(output / 'operation.json', record, exclusive=True)
    return record


def disjoint(first, second):
    a, b = Path(first).resolve(), Path(second).resolve()
    require(not a.is_relative_to(b) and not b.is_relative_to(a), 'PATH_OVERLAP')


def guard_release_output(output, plan, record_directories=True):
    """Reject aliases/overlap before creating any release record directory."""
    for key in ('source', 'build_output', 'artifact'):
        disjoint(output, plan[key])
    if record_directories:
        for key, path in plan.items():
            if key.endswith('_record') or key == 'release_manifest':
                disjoint(output, Path(path).parent)


def repo_origin(source, repo):
    origin = command(['git', 'remote', 'get-url', 'origin'], source)
    require(origin.rstrip('/').removesuffix('.git') in
            ('https://github.com/' + repo, 'git@github.com:' + repo), 'SOURCE_REPO_MISMATCH')
    return origin


def api(endpoint, payload=None):
    argv = ['gh', 'api', endpoint]
    if payload is not None:
        result = subprocess.run(argv + ['--method', 'POST', '--input', '-'],
                                input=json.dumps(payload), capture_output=True, text=True, timeout=60)
        require(result.returncode == 0, 'GH_EFFECT_UNKNOWN: reconcile original operation')
        return json.loads(result.stdout)
    return json.loads(command(argv))


def pages(endpoint):
    # Failure, truncation, or malformed pages never becomes an empty search result.
    result = json.loads(command(['gh', 'api', '--paginate', '--slurp', endpoint], timeout=60))
    require(isinstance(result, list) and all(isinstance(page, list) for page in result), 'PAGINATION_INCOMPLETE')
    return [item for page in result for item in page]
