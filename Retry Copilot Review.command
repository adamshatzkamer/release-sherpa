#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
python3 - <<'PY'
from pathlib import Path
import shepherd
config = shepherd.read(shepherd.ROOT / 'config.json')
if not config:
    raise SystemExit('Configure config.json first.')
enabled = {group['name'] for group in config['groups'] if group.get('auto_prepare', True)}
latest = {}
for path in sorted((shepherd.STATE / 'runs').glob('*/manifest.json')):
    manifest = shepherd.read(path)
    if manifest['group'] in enabled and manifest.get('status') in ('prepared', 'awaiting_copilot', 'blocked'):
        latest[manifest['group']] = path.parent
for directory in latest.values():
    shepherd.handoff(config, directory, retry=True)
print('Pending reviews routed according to verified provider availability. Copilot quota status is not reset by retry.')
PY
