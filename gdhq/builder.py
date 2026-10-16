"""Real local static-app generation; never launches third-party commands or charges customers."""
import html,hashlib,json,re
from pathlib import Path
from .database import utc

SAFE_FILES={'index.html','app.js','styles.css'}

STYLE = r'''*{box-sizing:border-box}body{margin:0;font:16px system-ui,sans-serif;color:#1d2540;background:#f7f7fb}a{color:inherit;text-decoration:none}header{display:flex;justify-content:space-between;align-items:center;background:white;padding:18px 7%;border-bottom:1px solid #e6e8f1}.logo{font-weight:850;color:#5437b4;font-size:22px}.pill{background:#eee9ff;border:0;padding:10px 16px;border-radius:30px;color:#5036b5;cursor:pointer}.hero{padding:72px 7%;background:linear-gradient(120deg,#ede7ff,#f7fafc)}.hero h1{font-size:clamp(32px,5vw,58px);max-width:760px;margin:0 0 12px}.hero p{max-width:720px;line-height:1.6;color:#58627a}button{cursor:pointer}.primary{background:#5b3cba;border:none;padding:14px 22px;border-radius:12px;color:white;font-weight:750}.wrap{padding:34px 7%}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}.product{background:white;border:1px solid #e4e6f1;border-radius:16px;padding:22px;box-shadow:0 8px 20px #29205008}.product .emoji{font-size:48px}.product h3{margin:10px 0}.tag{display:inline-block;background:#f2efff;color:#6046a4;padding:6px 10px;border-radius:10px;font-size:12px}footer{padding:28px 7%;border-top:1px solid #ddd;color:#68718c}#cart{margin-top:18px;background:white;border-radius:16px;padding:20px}.empty{color:#7b8196}@media(max-width:600px){.hero{padding:38px 7%}}'''

JS = r'''const cart=[];const products=[{name:'Accessoire nomade',price:24.9,emoji:'🧳'},{name:'Kit essentiel',price:34.9,emoji:'✨'},{name:'Edition premium',price:49.9,emoji:'🎁'}];const target=document.querySelector('#products');function money(v){return new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format(v)}function render(){target.innerHTML='';products.forEach((p,i)=>{const card=document.createElement('article');card.className='product';const e=document.createElement('div');e.className='emoji';e.textContent=p.emoji;const h=document.createElement('h3');h.textContent=p.name;const price=document.createElement('p');price.textContent=money(p.price);const b=document.createElement('button');b.className='primary';b.textContent='Ajouter au panier';b.addEventListener('click',()=>{cart.push(p);refreshCart()});card.append(e,h,price,b);target.append(card)});refreshCart()}function refreshCart(){const lines=document.querySelector('#cartLines');lines.innerHTML='';if(!cart.length){const p=document.createElement('p');p.className='empty';p.textContent='Votre panier est vide';lines.append(p)}else cart.forEach((p,i)=>{const line=document.createElement('p');line.textContent=p.name+' — '+money(p.price)+' ';const b=document.createElement('button');b.textContent='Retirer';b.className='pill';b.onclick=()=>{cart.splice(i,1);refreshCart()};line.append(b);lines.append(line)});document.querySelector('#total').textContent=money(cart.reduce((n,p)=>n+p.price,0))}document.querySelector('#checkout').onclick=()=>{document.querySelector('#message').textContent='Mode démonstration : aucun paiement et aucune commande réelle.'};render();'''

TASK_JS = r"""const tasks=[];const list=document.querySelector('#taskList');const input=document.querySelector('#taskText');function renderTasks(){list.innerHTML='';if(!tasks.length){const empty=document.createElement('p');empty.textContent='Aucune tâche pour le moment.';list.append(empty)}tasks.forEach((task,i)=>{const row=document.createElement('p');const toggle=document.createElement('button');toggle.className='pill';toggle.textContent=task.done?'↺ Reprendre':'✓ Terminer';toggle.onclick=()=>{task.done=!task.done;renderTasks()};const span=document.createElement('span');span.textContent=' '+task.title+' ';span.style.textDecoration=task.done?'line-through':'none';const remove=document.createElement('button');remove.className='pill';remove.textContent='Supprimer';remove.onclick=()=>{tasks.splice(i,1);renderTasks()};row.append(toggle,span,remove);list.append(row)})}document.querySelector('#addTask').onclick=()=>{const title=input.value.trim();if(!title)return;tasks.push({title,done:false});input.value='';renderTasks()};renderTasks();"""
CONTENT_JS = r"""const ideas=[];const list=document.querySelector('#contentList');const input=document.querySelector('#topicText');function renderIdeas(){list.innerHTML='';if(!ideas.length){const p=document.createElement('p');p.textContent='Aucune idée planifiée';list.append(p)}ideas.forEach((idea,i)=>{const p=document.createElement('p');p.textContent=idea+' ';const b=document.createElement('button');b.className='pill';b.textContent='Retirer';b.onclick=()=>{ideas.splice(i,1);renderIdeas()};p.append(b);list.append(p)})}document.querySelector('#addIdea').onclick=()=>{const idea=input.value.trim();if(idea){ideas.push(idea);input.value='';renderIdeas()}};renderIdeas();"""

