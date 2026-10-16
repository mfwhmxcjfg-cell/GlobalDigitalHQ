"""Hard boundaries: cost, publishing, and customer data operations require an explicit gate."""
from .database import utc

GUARDED_ACTIONS={'SPEND','ENABLE_PAID_API','PUBLISH','SEND_MARKETING','COLLECT_PERSONAL_DATA','CHARGE_CARD','ORDER_SUPPLIER','DEPLOY_PUBLIC','DELETE_PRODUCTION_DATA'}

def require_gate(db, project_id, action, justification):
    if action not in GUARDED_ACTIONS: raise ValueError('Action gouvernée inconnue.')
    row=db.one('SELECT * FROM gates WHERE project_id=? AND action=?',(project_id,action))
    if not row:
        db.write('INSERT INTO gates(project_id,action,state,justification,created_at) VALUES(?,?,?,?,?)', (project_id,action,'AWAITING_OWNER',justification[:1000],utc()))
        row=db.one('SELECT * FROM gates WHERE project_id=? AND action=?',(project_id,action))
    return row

def decision(db, gate_id, value):
    if value not in ('APPROVED','REJECTED'):raise ValueError('Décision invalide.')
    with db.lock,db.connect() as c:
        gate=c.execute('SELECT * FROM gates WHERE id=?',(gate_id,)).fetchone()
        if not gate or gate['state']!='AWAITING_OWNER':raise ValueError('Validation inexistante ou déjà décidée.')
        c.execute('UPDATE gates SET state=?,decided_at=? WHERE id=?',(value,utc(),gate_id))
    db.event('OWNER_GATE',f'{gate["action"]} : {value}',gate['project_id'])
    return {'id':gate_id,'state':value}

def block_external(action):
    """This product has no integration able to charge, publish or transact, irrespective of gate status."""
    raise PermissionError(f'{action} : opération externe non implémentée. Aucune exécution réelle possible.')
