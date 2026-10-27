"""Synthetic fixtures exercise guards; never count as real-model benchmark results."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gdhq.shadow_evaluation import CATEGORIES, CANDIDATE, fingerprint, prepare, evaluate


def fixtures():
    # synthetic=False exercises schema; independent source verification is required
    # for live datasets. These fixtures are explicitly synthetic in this module.
    suite = {'candidate': CANDIDATE, 'baseline': 'gpt-6.1-sol', 'cases': []}
    for category in CATEGORIES:
        for i in range(5):
            suite['cases'].append({'id': category + str(i), 'category': category,
                'synthetic': False, 'mission_reference': 'TEST_ONLY',
                'captured_at': '2026-10-27T10:00:00Z', 'prompt': 'Synthetic test fixture',
                'criteria': ['Expected result', 'Evidence present'],
                'evidence': [{'reference': 'TEST_ONLY', 'observed_at': '2026-10-27', 'excerpt': 'fixture'}],
                'assets': [{'reference': 'TEST_ONLY', 'sha256': 'a' * 64}]})
    rows = []
    for case in suite['cases']:
        for model in (CANDIDATE, suite['baseline']):
            rows.append({'case_id': case['id'], 'model': model, 'request_id': case['id'] + model,
                'output_sha256': 'b' * 64, 'trace_reference': 'TEST_ONLY', 'reviewer': 'unit-test',
                'reviewed_at': '2026-10-27', 'completed': True, 'cost_status': 'RECONCILED',
                'cost_usd': .02 if model == CANDIDATE else .04, 'latency_ms': 500,
                'unauthorized_actions': 0, 'unsupported_claims': 0, 'criteria_pass': [True, True]})
    return suite, {'suite_sha256': fingerprint(suite), 'rows': rows}


class ShadowEvaluationTests(unittest.TestCase):
    def test_offline_no_network_and_no_promotion_even_if_passed(self):
        suite, observed = fixtures()
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
            self.assertEqual(prepare(suite)['status'], 'PREPARED_NOT_EXECUTED')
            report = evaluate(suite, observed)
        self.assertEqual(report['status'], 'ELIGIBLE_FOR_OWNER_REVIEW')
        self.assertIs(report['automatic_promotion'], False)
        self.assertEqual(report['production_routing'], 'UNCHANGED')

    def test_missing_synthetic_or_unbalanced_cases_block(self):
        suite, _ = fixtures()
        for edit in ('empty', 'synthetic', 'duplicate', 'assets', 'unbalanced'):
            bad = copy.deepcopy(suite)
            if edit == 'empty': bad['cases'] = []
            if edit == 'synthetic': bad['cases'][0]['synthetic'] = True
            if edit == 'duplicate': bad['cases'][0]['id'] = bad['cases'][1]['id']
            if edit == 'assets': bad['cases'][0]['assets'] = []
            if edit == 'unbalanced': bad['cases'][0]['category'] = 'writing'
            with self.subTest(edit=edit), self.assertRaises(ValueError): prepare(bad)

    def test_changed_prompt_or_asset_invalidates_results(self):
        for field in ('prompt', 'asset'):
            suite, obs = fixtures()
            if field == 'prompt': suite['cases'][0]['prompt'] += 'changed'
            else: suite['cases'][0]['assets'][0]['sha256'] = 'c' * 64
            with self.subTest(field=field), self.assertRaises(ValueError): evaluate(suite, obs)

    def test_missing_duplicate_wrong_model_or_review_blocks(self):
        suite, obs = fixtures()
        for edit in ('missing', 'duplicate', 'request_reuse', 'wrong_model', 'review', 'incomplete', 'unreconciled'):
            bad = copy.deepcopy(obs)
            if edit == 'missing': bad['rows'].pop()
            if edit == 'duplicate': bad['rows'][0] = bad['rows'][1]
            if edit == 'request_reuse': bad['rows'][2]['request_id'] = bad['rows'][0]['request_id']
            if edit == 'wrong_model': bad['rows'][0]['model'] = 'unknown'
            if edit == 'review': bad['rows'][0]['criteria_pass'] = [True]
            if edit == 'incomplete': bad['rows'][0]['completed'] = False
            if edit == 'unreconciled': bad['rows'][0]['cost_status'] = 'ESTIMATED'
            with self.subTest(edit=edit), self.assertRaises(ValueError): evaluate(suite, bad)

    def test_nonfinite_negative_boolean_metrics_block(self):
        suite, obs = fixtures()
        for value in (float('nan'), float('inf'), -1, True):
            for field in ('cost_usd', 'latency_ms'):
                bad = copy.deepcopy(obs)
                bad['rows'][0][field] = value
                with self.subTest(value=value, field=field), self.assertRaises(ValueError): evaluate(suite, bad)

    def test_safety_and_evidence_failure_on_either_model_reject(self):
        suite, obs = fixtures()
        for index in (0, 1):
            for field in ('unauthorized_actions', 'unsupported_claims'):
                bad = copy.deepcopy(obs)
                bad['rows'][index][field] = 1
                self.assertIn('SAFETY_OR_EVIDENCE_FAILURE', evaluate(suite, bad)['reasons'])

    def test_budget_quality_savings_latency_and_free_baseline(self):
        suite, obs = fixtures()
        cases = {'budget': 'BUDGET_EXCEEDED', 'quality': 'QUALITY_REGRESSION_OR_BELOW_90_PERCENT',
                 'savings': 'SAVINGS_BELOW_30_PERCENT_OR_UNMEASURABLE', 'latency': 'LATENCY_REGRESSION',
                 'free': 'SAVINGS_BELOW_30_PERCENT_OR_UNMEASURABLE'}
        for edit, reason in cases.items():
            bad = copy.deepcopy(obs)
            for row in bad['rows']:
                if edit == 'budget': row['cost_usd'] *= 10
                if row['model'] == CANDIDATE:
                    if edit == 'quality': row['criteria_pass'][0] = False
                    if edit == 'savings': row['cost_usd'] = .04
                    if edit == 'latency': row['latency_ms'] = 501
                elif edit == 'free': row['cost_usd'] = 0
            self.assertIn(reason, evaluate(suite, bad)['reasons'])

    def test_cli_rejects_empty_template_without_echoing_private_input(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/evaluate_shadow.py'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'suite.json'
            path.write_text('{"private":"DO_NOT_PRINT"}', encoding='utf-8')
            result = subprocess.run([sys.executable, str(script), '--suite', str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'BLOCKED')
        self.assertNotIn('DO_NOT_PRINT', result.stdout + result.stderr)
