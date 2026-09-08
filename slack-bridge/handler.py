"""Hermes agent:start hook: accept only an explicit owner Slack request."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

# The hook directory must also contain settings.py.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from settings import load
config = load()
QUEUE = Path(config['queue_dir'])
OWNER = config['owner_id']
PHRASES = {'run release review', 'run release shepherd', 'run release shepherd now'}


def eligible(context):
    message = re.sub(r'<@[A-Z0-9]+(?:\|[^>]+)?>', '', context.get('raw_message', '')).strip().lower().rstrip('.!')
    return (context.get('platform') == 'slack' and context.get('user_id') == OWNER
            and message in PHRASES and re.fullmatch(r'[CDG][A-Z0-9]{8,}', context.get('chat_id', '')))


async def handle(event_type, context):
    if event_type != 'agent:start' or not eligible(context):
        return
    QUEUE.mkdir(mode=0o700, parents=True, exist_ok=True)
    bot = config['bot_id']
    # Deduplicate by the actual Slack message, independent of retries or time.
    message_id = context.get('message_id')
    if not message_id:
        return
    key = hashlib.sha256(json.dumps([bot, context['chat_id'], message_id]).encode()).hexdigest()
    record = dict(id=key, status='queued', created_at=time.time(), bot=bot,
                  user_id=OWNER, channel=context['chat_id'], thread=context.get('thread_id') or message_id,
                  group=config['group'])
    target = QUEUE / (key + '.json')
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, 'w') as out:
        json.dump(record, out)
