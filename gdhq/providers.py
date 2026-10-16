"""Local inference ONLY. Never route to remote models or billable APIs."""
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler
from urllib.error import URLError, HTTPError
import json,socket
from .settings import local_endpoint

class ModelUnavailable(RuntimeError): pass

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ModelUnavailable('Redirection interdite par la politique LOCAL_ONLY')

class LMStudio:
    def __init__(self,url='http://127.0.0.1:1234/v1',timeout=90):
        self.url=local_endpoint(url)
        self.timeout=timeout
    def _request(self,path,payload=None):
        data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
        req=Request(self.url+path,data=data,headers={'Content-Type':'application/json','Accept':'application/json'})
        try:
            with build_opener(ProxyHandler({}),_NoRedirect()).open(req, timeout=self.timeout) as res:
                if res.status!=200:raise ModelUnavailable('LM Studio HTTP '+str(res.status))
                raw=res.read(1024*1024+1)
                if len(raw)>1024*1024:raise ModelUnavailable('Réponse IA trop volumineuse')
                return json.loads(raw.decode('utf-8'))
        except (URLError,TimeoutError,socket.timeout,ValueError,json.JSONDecodeError,HTTPError) as exc:
            raise ModelUnavailable(f'Moteur local inaccessible : {type(exc).__name__}') from exc
    def models(self):
        data=self._request('/models')
        return [i['id'] for i in data.get('data',[]) if isinstance(i,dict) and isinstance(i.get('id'),str)]
    def chat(self,system,user,model,max_tokens=1100):
        if not model or not isinstance(model,str):raise ModelUnavailable('Sélectionne un modèle dans LM Studio.')
        data=self._request('/chat/completions',{'model':model,'messages':[{'role':'system','content':system[:10000]},{'role':'user','content':user[:18000]}], 'temperature':0.2,'max_tokens':max_tokens,'stream':False})
        try:
            content=data['choices'][0]['message']['content']
            if not isinstance(content,str) or not content.strip():raise ValueError('empty')
            return content.strip()
        except (KeyError,IndexError,TypeError,ValueError) as exc:
            raise ModelUnavailable('Le modèle ne renvoie pas de texte exploitable.') from exc

class Ollama(LMStudio):
    """Ollama local OpenAI compatibility. No pull, cloud routing or tool execution."""
    def __init__(self,url='http://127.0.0.1:11434/v1',timeout=90):
        super().__init__(url,timeout)
    def models(self):
        return [m for m in super().models() if not self._cloud(m)]
    @staticmethod
    def _cloud(model):
        return 'cloud' in model.lower() or '/' in model or '://' in model
    def chat(self,system,user,model,max_tokens=1100):
        if not isinstance(model,str) or not model or self._cloud(model):
            raise ModelUnavailable('Choisir un modèle Ollama local, sans routage cloud.')
        if model not in self.models():raise ModelUnavailable('Modèle non chargé dans Ollama local.')
        return super().chat(system,user,model,max_tokens)
