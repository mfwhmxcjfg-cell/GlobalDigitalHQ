"""Explicit agent registry sourced from the previous Hybrid archive; not active model processes."""
import json,re
from .settings import ROOT
ROLES=json.loads((ROOT/'seed'/'roles.json').read_text(encoding='utf-8'))
INDEX={x['id']:x for x in ROLES}
if len(ROLES)!=40 or len(INDEX)!=40:
    raise RuntimeError('Le catalogue doit contenir exactement 40 managers distincts.')

DEPARTMENTS = {
    'services': ['ceo','chief_of_staff','sales','operations','finance','accounting','compliance','security','qa','support'],
    'dropshipping': ['ceo','chief_of_staff','trend_intel','customer_research','competitive_intel','market_analyst','product_architect','pricing','finance','supplier','compliance','security','qa','growth'],
    'webapp': ['ceo','chief_of_staff','product_architect','digital_factory','qa','security','compliance','learning'],
    'content': ['ceo','chief_of_staff','trend_intel','content_strategist','growth','qa','compliance'],
    'services': ['ceo','chief_of_staff','sales','accounting','operations','finance','compliance','qa','security'],
    'general': ['ceo','chief_of_staff','market_analyst','product_architect','finance','qa','security']
}

def team_for(kind):
    terms={r['id'] for r in ROLES}
    chosen=[r for r in DEPARTMENTS.get(kind,DEPARTMENTS['general']) if r in terms]
    if len(chosen)<3:
        chosen=[r['id'] for r in ROLES[:8]]
    return [INDEX[x] for x in chosen]

def skill_text(role):
    p=ROOT/'seed'/'skills'/role['id'].replace('_','-')/'SKILL.md'
    try:
        if p.is_file() and p.resolve().is_relative_to((ROOT/'seed'/'skills').resolve()):
            return p.read_text(encoding='utf-8')[:5000]
    except (OSError,ValueError):pass
    return 'Rôle : '+role['id']+' — '+role['name']+'\nMission : '+role['mission']+'\nInterdits : '+', '.join(role.get('must_not',[]))
