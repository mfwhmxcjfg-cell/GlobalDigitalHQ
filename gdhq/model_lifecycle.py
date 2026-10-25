"""Offline, provider-scoped lifecycle checks. Never select a replacement or call an API."""
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .settings import ROOT

CATALOG = ROOT / 'seed' / 'model_lifecycle.json'


def catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def model_status(config, today=None):
    data = catalog()
    model = config.get('model', '')
    host = urlsplit(config.get('url', '')).hostname
    result = {'status': 'NOT_APPLICABLE', 'checked_at': data['verified_at'],
              'source': data['source'], 'auto_replacement': False}
    if config.get('kind') != 'MODEL':
        return result
    if config.get('local') and host in ('127.0.0.1', '::1', 'localhost'):
        result['status'] = 'LOCAL_OR_ROUTER_UNVERIFIED'
        return result
    if host != 'api.openai.com' or config.get('protocol', 'openai') != 'openai':
        result['status'] = 'PROVIDER_UNVERIFIED'
        return result
    # Fine-tuned API IDs use ft:<base>:<organization>:<suffix>:<id>.
    base = model.split(':')[1] if model.startswith('ft:') and ':' in model else model
    candidates = {base, 'ft-' + base} if model.startswith('ft:') else {base}
    entry = next((x for x in data['retirements'] if candidates.intersection(x['models'])), None)
    if entry is None:
        result['status'] = 'NOT_LISTED_AVAILABILITY_UNVERIFIED'
        return result
    result.update(shutdown_date=entry['shutdown_date'], replacements=entry['replacements'])
    result['status'] = 'RETIRED' if (today or date.today()).isoformat() >= entry['shutdown_date'] else 'DEPRECATED'
    return result


def ensure_model_available(config):
    status = model_status(config)
    if status['status'] == 'RETIRED':
        raise ValueError('Modèle OpenAI retiré le ' + status['shutdown_date'] +
                         ' : choisir et évaluer un remplacement explicite. Aucun appel effectué.')
    return status
