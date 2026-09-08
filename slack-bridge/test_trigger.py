import importlib.util
import unittest
import asyncio
import tempfile
from unittest.mock import patch
import json
import sys
from types import SimpleNamespace
from pathlib import Path
spec = importlib.util.spec_from_file_location('trigger', Path(__file__).with_name('handler.py'))
hook = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'settings': SimpleNamespace(load=lambda: {'owner_id': 'UOWNERTEST', 'queue_dir': '/tmp/test-shepherd-queue', 'bot_id': 'review-bot', 'group': 'example-app'})}):
    spec.loader.exec_module(hook)


class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.context = dict(platform='slack', user_id=hook.OWNER, chat_id='D123456789', raw_message='Run release review')

    def test_explicit_owner_request(self):
        self.assertTrue(hook.eligible(self.context))

    def test_other_user_rejected(self):
        self.context['user_id'] = 'UOTHER0000'
        self.assertFalse(hook.eligible(self.context))

    def test_quoted_or_expanded_text_rejected(self):
        for message in ['Please explain run release review', 'Run release review; deploy now', '> Run release review']:
            self.context['raw_message'] = message
            self.assertFalse(hook.eligible(self.context))

    def test_mention_accepted(self):
        self.context['raw_message'] = '<@UBOT12345> Run release review!'
        self.assertTrue(hook.eligible(self.context))

    def test_labeled_slack_mention(self):
        self.context['raw_message'] = '<@UREVIEWBOT|Review Bot> run release review'
        self.assertTrue(hook.eligible(self.context))

    def test_context_cannot_trigger(self):
        self.context['raw_message'] = 'status?'
        self.context['message'] = 'Run release review'
        self.assertFalse(hook.eligible(self.context))

    def test_actual_gateway_context_enqueues_once(self):
        self.context.update(raw_message='<@UREVIEWBOT|Review Bot> run release review',
                            message='[Channel context] unrelated history',
                            message_id='1234567890.123456', session_id='session')
        with tempfile.TemporaryDirectory() as directory, patch.object(hook, 'QUEUE', Path(directory)):
            asyncio.run(hook.handle('agent:start', self.context))
            asyncio.run(hook.handle('agent:start', self.context))
            files = list(Path(directory).glob('*.json'))
            self.assertEqual(len(files), 1)
            record = json.loads(files[0].read_text())
            self.assertEqual(record['thread'], self.context['message_id'])
            self.assertEqual(record['status'], 'queued')

    def test_other_platform_rejected(self):
        self.context['platform'] = 'telegram'
        self.assertFalse(hook.eligible(self.context))


if __name__ == '__main__':
    unittest.main()
