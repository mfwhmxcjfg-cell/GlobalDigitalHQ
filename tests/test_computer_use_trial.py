import ast
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from gdhq.computer_use_trial import TrialBlocked, TrialExecutor
from gdhq.model_lifecycle import model_status, ensure_model_available
from gdhq.model_council import RemoteModel
from gdhq.public_http import ConnectorError


def action(name='click', arguments=None, safety='allowed'):
    return {'name': name, 'arguments': {'x': 100, 'y': 120} if arguments is None else arguments,
            'safety_decision': safety}


class ComputerUseTrialTests(unittest.TestCase):
    def page(self):
        page = Mock()
        page.url = 'about:blank'
        page.viewport_size = {'width': 2000, 'height': 1000}
        return page

    def test_coordinates_scaled_and_success_traced_without_arguments(self):
        page = self.page(); executor = TrialExecutor(page)
        executor.execute(action())
        page.mouse.click.assert_called_once_with(200, 120)
        self.assertEqual(executor.events, [{'step': 1, 'action': 'click', 'status': 'EXECUTED'}])
        self.assertNotIn('arguments', json.dumps(executor.events))

    def test_unknown_or_malformed_actions_never_execute(self):
        invalid = [action('navigate', {'url': 'https://example.org'}), action('shell', {'command': 'noop'}),
                   action(['click']), action(arguments={'x': float('nan'), 'y': 1}),
                   action(arguments={'x': True, 'y': 1}), action(arguments={'x': 1001, 'y': 1}),
                   action(arguments={'x': 1, 'y': 1, 'extra': 'unsafe'}),
                   action('type', {'text': 'contains\ncontrol'}), action('type', {'text': 'x'*101}),
                   action(safety='require_confirmation'), action(safety='blocked'), {}, None]
        for item in invalid:
            page = self.page(); executor = TrialExecutor(page)
            with self.subTest(item=item), self.assertRaises(TrialBlocked): executor.execute(item)
            page.mouse.click.assert_not_called()
            page.locator.assert_not_called()
            with self.assertRaisesRegex(TrialBlocked, 'ALREADY_BLOCKED'): executor.execute(action())

    def test_focus_stop_url_and_step_limits(self):
        page = self.page(); page.locator.return_value.evaluate.return_value = False
        with self.assertRaisesRegex(TrialBlocked, 'INPUT_NOT_FOCUSED'):
            TrialExecutor(page).execute(action('type', {'text': 'fixture'}))
        page.locator.return_value.fill.assert_not_called()
        for reason in ('url', 'stop', 'time', 'steps'):
            page = self.page(); executor = TrialExecutor(page, max_steps=1, stopped=lambda: reason == 'stop')
            if reason == 'url': page.url = 'https://example.org'
            if reason == 'time': executor.deadline = 0
            if reason == 'steps': executor.execute(action()); page.mouse.click.reset_mock()
            with self.subTest(reason=reason), self.assertRaises(TrialBlocked): executor.execute(action())
            page.mouse.click.assert_not_called()

    def test_error_and_stop_after_effect_are_not_reported_successful(self):
        page = self.page(); page.mouse.click.side_effect = RuntimeError('private error')
        executor = TrialExecutor(page)
        with self.assertRaisesRegex(TrialBlocked, 'EXECUTION_ERROR'): executor.execute(action())
        self.assertNotIn('private error', json.dumps(executor.events))
        page = self.page(); executor = TrialExecutor(page, stopped=Mock(side_effect=[False, True]))
        with self.assertRaisesRegex(TrialBlocked, 'EMERGENCY_STOP'): executor.execute(action())
        self.assertEqual([e['status'] for e in executor.events], ['EXECUTED', 'BLOCKED'])


class AnthropicModeRetirementTests(unittest.TestCase):
    def config(self, **changes):
        return {'kind': 'MODEL', 'protocol': 'anthropic', 'url': 'https://api.anthropic.com/v1/messages',
                'model': 'claude-opus-4-8', 'speed': 'fast', **changes}

    def test_exact_mode_and_retirement_boundary(self):
        config = self.config()
        self.assertEqual(model_status(config, date(2026,11,29))['status'], 'MODE_DEPRECATED')
        self.assertEqual(model_status(config, date(2026,11,30))['status'], 'MODE_RETIRED')
        for changes in ({'speed': 'standard'}, {'model': 'claude-opus-5-5'},
                        {'url': 'https://router.example/v1/messages'}, {'protocol': 'openai'}):
            self.assertEqual(model_status(self.config(**changes))['status'], 'PROVIDER_UNVERIFIED')

    def test_retired_mode_never_reserves_or_calls_network(self):
        db = Mock(); row = {'config': json.dumps(self.config())}
        retired = model_status(self.config(), date(2026,11,30))
        with patch('gdhq.model_lifecycle.model_status', return_value=retired), \
             patch('gdhq.model_council.check_running'), patch('gdhq.model_council.reserve') as reserve, \
             patch('gdhq.model_council.fetch') as network:
            with self.assertRaisesRegex(ConnectorError, 'Mode fournisseur retiré'):
                RemoteModel(db, None, row).chat('system', 'fixture')
            reserve.assert_not_called(); network.assert_not_called()

    def test_current_adapter_does_not_silently_enable_fast_mode(self):
        root = Path(__file__).resolve().parents[1]
        module = ast.parse((root/'gdhq/model_council.py').read_text(encoding='utf-8'))
        payload_dicts = [n for n in ast.walk(module) if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == 'payload' for t in n.targets)
                         and isinstance(n.value, ast.Dict)]
        self.assertTrue(payload_dicts)
        for node in payload_dicts:
            self.assertNotIn('speed', [k.value for k in node.value.keys if isinstance(k, ast.Constant)])
