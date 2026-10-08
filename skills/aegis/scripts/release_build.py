"""Fresh source-bound builds; ignored dependencies are explicitly not hermetic proof."""
import os
from pathlib import Path
import platform
import signal
import subprocess
import time
import release_pipeline as pipeline
from release_support import command, disjoint, fingerprint, read, repo_origin, require, reserve, write


def snapshot(source, repo):
    require(Path(command(['git', 'rev-parse', '--show-toplevel'], source)).resolve() == Path(source).resolve(), 'SOURCE_ROOT')
    origin = repo_origin(source, repo)
    require(not command(['git', 'status', '--porcelain', '--untracked-files=all'], source), 'SOURCE_DIRTY')
    return dict(source_sha=command(['git', 'rev-parse', 'HEAD'], source),
                source_tree=command(['git', 'rev-parse', 'HEAD^{tree}'], source), origin=origin)


def build(source, build_output, output, repo, argv, mode, timeout=600):
    source, build_output, output = map(lambda p: Path(p).resolve(), (source, build_output, output))
    disjoint(source, output)
    disjoint(build_output, output)
    require(not source.is_relative_to(build_output), 'BUILD_OVERLAP')
    require(not build_output.exists(), 'BUILD_STALE_OUTPUT')
    require(isinstance(argv, list) and argv and all(isinstance(a, str) and a for a in argv), 'BUILD_ARGV')
    require(mode.strip() and timeout > 0, 'BUILD_MODE_OR_TIMEOUT')
    before = snapshot(source, repo)
    result = reserve(output, 'aegis-build/v1', source_repo=repo, source=str(source),
                     build_output=str(build_output), argv=argv, build_mode=mode,
                     runtime=platform.python_version(), **before)
    process = None
    started = time.monotonic()
    try:
        environment = dict(os.environ, AEGIS_BUILD_OUTPUT=str(build_output))
        process = subprocess.Popen(argv, cwd=source, env=environment, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=(os.name != 'nt'))
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=15)
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            stdout, stderr = process.communicate(timeout=15)
            (output / 'stdout.log').write_bytes(stdout)
            (output / 'stderr.log').write_bytes(stderr)
            raise ValueError('BUILD_TIMEOUT: process group stopped; retain attempt')
        (output / 'stdout.log').write_bytes(stdout)
        (output / 'stderr.log').write_bytes(stderr)
        result['exit_code'] = process.returncode
        require(process.returncode == 0, 'BUILD_FAILED')
        require(snapshot(source, repo) == before, 'SOURCE_DRIFT')
        files = pipeline.inventory(build_output)
        require(files, 'BUILD_EMPTY')
        result.update(status='built', files={n: pipeline.digest(b) for n, b in files.items()},
                      limitations='Observed source and output binding; ignored dependencies/environment are not hermetic or hostile-writer attestation.')
    except Exception as error:
        result.update(status='failed', diagnostics=str(error))
        raise
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        write(output / 'operation.json', result)
    return result


def validate(path):
    record = read(path)
    require(record.get('schema') == 'aegis-build/v1' and record.get('status') == 'built' and record.get('exit_code') == 0, 'BUILD_UNVERIFIED')
    actual = snapshot(record['source'], record['source_repo'])
    require(all(actual[k] == record[k] for k in actual), 'SOURCE_DRIFT')
    require({n: pipeline.digest(b) for n, b in pipeline.inventory(record['build_output']).items()} == record['files'], 'BUILD_OUTPUT_CHANGED')
    return record


def prepare(build_record, previous, output, site, allow_remove=(), protected=()):
    record = validate(build_record)
    disjoint(Path(build_record).parent, output)
    disjoint(record['source'], output)
    result = pipeline.prepare(record['build_output'], previous, output, record['source_sha'], site, allow_remove, protected)
    result['build_binding'] = {'record_digest': fingerprint(build_record), 'operation_id': record['operation_id'],
                               'source_repo': record['source_repo'], 'build_mode': record['build_mode']}
    write(Path(output) / 'artifact.json', result)
    return result
