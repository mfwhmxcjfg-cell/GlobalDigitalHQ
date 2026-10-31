"""Native stateless Gemini transport. Browser proposals NEVER execute actions."""
import base64
import json
import math

from . import live
from .public_http import fetch, ConnectorError

URL = 'https://generativelanguage.googleapis.com/v1/interactions'
FIXTURE_PROMPT = ('This is a synthetic offline GDHQ form, not a real service. '
                  'Suggest only the next click to focus the title input. '
                  'Do not navigate, submit, use another tool or request private data.')


def interact(db, pid, row, system, user, max_tokens=1100, fixture_png=None):
    c = live.clean_config(json.loads(row['config']))
    if c['kind'] != 'MODEL' or c['protocol'] != 'gemini_interactions':
        raise ConnectorError('Gemini Interactions connector required')
    if type(max_tokens) is not int or not 1 <= max_tokens <= 5000:
        raise ValueError('Output limit must be between 1 and 5000 tokens')
    if not isinstance(system, str) or not isinstance(user, str):
        raise ValueError('Text input required')
    payload = {'model': c['model'], 'input': user[:26000],
               'system_instruction': system[:14000], 'store': False, 'stream': False,
               'generation_config': {'max_output_tokens': max_tokens}}
    if fixture_png is not None:
        if not c.get('browser_fixture'):
            raise ConnectorError('Synthetic screenshot transmission not approved')
        if not isinstance(fixture_png, bytes) or not fixture_png.startswith(b'\x89PNG\r\n\x1a\n') or len(fixture_png) > 262144:
            raise ValueError('Bounded PNG fixture required')
        # A fixed prompt and fresh synthetic screenshot only. No production browser.
        payload['system_instruction'] = 'Propose an action only; the client will not execute it.'
        payload['input'] = [{'type': 'text', 'text': FIXTURE_PROMPT},
                            {'type': 'image', 'mime_type': 'image/png',
                             'data': base64.b64encode(fixture_png).decode('ascii')}]
        payload['tools'] = [{'type': 'computer_use', 'environment': 'browser',
                             'enable_prompt_injection_detection': True}]
    headers = live.auth(c)  # Missing credential fails BEFORE reserving any call.
    live.check_running(db)
    cid = live.reserve(db, row, pid)
    try:
        raw, _ = fetch(URL, headers, payload)
        response = json.loads(raw)
        if (not isinstance(response, dict) or response.get('status') not in ('completed', 'requires_action')
                or not isinstance(response.get('steps'), list) or len(response['steps']) > 100
                or any(not isinstance(s, dict) for s in response['steps'])):
            raise ConnectorError('Gemini response incomplete or invalid')
        # A transport success is not a validated decision or browser success.
        live.check_running(db)
        db.write("UPDATE connector_calls SET status='OK' WHERE id=?", (cid,))
        return response
    except Exception:
        db.write("UPDATE connector_calls SET status='FAILED' WHERE id=?", (cid,))
        raise ConnectorError('Gemini call failed; no automatic retry or action') from None


def text_result(response, config):
    if response.get('status') != 'completed' or any(s.get('type') not in ('model_output', 'thought') for s in response['steps']):
        raise ConnectorError('Text-only council refuses tools or incomplete output')
    texts = []
    for step in response['steps']:
        if step.get('type') != 'model_output': continue  # Never expose thought steps.
        content = step.get('content', [])
        if not isinstance(content, list): raise ConnectorError('Invalid Gemini text')
        for part in content:
            if not isinstance(part, dict) or part.get('type') != 'text' or not isinstance(part.get('text'), str):
                raise ConnectorError('Non-text Gemini output refused')
            texts.append(part['text'])
    text = '\n'.join(texts).strip()
    if not text: raise ConnectorError('Empty Gemini text')
    return live.redact(text, config)


def proposal_summary(response):
    """Sanitized metadata only. Never return action arguments or reasoning."""
    calls = [s for s in response['steps'] if s.get('type') == 'function_call']
    allowed = len(calls) == 1 and response.get('status') == 'requires_action'
    for call in calls:
        args = call.get('arguments')
        allowed = allowed and call.get('name') == 'click' and isinstance(args, dict)
        if not isinstance(args, dict): continue
        allowed = allowed and not (set(args) - {'x', 'y', 'intent'})
        allowed = allowed and all(type(args.get(k)) in (int, float) and math.isfinite(args[k])
                                  and 0 <= args[k] <= 1000 for k in ('x', 'y'))
        # No action is authorized by absence of a provider safety verdict.
        allowed = allowed and call.get('safety_decision') in (None, 'allowed')
    if any(s.get('type') not in ('function_call', 'thought', 'model_output') for s in response['steps']):
        allowed = False
    return {'status': 'PROPOSAL_RECEIVED_NOT_EXECUTED' if allowed else 'PROPOSAL_BLOCKED',
            'model_called': True, 'actions_executed': 0, 'function_calls': len(calls),
            'provider_cost_usd': None, 'production_routing': 'UNCHANGED',
            'limitation': 'One synthetic screenshot; not an execution or Gemini success benchmark'}


def probe_fixture(db, pid, row, browser):
    """Fresh offline fixture, one API request, zero execution of returned actions."""
    from .computer_use_trial import FIXTURE
    context = browser.new_context(viewport={'width': 1000, 'height': 1000},
                                  accept_downloads=False, service_workers='block')
    try:
        context.route('**/*', lambda route: route.abort())
        page = context.new_page()
        context.on('page', lambda other: other.close() if other != page else None)
        page.set_content(FIXTURE)
        png = page.screenshot(type='png')
        response = interact(db, pid, row, '', FIXTURE_PROMPT, max_tokens=1000, fixture_png=png)
        return proposal_summary(response)
    finally:
        context.close()
