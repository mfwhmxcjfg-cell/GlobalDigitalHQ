"""Run bounded local text-only agent drafts on the owner's runner."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from gdhq.roles import INDEX,skill_text
from gdhq.ecosystem import context
from gdhq.providers import Ollama,LMStudio

def run(provider,model,roles,brief,output):
    ids=list(dict.fromkeys(r.strip() for r in roles.split(',') if r.strip()))
    if not ids or len(ids)>40 or any(r not in INDEX for r in ids):raise ValueError('Responsables invalides')
    if not 10<=len(brief)<=2500 or not 1<=len(model)<=160:raise ValueError('Brief ou modèle invalide')
    if model not in provider.models():raise ValueError('Modèle local absent')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    results=[]
    for role_id in ids:
        system=('Produis uniquement un brouillon en français. Aucun outil externe, aucune commande à exécuter. '
                'Sans source datée : DONNÉES INSUFFISANTES.\n'+context(role_id)+'\n'+skill_text(INDEX[role_id])[:3500])
        answer=provider.chat(system,brief,model,max_tokens=900)
        (output/(role_id+'.md')).write_text('# '+INDEX[role_id]['name']+'\n\nBROUILLON NON VÉRIFIÉ — REVUE PROPRIÉTAIRE REQUISE\n\n'+answer,encoding='utf-8')
        results.append({'role':role_id,'status':'DRAFT_CREATED','external_action':False})
    (output/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--provider',choices=['ollama','lmstudio'],required=True);p.add_argument('--model',required=True);p.add_argument('--roles',required=True);p.add_argument('--brief',required=True);p.add_argument('--output',default='agent-output');a=p.parse_args()
    provider=Ollama() if a.provider=='ollama' else LMStudio()
    print(json.dumps(run(provider,a.model,a.roles,a.brief,a.output)))
