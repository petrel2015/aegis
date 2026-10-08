#!/usr/bin/env python3
"""Reserve and reconcile an append-only Issue/PR comment before one bounded POST."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import uuid
from release_support import api, pages, read, require, reserve, write
from release_pipeline import digest


def matches(record, comments):
    marker = '<!-- aegis-report:' + record['record_id'] + ' -->'
    found = [comment for comment in comments if marker in (comment.get('body') or '')]
    require(len(found) <= 1, 'REPORT_DUPLICATE: reconcile existing comments')
    if found:
        require(found[0]['body'] == record['body'], 'REPORT_CONTENT_MISMATCH')
        require(found[0].get('html_url', '').startswith(f'https://github.com/{record["repo"]}/'), 'REPORT_DESTINATION_MISMATCH')
    return found


def publish(body, output, repo, issue, record_id, authorization):
    require(re.fullmatch(r'[\w.-]+/[\w.-]+', repo), 'REPO')
    require(type(issue) is int and issue > 0, 'ISSUE')
    require(str(uuid.UUID(record_id)) == record_id, 'RECORD_ID')
    require(authorization.strip() and body.strip(), 'REPORT_AUTHORIZATION_OR_BODY')
    marker = '<!-- aegis-report:' + record_id + ' -->'
    require('<!-- aegis-report:' not in body, 'REPORT_MARKER: helper adds marker')
    body = body.rstrip() + '\n\n' + marker
    result = reserve(output, 'aegis-report-publication/v1', repo=repo, issue=issue,
                     record_id=record_id, authorization_ref=authorization, body=body,
                     body_digest='sha256:' + digest(body.encode()))
    endpoint = f'repos/{repo}/issues/{issue}/comments'
    try:
        found = matches(result, pages(endpoint + '?per_page=100'))
        if found:
            result.update(status='published', comment_id=found[0]['id'], url=found[0]['html_url'])
        else:
            result['status'] = 'remote_unknown'
            write(Path(output) / 'operation.json', result)
            comment = api(endpoint, {'body': body})  # one POST; no automatic retries
            require(comment.get('body') == body and comment.get('html_url', '').startswith(f'https://github.com/{repo}/'), 'REPORT_RESPONSE_MISMATCH')
            result.update(status='published', comment_id=comment['id'], url=comment['html_url'])
    except Exception as error:
        result.update(status='remote_unknown', diagnostics=str(error))
        raise
    finally:
        write(Path(output) / 'operation.json', result)
    return result


def resume(output):
    result = read(Path(output) / 'operation.json')
    require(result.get('schema') == 'aegis-report-publication/v1', 'OPERATION_SCHEMA')
    try:
        found = matches(result, pages(f'repos/{result["repo"]}/issues/{result["issue"]}/comments?per_page=100'))
        if found:
            return dict(result, status='published', comment_id=found[0]['id'], url=found[0]['html_url'], next_action='Use original report; do not repost.')
        return dict(result, status='remote_unknown', next_action='Original report not observed; inspect original request and stopped process before any explicit new attempt.')
    except Exception as error:
        return dict(result, status='remote_unknown', diagnostics=str(error), next_action='Resolve incomplete search; never interpret it as absence.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('publish')
    for key in ('body-file', 'output', 'repo', 'record-id', 'authorization-ref'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--issue', type=int, required=True)
    sub.add_parser('resume').add_argument('--output', required=True)
    a = parser.parse_args()
    result = resume(a.output) if a.action == 'resume' else publish(Path(a.body_file).read_text(), a.output, a.repo, a.issue, a.record_id, a.authorization_ref)
    print(json.dumps(result, indent=2))
    return int(result['status'] != 'published')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
