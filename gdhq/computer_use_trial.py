"""Offline browser executor trial. No model, API, runtime DB or production integration.

Only our fixed synthetic form is loaded into an isolated browser context. Remote
requests and popups must be blocked by the caller; default CLI does exactly that.
"""
import math
import time

FIXTURE = '''<!doctype html><html lang="fr"><meta charset="utf-8">
<title>GDHQ — fixture locale, aucun service connecté</title>
<style>body{font:18px sans-serif;margin:40px}input{position:absolute;left:40px;top:100px;width:300px;height:35px}
button{position:absolute;left:40px;top:160px;width:160px;height:40px}output{position:absolute;left:40px;top:240px}</style>
<h1>Essai synthétique local</h1><label for="title">Titre fictif</label>
<input id="title" maxlength="100" autocomplete="off"><button id="save" type="button">Valider le brouillon</button>
<output id="result" role="status"></output>
<script>document.getElementById('save').onclick=()=>{document.getElementById('result').textContent=
'Brouillon local : '+document.getElementById('title').value;};</script></html>'''


class TrialBlocked(RuntimeError):
    pass


class TrialExecutor:
    """Bounded action dispatch, fail closed. A denial stops the whole trial."""
    def __init__(self, page, max_steps=20, max_seconds=30, stopped=lambda: False):
        if type(max_steps) is not int or not 1 <= max_steps <= 20:
            raise ValueError('Invalid step limit')
        if type(max_seconds) not in (float, int) or not math.isfinite(max_seconds) or not 0 < max_seconds <= 30:
            raise ValueError('Invalid duration limit')
        self.page, self.max_steps, self.stopped = page, max_steps, stopped
        self.deadline = time.monotonic() + max_seconds
        self.events, self.state = [], 'READY'

    def block(self, code):
        self.state = 'BLOCKED'
        self.events.append({'step': len(self.events) + 1, 'status': 'BLOCKED', 'reason': code})
        raise TrialBlocked(code)

    def execute(self, action):
        if self.state == 'BLOCKED':
            raise TrialBlocked('TRIAL_ALREADY_BLOCKED')
        if self.stopped(): self.block('EMERGENCY_STOP')
        if time.monotonic() >= self.deadline: self.block('TIME_LIMIT')
        if len(self.events) >= self.max_steps: self.block('STEP_LIMIT')
        if self.page.url != 'about:blank': self.block('UNEXPECTED_PAGE')
        if not isinstance(action, dict) or set(action) != {'name', 'arguments', 'safety_decision'}:
            self.block('INVALID_ACTION')
        if action['safety_decision'] != 'allowed': self.block('CONFIRMATION_OR_DENIAL')
        name, args = action['name'], action['arguments']
        if not isinstance(args, dict): self.block('INVALID_ARGUMENTS')
        expected = {'click': {'x', 'y'}, 'type': {'text'}}
        if not isinstance(name, str) or name not in expected or set(args) != expected[name]:
            self.block('ACTION_NOT_ALLOWED')
        if name == 'click':
            if any(type(args[k]) not in (int, float) or not math.isfinite(args[k])
                   or not 0 <= args[k] <= 1000 for k in ('x', 'y')):
                self.block('INVALID_COORDINATES')
        else:
            if not isinstance(args['text'], str) or not 1 <= len(args['text']) <= 100 or any(
                    ord(c) < 32 or ord(c) == 127 for c in args['text']):
                self.block('INVALID_TEXT')
        try:
            if name == 'click':
                viewport = self.page.viewport_size
                self.page.mouse.click(args['x'] * viewport['width'] / 1000,
                                      args['y'] * viewport['height'] / 1000)
            else:
                # Never send text to arbitrary focused widgets or password fields.
                if not self.page.locator('#title').evaluate('(e) => e === document.activeElement'):
                    self.block('INPUT_NOT_FOCUSED')
                self.page.locator('#title').fill(args['text'], timeout=1000)
        except TrialBlocked:
            raise
        except Exception:
            self.block('EXECUTION_ERROR')
        self.events.append({'step': len(self.events) + 1, 'action': name, 'status': 'EXECUTED'})
        if self.stopped(): self.block('EMERGENCY_STOP')
        self.state = 'RUNNING'


def run_browser_trial(browser):
    """Ten actual browser replays with synthetic actions; NOT Gemini executions."""
    context = browser.new_context(viewport={'width': 1000, 'height': 1000},
                                  accept_downloads=False, service_workers='block')
    blocked_requests = []
    def deny(route):
        blocked_requests.append(True)
        route.abort()
    context.route('**/*', deny)
    page = context.new_page()
    context.on('page', lambda other: other.close() if other != page else None)
    checks = []
    try:
        for i in range(10):
            page.set_content(FIXTURE)
            executor = TrialExecutor(page)
            title = 'Fixture synthétique ' + str(i + 1)
            for action in (
                {'name': 'click', 'arguments': {'x': 100, 'y': 120}, 'safety_decision': 'allowed'},
                {'name': 'type', 'arguments': {'text': title}, 'safety_decision': 'allowed'},
                {'name': 'click', 'arguments': {'x': 100, 'y': 180}, 'safety_decision': 'allowed'}):
                executor.execute(action)
            success = page.locator('#result').inner_text() == 'Brouillon local : ' + title
            checks.append({'id': i + 1, 'passed': success, 'events': executor.events})
        # Real-browser refusal and kill-switch checks, before any dangerous call.
        for action in (
            {'name': 'navigate', 'arguments': {'url': 'https://example.com'}, 'safety_decision': 'allowed'},
            {'name': 'click', 'arguments': {'x': 100, 'y': 180}, 'safety_decision': 'require_confirmation'}):
            try: TrialExecutor(page).execute(action)
            except TrialBlocked: pass
            else: raise AssertionError('Guard failed')
        try: TrialExecutor(page, stopped=lambda: True).execute(
            {'name': 'click', 'arguments': {'x': 100, 'y': 180}, 'safety_decision': 'allowed'})
        except TrialBlocked: pass
        else: raise AssertionError('Kill switch failed')
        # Prove interception, rather than only registering an unexercised route.
        outcome = page.evaluate("""async () => { try {
            await fetch('https://gdhq-network-probe.invalid/'); return 'UNEXPECTED';
            } catch (_) { return 'BLOCKED'; } }""")
        if outcome != 'BLOCKED' or not blocked_requests:
            raise AssertionError('Network interception not verified')
        return {'status': 'HARNESS_VERIFIED_MODEL_NOT_TESTED' if all(c['passed'] for c in checks) else 'FAILED',
                'synthetic': True, 'model_called': False, 'provider_cost_usd': 0,
                'gemini_success_rate': None, 'production_routing': 'UNCHANGED',
                'completed_browser_replays': len(checks), 'checks': checks,
                'network_requests_blocked': len(blocked_requests),
                'limitations': ['Fixed local form only; not a general browser sandbox',
                                'No Gemini API, model performance or Windows validation']}
    finally:
        context.close()
