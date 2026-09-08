"""Runs over SSH. Reads Paperclip and GitHub; never writes to either."""
import concurrent.futures
import datetime
import json
import re
import subprocess
import sys
import urllib.request


def scan(config, previous):
    def api(path):
        with urllib.request.urlopen(config['paperclip_url'] + '/api/' + path, timeout=60) as r:
            return json.load(r)

    repositories = []
    for group in config['groups']:
        for source in group['sources']:
            proc = subprocess.run(['git', '-C', source['path'], 'ls-remote', '--heads',
                                   'https://github.com/' + source['repo'] + '.git'],
                                  capture_output=True, text=True, timeout=120)
            if proc.returncode:
                raise RuntimeError('Cannot read GitHub branches for ' + source['repo'])
            refs = {line.split()[1].removeprefix('refs/heads/'): line.split()[0]
                    for line in proc.stdout.splitlines() if line.strip()}
            repositories.append(dict(source, group=group['name'], branches=refs))

    branches = sorted({b for r in repositories for b in r['branches'] if b not in ('main', 'master', 'develop')}, key=len, reverse=True)
    branch_pattern = re.compile(r'(?<![\w/.-])(' + '|'.join(re.escape(b) for b in branches) + r')(?![\w/.-])') if branches else None
    # Only retain code references and metadata, never raw task/comment bodies.
    old = {i['id']: i for i in previous.get('issues', [])}
    issues, offset, seen = [], 0, set()
    while True:
        page = api('companies/' + config['company_id'] + '/issues?limit=200&offset=' + str(offset))
        if not isinstance(page, list):
            raise RuntimeError('Unexpected issue pagination shape')
        if not page:
            break
        ids = {i['id'] for i in page}
        if seen.intersection(ids):
            raise RuntimeError('Pagination repeated issues; refusing incomplete inventory')
        seen.update(ids)
        issues.extend(page)
        offset += len(page)
    inventory_key = json.dumps([(r['repo'], sorted(r['branches'])) for r in repositories], sort_keys=True)

    def evidence(issue):
        cached = old.get(issue['id'])
        stamp = [issue.get('updatedAt'), issue.get('lastActivityAt')]
        if cached and cached.get('stamp') == stamp and previous.get('inventory_key') == inventory_key:
            return cached
        matches = {}
        if issue.get('status') not in ('cancelled',):
            detail = api('issues/' + issue['id']) if issue.get('descriptionTruncated') else issue
            comments = api('issues/' + issue['id'] + '/comments')
            if not isinstance(comments, list):
                raise RuntimeError('Unexpected comment response')
            texts = [('description', detail.get('description') or '')] + [(c['id'], c.get('body') or '') for c in comments]
            for cid, body in texts:
                if branch_pattern:
                    for match in branch_pattern.finditer(body):
                        matches.setdefault(match.group(), []).append(cid)
        return {'id': issue['id'], 'identifier': issue['identifier'], 'title': issue['title'],
                'status': issue['status'], 'stamp': stamp,
                'completed_at': issue.get('completedAt'),
                'references': {b: sorted(set(ids)) for b, ids in matches.items()}}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        extracted = list(pool.map(evidence, issues))
    return {'scanned_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'repositories': repositories, 'issues': extracted, 'inventory_key': inventory_key,
            'complete': True}


if __name__ == '__main__':
    payload = json.loads(sys.stdin.readline())
    print(json.dumps(scan(payload['config'], payload.get('previous', {}))))
