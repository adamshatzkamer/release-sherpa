import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import shepherd as s


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.group = {'name': 'app'}
        self.snapshot = {'repositories': [{'group': 'app', 'repo': 'org/app', 'branches': {'main': 'base', 'work/app12-fix': 'abc'}}],
                         'issues': [{'id': '12', 'identifier': 'APP-12', 'title': 'Fix', 'status': 'done',
                                     'references': {'work/app12-fix': ['comment']}}]}

    def test_completed_exact_reference_is_candidate(self):
        self.assertEqual(len(s.classify(self.snapshot, self.group)['candidates']), 1)

    def test_active_task_holds_branch(self):
        self.snapshot['issues'].append({'id': '13', 'identifier': 'APP-13', 'status': 'in_review',
                                        'references': {'work/app12-fix': ['comment2']}})
        result = s.classify(self.snapshot, self.group)
        self.assertFalse(result['candidates'])
        self.assertEqual(len(result['held']), 1)

    def test_task_named_in_branch_is_checked_even_without_comment(self):
        self.snapshot['issues'][0].update(status='in_progress', references={})
        self.snapshot['issues'].append({'id': '13', 'identifier': 'APP-13', 'status': 'done',
                                       'references': {'work/app12-fix': ['comment2']}})
        self.assertEqual(len(s.classify(self.snapshot, self.group)['held']), 1)

    def test_task_id_without_branch_evidence_is_not_enough(self):
        self.snapshot['issues'][0]['references'] = {}
        self.assertFalse(s.classify(self.snapshot, self.group)['candidates'])

    def test_fork_divergence_is_held(self):
        self.snapshot['repositories'].append({'group': 'app', 'repo': 'user/app', 'branches': {'work/app12-fix': 'different'}})
        self.assertFalse(s.classify(self.snapshot, self.group)['candidates'])

    def test_unknown_branch_is_not_completed(self):
        self.snapshot['repositories'][0]['branches']['mystery'] = 'other'
        self.assertEqual(len(s.classify(self.snapshot, self.group)['unassociated']), 1)


class VerdictTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'run_id': 'run', 'head_sha': 'head', 'base_sha': 'base', 'diff_base_sha': 'live',
                         'checks': [{'returncode': 0}], 'diff_check': 0, 'deployment_verified': True, 'integration_complete': True}
        self.result = {'reviewer': 'GitHub Copilot in VS Code', 'run_id': 'run', 'head_sha': 'head', 'base_sha': 'base', 'diff_base_sha': 'live',
                       'verdict': 'approved', 'merge_ready': True, 'deploy_ready': True, 'blockers': [], 'summary': 'Reviewed'}

    def test_complete_approval(self):
        self.assertEqual(s.verdict_errors(self.manifest, self.result), [])

    def test_authorized_codex_fallback(self):
        self.manifest.update(expected_reviewer='OpenAI Codex', verified_reviewer='OpenAI Codex', fallback_reason='Copilot quota exhausted')
        self.result['reviewer'] = 'OpenAI Codex'
        self.assertEqual(s.verdict_errors(self.manifest, self.result), [])

    def test_unassigned_codex_rejected(self):
        self.result['reviewer'] = 'OpenAI Codex'
        self.assertTrue(s.verdict_errors(self.manifest, self.result))

    def test_codex_cannot_bypass_checks(self):
        self.manifest.update(expected_reviewer='OpenAI Codex', fallback_reason='Copilot quota exhausted', checks=[])
        self.result['reviewer'] = 'OpenAI Codex'
        self.assertTrue(s.verdict_errors(self.manifest, self.result))

    def test_stale_approval_rejected(self):
        self.result['head_sha'] = 'old-head'
        self.assertTrue(s.verdict_errors(self.manifest, self.result))

    def test_actual_reviewer_mismatch_rejected(self):
        self.manifest['verified_reviewer'] = 'OpenAI Codex'
        self.assertTrue(s.verdict_errors(self.manifest, self.result))

    def test_missing_checks_rejected(self):
        self.manifest['checks'] = []
        self.assertTrue(s.verdict_errors(self.manifest, self.result))

    def test_failed_check_rejected(self):
        self.manifest['checks'][0]['returncode'] = 1
        self.assertTrue(s.verdict_errors(self.manifest, self.result))

    def test_unknown_deployment_rejected(self):
        self.manifest['deployment_verified'] = False
        self.assertTrue(s.verdict_errors(self.manifest, self.result))

    def test_string_boolean_rejected(self):
        self.result['deploy_ready'] = 'true'
        self.assertTrue(s.verdict_errors(self.manifest, self.result))


class GitTests(unittest.TestCase):
    def test_cherry_picked_work_is_not_reintroduced(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            s.git(repo, 'init')
            (repo / 'file').write_text('base\n')
            s.git(repo, 'add', '.')
            s.git(repo, 'commit', '-m', 'base')
            base = s.git(repo, 'rev-parse', 'HEAD').stdout.strip()
            s.git(repo, 'checkout', '-b', 'target')
            (repo / 'file').write_text('fix\n')
            s.git(repo, 'commit', '-am', 'Applied fix')
            target = s.git(repo, 'rev-parse', 'HEAD').stdout.strip()
            s.git(repo, 'checkout', '-b', 'source', base)
            (repo / 'file').write_text('fix\n')
            s.git(repo, 'commit', '-am', 'Original branch fix')
            source = s.git(repo, 'rev-parse', 'HEAD').stdout.strip()
            self.assertFalse(s.ancestor(repo, source, target))
            self.assertTrue(s.patches_in_target_history(repo, source, target))
            (repo / 'file').write_text('new work\n')
            s.git(repo, 'commit', '-am', 'Not yet included')
            self.assertFalse(s.patches_in_target_history(repo, 'HEAD', target))

    def test_conflicting_merge_is_aborted_and_source_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            s.git(repo, 'init')
            (repo / 'file').write_text('base\n')
            s.git(repo, 'add', '.')
            s.git(repo, 'commit', '-m', 'base')
            base = s.git(repo, 'rev-parse', 'HEAD').stdout.strip()
            s.git(repo, 'checkout', '-b', 'feature-a')
            (repo / 'file').write_text('A\n')
            s.git(repo, 'commit', '-am', 'A')
            a = s.git(repo, 'rev-parse', 'HEAD').stdout.strip()
            s.git(repo, 'checkout', '-b', 'feature-b', base)
            (repo / 'file').write_text('B\n')
            s.git(repo, 'commit', '-am', 'B')
            b = s.git(repo, 'rev-parse', 'HEAD').stdout.strip()
            s.git(repo, 'checkout', '-b', 'review', base)
            s.git(repo, 'merge', '--no-ff', '--no-edit', a)
            before = s.git(repo, 'rev-parse', 'HEAD').stdout.strip()
            self.assertNotEqual(s.git(repo, 'merge', '--no-ff', '--no-edit', b, check=False).returncode, 0)
            s.git(repo, 'merge', '--abort')
            self.assertEqual(s.git(repo, 'rev-parse', 'HEAD').stdout.strip(), before)
            self.assertEqual(s.git(repo, 'rev-parse', 'feature-a').stdout.strip(), a)
            self.assertEqual(s.git(repo, 'rev-parse', 'feature-b').stdout.strip(), b)
            self.assertTrue(s.ancestor(repo, a, 'HEAD'))
            self.assertFalse(s.ancestor(repo, b, 'HEAD'))


if __name__ == '__main__':
    unittest.main()