def scaffold(db,root,project):
    base=Path(root)/'projects'/str(project['id'])
    base.mkdir(parents=True,exist_ok=True)
    name=html.escape(project['name'][:120],quote=True)
    brief=html.escape(project['brief'][:600],quote=True)
    kind=project['kind']
    if kind=='dropshipping':
        content='''<h2 id="catalogue">Notre sélection</h2><p class="empty">Produits et prix fictifs. Fournisseurs non vérifiés.</p><div class="grid" id="products"></div><section id="cart"><h2>Votre panier</h2><div id="cartLines"></div><p><strong>Total : <span id="total">0 €</span></strong></p><button id="checkout" class="primary">Simuler la commande</button><p id="message" role="status"></p></section>'''
        script=JS; label='Boutique locale'
    elif kind=='content':
        content='''<h2 id="catalogue">Calendrier éditorial</h2><p class="empty">Idées à valider ; aucune publication automatique.</p><label>Nouvelle idée<input id="topicText" placeholder="Idée de contenu"></label><button id="addIdea" class="primary">Ajouter</button><div class="product" id="contentList"></div>'''
        script=CONTENT_JS;label='Content Factory'
    else:
        content='''<h2 id="catalogue">Tableau des tâches</h2><p class="empty">Application de démonstration fonctionnelle.</p><label>Nouvelle tâche<input id="taskText" placeholder="À réaliser"></label><button id="addTask" class="primary">Ajouter</button><div class="product" id="taskList"></div>'''
        script=TASK_JS;label='Web App Factory'
    code=f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} — Démonstration</title><link href="styles.css" rel="stylesheet"></head><body data-template="{kind}"><header><div class="logo">{name}</div><a class="pill" href="#catalogue">Voir le contenu ↓</a></header><section class="hero"><span class="tag">{label} · aperçu local</span><h1>{name}</h1><p>{brief}</p><a href="#catalogue" class="primary" style="display:inline-block">Accéder à la démonstration ↓</a></section><main class="wrap">{content}</main><footer>Prototype non publié — Sécurité et conformité à vérifier avant mise en production.</footer><script src="app.js"></script></body></html>'''
    files={'index.html':code,'styles.css':STYLE,'app.js':script}
    for filename,body in files.items():
        p=base/filename
        p.write_text(body,encoding='utf-8')
        db.write('INSERT INTO artifacts(project_id,relative_path,sha256,origin,created_at) VALUES(?,?,?,?,?) ON CONFLICT(project_id,relative_path) DO UPDATE SET sha256=excluded.sha256,origin=excluded.origin,created_at=excluded.created_at',(project['id'],filename,hashlib.sha256(body.encode()).hexdigest(),'LOCAL_TEMPLATE',utc()))
    db.event('BUILD',f'Prototype {kind} généré : {len(files)} fichiers',project['id'])
    return files

def read_preview(root,project_id,filename):
    if filename not in SAFE_FILES:raise ValueError('Fichier interdit')
    path=Path(root)/'projects'/str(int(project_id))/filename
    if not path.is_file():raise FileNotFoundError(filename)
    return path.read_bytes()

def check_project(root,project_id):
    files={f:read_preview(root,project_id,f).decode('utf-8') for f in SAFE_FILES}
    try:validate_candidate(files)
    except ValueError as e:return {'ok':False,'issues':[str(e)],'files':len(files)}
    return {'ok':True,'issues':[],'files':len(files)}

# Restricted AI editing. All changes are drafts, never executed as server code.
import os,shutil
from datetime import datetime,timezone

BANNED = ('fetch(', 'xmlhttprequest', 'websocket(', 'navigator.sendbeacon', 'document.cookie',
          'localstorage.', 'sessionstorage.', 'eval(', 'new function(', '<iframe', '<object',
          'javascript:', 'onerror=', 'onload=', 'srcdoc=', 'window.open(', 'location.href',
          '<embed', 'window.location=', 'https://', 'http://', 'import(', 'process.env')

def validate_candidate(files):
    if set(files)!=SAFE_FILES:raise ValueError('Lot de fichiers incomplet (index.html, styles.css, app.js).')
    for filename,body in files.items():
        if not isinstance(body,str) or len(body.encode('utf-8'))>160000 or not body.strip():raise ValueError('Fichier vide ou trop volumineux: '+filename)
        lowered=body.lower().replace(' ','')
        if any(bad in lowered for bad in BANNED):raise ValueError('Code non autorisé détecté dans '+filename)
    html_source=files['index.html']
    if '<html' not in html_source.lower() or '<script src="app.js"' not in html_source:raise ValueError('HTML ou script local manquant')
    if 'data-template="dropshipping"' in html_source: required=('id="products"','id="cartLines"','id="checkout"','id="total"');logic='refreshCart()'
    elif 'data-template="content"' in html_source: required=('id="contentList"','id="topicText"','id="addIdea"');logic='renderIdeas()'
    elif 'data-template="webapp"' in html_source or 'data-template="general"' in html_source or 'data-template="services"' in html_source: required=('id="taskList"','id="taskText"','id="addTask"');logic='renderTasks()'
    else:raise ValueError('Marqueur de template manquant ou altéré')
    if any(item not in html_source for item in required):raise ValueError('Contrat fonctionnel incomplet')
    if logic not in files['app.js']:raise ValueError('Logique interactive manquante')
    return {'ok':True,'files':3}

def apply_candidate(db,root,project_id,files):
    validate_candidate(files)
    home=Path(root)
    folder=home/'projects'/str(int(project_id))
    if not folder.is_dir():raise ValueError('Générer le prototype initial avant toute modification.')
    before={name:(folder/name).read_bytes() for name in SAFE_FILES}
    checkpoints=home/'checkpoints'/str(project_id)
    checkpoints.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    snapshot=checkpoints/stamp
    snapshot.mkdir(parents=True)
    for name,contents in before.items():(snapshot/name).write_bytes(contents)
    staged=folder/'_candidate'
    if staged.exists():shutil.rmtree(staged)
    staged.mkdir()
    try:
        for name,contents in files.items():(staged/name).write_text(contents,encoding='utf-8')
        # Generated JS must be parsed independently before automatic application.
        import shutil as _shutil, subprocess
        node=_shutil.which('node')
        if node is None:raise ValueError('Node.js absent : modification IA non appliquée automatiquement (lint JavaScript requis).')
        try:
            check=subprocess.run([node,'--check',str(staged/'app.js')],capture_output=True,text=True,timeout=10,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise ValueError('Analyse JavaScript indisponible.') from exc
        if check.returncode!=0:raise ValueError('Syntaxe JavaScript incorrecte : '+check.stderr[:300])
        # Transaction at filesystem level is not atomic across all files; restore on partial failure.
        for name in SAFE_FILES:os.replace(staged/name,folder/name)
        for name,body in files.items():
            db.write('INSERT INTO artifacts(project_id,relative_path,sha256,origin,created_at) VALUES(?,?,?,?,?) ON CONFLICT(project_id,relative_path) DO UPDATE SET sha256=excluded.sha256,origin=excluded.origin,created_at=excluded.created_at',(project_id,name,hashlib.sha256(body.encode()).hexdigest(),'LOCAL_MODEL_VALIDATED',utc()))
        db.event('PATCH',f'3 fichiers mis à jour, sauvegarde locale {snapshot.name}',project_id)
        return {'applied':True,'checkpoint':snapshot.name}
    except Exception:
        for name,contents in before.items():(folder/name).write_bytes(contents)
        raise
    finally:
        if staged.exists():shutil.rmtree(staged)

def restore_checkpoint(db,root,project_id,checkpoint):
    if not re.fullmatch(r'\d{8}_\d{6}_\d{6}',checkpoint):raise ValueError('Identifiant de sauvegarde incorrect')
    base=Path(root)/'checkpoints'/str(int(project_id))/checkpoint
    if not base.is_dir():raise ValueError('Version de sauvegarde introuvable')
    files={name:(base/name).read_text(encoding='utf-8') for name in SAFE_FILES}
    validate_candidate(files)
    return apply_candidate(db,root,project_id,files)
