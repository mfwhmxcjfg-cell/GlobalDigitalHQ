"""Offline paired evaluation. No provider calls, tools, runtime writes or promotion.

Inputs are owner/reviewer supplied observations, not model self-grades. A passing
report is a recommendation for owner review, never permission to change routing.
"""
import hashlib
import json
import math
from collections import Counter
from statistics import median

CATEGORIES = ('screenshots', 'products', 'writing', 'interfaces')
CANDIDATE = 'gpt-6.1-terra'
CAP_USD = 2.0


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value, positive=False):
    return (type(value) in (int, float) and math.isfinite(value)
            and (value > 0 if positive else value >= 0))


def validate_suite(suite):
    require(isinstance(suite, dict), 'Suite JSON attendue')
    require(suite.get('candidate') == CANDIDATE, 'Candidat incorrect')
    require(isinstance(suite.get('baseline'), str) and
            suite['baseline'].strip() and suite['baseline'] != CANDIDATE,
            'Modèle de référence exact requis')
    cases = suite.get('cases')
    require(isinstance(cases, list) and len(cases) == 20,
            '20 missions réelles sont requises ; aucun exemple synthétique admis')
    ids = set()
    for case in cases:
        require(isinstance(case, dict), 'Mission invalide')
        cid = case.get('id')
        require(isinstance(cid, str) and cid.strip() and cid not in ids,
                'Identifiants uniques requis')
        ids.add(cid)
        require(case.get('category') in CATEGORIES, 'Catégorie invalide')
        require(case.get('synthetic') is False, 'Mission synthétique interdite')
        for name in ('mission_reference', 'prompt', 'captured_at'):
            require(isinstance(case.get(name), str) and case[name].strip(),
                    'Champ requis : ' + name)
        criteria = case.get('criteria')
        require(isinstance(criteria, list) and criteria and
                all(isinstance(x, str) and x.strip() for x in criteria) and
                len(set(criteria)) == len(criteria), 'Critères uniques requis')
        evidence = case.get('evidence')
        require(isinstance(evidence, list) and evidence, 'Preuves requises')
        for item in evidence:
            require(isinstance(item, dict), 'Preuve invalide')
            for name in ('reference', 'observed_at', 'excerpt'):
                require(isinstance(item.get(name), str) and item[name].strip(),
                        'Preuve incomplète : ' + name)
        # Freeze the actual assets by content, not just a mutable file name/URL.
        assets = case.get('assets', [])
        require(isinstance(assets, list), 'Liste de pièces requise')
        if case['category'] in ('screenshots', 'interfaces'):
            require(bool(assets), 'Capture réelle requise pour une mission visuelle')
        for asset in assets:
            require(isinstance(asset, dict) and
                    isinstance(asset.get('reference'), str) and asset['reference'].strip() and
                    isinstance(asset.get('sha256'), str) and len(asset['sha256']) == 64 and
                    all(c in '0123456789abcdef' for c in asset['sha256']),
                    'Pièce : référence et SHA256 requis')
    require(Counter(c['category'] for c in cases) == Counter({k: 5 for k in CATEGORIES}),
            'Cinq missions par catégorie sont requises')
    return suite


def prepare(suite):
    validate_suite(suite)
    return {'suite_sha256': fingerprint(suite), 'status': 'PREPARED_NOT_EXECUTED',
            'mode': 'OFFLINE_REPLAY_ONLY', 'candidate': CANDIDATE,
            'baseline': suite['baseline'], 'total_budget_usd': CAP_USD,
            'tools': [], 'production_routing': 'UNCHANGED',
            'requires': ['Owner Gate limité au test et aux données autorisées',
                         'clé hors Git sur le poste exécutant',
                         'adaptateur Responses et réservations atomiques vérifiés',
                         'relecteur indépendant des modèles évalués'],
            'case_ids': [c['id'] for c in suite['cases']]}


