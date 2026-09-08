import unittest
from check_public_tree import issues

class PublicTreeTests(unittest.TestCase):
    def test_blocks_local_artifacts(self):
        for name in ('config.json', 'bridge.local.json', 'state/result.json', '.env', '__pycache__/module.pyc'):
            self.assertTrue(issues(name, '{}'))

    def test_allows_examples(self):
        self.assertFalse(issues('config.example.json', '{"host":"example.invalid"}'))
        self.assertFalse(issues('.env.example', 'TOKEN=YOUR_TOKEN'))

    def test_flags_realistic_identifiers_without_publishing_them(self):
        value = '/Use' + 'rs/' + 'synthetic' + '/project'
        self.assertTrue(issues('README.md', value))
