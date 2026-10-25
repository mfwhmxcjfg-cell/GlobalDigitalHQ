"""Explicitly approved remote model calls, bounded per connector, no tool execution."""
import json
from .public_http import fetch,ConnectorError
from .live import auth,redact,reserve,check_running,DECISION_SYSTEM,validate_decision,MissingResource
from .database import utc,dumps

class RemoteModel:
    def __init__(self,db,pid,row):self.db=db;self.pid=pid;self.row=row;self.config=json.loads(row['config'])
    def chat(self,system,user,model=None,max_tokens=1100):
        c=self.config;check_running(self.db)
        from .model_lifecycle import ensure_model_available
        try:ensure_model_available(c)
        except ValueError as exc:raise ConnectorError(str(exc)) from None
        cid=reserve(self.db,self.row,self.pid)
        try:
            headers=auth(c)
            if c['protocol']=='anthropic':
                headers['anthropic-version']='2023-06-01'
                payload={'model':c['model'],'system':system[:14000],'messages':[{'role':'user','content':user[:26000]}],'max_tokens':min(max_tokens,5000)}
            else:
                payload={'model':c['model'],'messages':[{'role':'system','content':system[:14000]},{'role':'user','content':user[:26000]}],c['output_limit_field']:min(max_tokens,5000),'stream':False}
            raw,_=fetch(c['url'],headers,payload,local=c['local'])
            response=json.loads(raw)
            if c['protocol']=='anthropic':text='\n'.join(x['text'] for x in response.get('content',[]) if x.get('type')=='text')
            else:text=response['choices'][0]['message']['content']
            if not isinstance(text,str) or not text.strip():raise ConnectorError('Réponse modèle vide')
            self.db.write("UPDATE connector_calls SET status='OK' WHERE id=?",(cid,))
            return redact(text,c).strip()
        except Exception as exc:
            self.db.write("UPDATE connector_calls SET status='FAILED' WHERE id=?",(cid,))
            if isinstance(exc,(ConnectorError,PermissionError)):raise
            raise ConnectorError('Réponse du modèle inexploitable : '+type(exc).__name__) from None


def compare(db,pid,plan,rows,prompt):
    reports=[]
    for cid in plan['model_ids']:
        row=db.one('SELECT * FROM live_connectors WHERE id=?',(cid,))
        if not row or not row['approved']:raise ConnectorError('Modèle non autorisé')
        client=RemoteModel(db,pid,row)
        report=validate_decision(client.chat(DECISION_SYSTEM,prompt,max_tokens=1600),rows,plan['required_kpis'])
        reports.append({'model':client.config['model'],'report':report,'connector_id':cid})
        db.write('INSERT INTO evidence_decisions(project_id,model,report,created_at) VALUES(?,?,?,?)',(pid,client.config['model'],dumps(report),utc()))
    # Selection by valid evidence coverage, not votes or answer fluency.
    reports.sort(key=lambda r:len({x['evidence_id'] for x in r['report']['claims']}),reverse=True)
    if len(reports)>1:
        best=db.one('SELECT * FROM live_connectors WHERE id=?',(reports[0]['connector_id'],))
        raw=RemoteModel(db,pid,best).chat(
            'Compare ces analyses avec les extraits fournis. Réponds en JSON strict {"agreement":"CONSISTENT" ou "DISAGREEMENT","reason":"explication"}. Un doute matériel ou contradiction impose DISAGREEMENT. Ne vote pas : les citations priment.',
            prompt[:16000]+'\nANALYSES :\n'+dumps(reports)[:10000],max_tokens=500)
        try:consistent=json.loads(raw).get('agreement')=='CONSISTENT'
        except ValueError:consistent=False
        if not consistent:raise MissingResource('Désaccord entre modèles : consulter les analyses, ajouter des preuves ou choisir explicitement un modèle puis valider la demande')
    return reports