def evaluate(suite, observations):
    validate_suite(suite)
    require(isinstance(observations, dict) and
            observations.get('suite_sha256') == fingerprint(suite),
            'Les observations ne correspondent pas à la suite figée')
    rows = observations.get('rows')
    require(isinstance(rows, list) and len(rows) == 40,
            '40 observations requises : 20 missions pour chacun des deux modèles')
    cases = {c['id']: c for c in suite['cases']}
    models = (CANDIDATE, suite['baseline'])
    seen, requests, costs, durations, passed = set(), set(), {}, {}, {}
    for model in models:
        costs[model], durations[model], passed[model] = 0.0, [], []
    reasons = []
    for row in rows:
        require(isinstance(row, dict), 'Observation invalide')
        identity = (row.get('case_id'), row.get('model'))
        require(identity[0] in cases and identity[1] in models and identity not in seen,
                'Observation dupliquée, inconnue ou modèle incorrect')
        seen.add(identity)
        for field in ('request_id', 'output_sha256', 'trace_reference', 'reviewer', 'reviewed_at'):
            require(isinstance(row.get(field), str) and row[field].strip(),
                    'Observation incomplète : ' + field)
        request_identity = (identity[1], row['request_id'])
        require(request_identity not in requests, 'Requête fournisseur réutilisée pour plusieurs missions')
        requests.add(request_identity)
        require(len(row['output_sha256']) == 64 and
                all(c in '0123456789abcdef' for c in row['output_sha256']), 'SHA256 sortie invalide')
        require(row.get('completed') is True, 'Une exécution incomplète ne peut pas réussir')
        require(row.get('cost_status') == 'RECONCILED',
                'Coût total outils et erreurs compris, rapproché au fournisseur, requis')
        require(finite(row.get('cost_usd')) and finite(row.get('latency_ms'), True),
                'Coût ou durée invalide')
        require(type(row.get('unauthorized_actions')) is int and row['unauthorized_actions'] >= 0 and
                type(row.get('unsupported_claims')) is int and row['unsupported_claims'] >= 0,
                'Comptages de sécurité et de preuves requis')
        checks = row.get('criteria_pass')
        require(isinstance(checks, list) and len(checks) == len(cases[identity[0]]['criteria']) and
                all(type(x) is bool for x in checks), 'Revue de tous les critères requise')
        if row['unauthorized_actions'] or row['unsupported_claims']:
            reasons.append('SAFETY_OR_EVIDENCE_FAILURE')
        costs[identity[1]] += row['cost_usd']
        durations[identity[1]].append(row['latency_ms'])
        passed[identity[1]].append(all(checks))
    total = sum(costs.values())
    if total > CAP_USD + 1e-9:
        reasons.append('BUDGET_EXCEEDED')
    quality = sum(passed[CANDIDATE]) / 20
    if quality < .9 or sum(passed[CANDIDATE]) < sum(passed[suite['baseline']]):
        reasons.append('QUALITY_REGRESSION_OR_BELOW_90_PERCENT')
    baseline_cost = costs[suite['baseline']]
    saving = 1 - costs[CANDIDATE] / baseline_cost if baseline_cost else None
    if saving is None or saving < .3 - 1e-9:
        reasons.append('SAVINGS_BELOW_30_PERCENT_OR_UNMEASURABLE')
    if median(durations[CANDIDATE]) > median(durations[suite['baseline']]):
        reasons.append('LATENCY_REGRESSION')
    return {'status': 'REJECTED' if reasons else 'ELIGIBLE_FOR_OWNER_REVIEW',
            'reasons': sorted(set(reasons)), 'suite_sha256': fingerprint(suite),
            'quality_rate': quality, 'cost_usd': costs, 'total_cost_usd': total,
            'saving_rate': saving,
            'median_latency_ms': {k: median(v) for k, v in durations.items()},
            'production_routing': 'UNCHANGED', 'automatic_promotion': False,
            'evidence_limit': 'Owner-supplied observations; source truth and invoices require independent review'}
