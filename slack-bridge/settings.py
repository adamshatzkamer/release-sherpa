"""Load deployment-specific bridge settings; importing this module has no side effects."""
import json
import os
from pathlib import Path


def load():
    filename = Path(os.environ.get('SHEPHERD_BRIDGE_CONFIG', Path(__file__).resolve().parents[1] / 'bridge.local.json'))
    if not filename.is_file():
        raise RuntimeError('Configure bridge.local.json from bridge.example.json before enabling Slack.')
    data = json.loads(filename.read_text())
    for key in ('owner_id', 'group', 'queue_dir', 'bot_id', 'profiles', 'ssh_host', 'remote_python', 'remote_broker'):
        if not data.get(key):
            raise ValueError('Missing bridge setting: ' + key)
    if data['bot_id'] not in data['profiles']:
        raise ValueError('bot_id must identify a configured profile')
    return data
