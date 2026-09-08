"""SSH-only request broker. Slack credentials stay on the VPS."""
import fcntl
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from dotenv import dotenv_values

from settings import load
config = load()
QUEUE = Path(config['queue_dir'])
PROFILES = {name: Path(value) for name, value in config['profiles'].items()}


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data))
    temp.replace(path)


def post(job, text):
    token = dotenv_values(PROFILES[job['bot']] / '.env')['SLACK_BOT_TOKEN']
    body = dict(channel=job['channel'], text=text[:3800], mrkdwn=False, unfurl_links=False, unfurl_media=False)
    if re.fullmatch(r'\d+\.\d+', job.get('thread', '')):
        body['thread_ts'] = job['thread']
    req = urllib.request.Request('https://slack.com/api/chat.postMessage', data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if not result.get('ok'):
        raise RuntimeError('Slack delivery failed: ' + result.get('error', 'unknown'))


def main():
    QUEUE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (QUEUE / 'broker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if sys.argv[1] == 'next':
            for p in sorted(QUEUE.glob('*.json')):
                job = json.loads(p.read_text())
                if job.get('status') != 'queued':
                    continue
                if job.get('user_id') != config['owner_id'] or job.get('bot') not in PROFILES:
                    continue
                job.update(status='running', started_at=time.time())
                save(p, job)
                print(json.dumps(job))
                return
            print('null')
        elif sys.argv[1] in ('started', 'finish'):
            payload = json.load(sys.stdin)
            if not re.fullmatch(r'[a-f0-9]{64}', payload['id']):
                raise ValueError('Invalid request ID')
            p = QUEUE / (payload['id'] + '.json')
            job = json.loads(p.read_text())
            if job['status'] == 'completed':
                print('already completed')
                return
            if job['status'] != 'running':
                raise ValueError('Request not running')
            if sys.argv[1] == 'started':
                post(job, 'Your Mac has picked up this request. Release Shepherd is collecting completed application branches now. I will post the verified outcome here.')
                print('started')
                return
            job.update(status='delivery_pending', result=payload['message'])
            save(p, job)
            post(job, payload['message'])
            job.update(status='completed', completed_at=time.time())
            save(p, job)
            print('completed')
        else:
            raise ValueError('Unknown operation')


if __name__ == '__main__':
    main()
