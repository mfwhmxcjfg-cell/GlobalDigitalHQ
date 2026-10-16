"""Bounded public HTTPS client: DNS-pinned connections, no proxy or redirects."""
import http.client, ipaddress, json, socket, ssl, time
from urllib.parse import urlsplit

class ConnectorError(RuntimeError):
    pass


def endpoint(url, local=False):
    u=urlsplit(url)
    if len(url)>3000 or any(ord(c)<32 for c in url) or u.username or u.password or u.fragment or not u.hostname:
        raise ValueError('URL invalide ou contenant des identifiants')
    islocal=u.hostname=='127.0.0.1' and u.scheme=='http' and local
    if not islocal and (u.scheme!='https' or u.port not in (None,443)):
        raise ValueError('HTTPS public sur le port 443 requis')
    if islocal and (not u.port or u.port in (80,443,8824)):
        raise ValueError('Port du service local invalide')
    return u


def public_addresses(host):
    answers=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    addresses=list(dict.fromkeys(a[4][0] for a in answers))
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ConnectorError('Adresse réseau privée ou réservée refusée')
    return addresses


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,address,timeout):
        super().__init__(host,timeout=timeout,context=ssl.create_default_context())
        self.address=address
    def connect(self):
        raw=socket.create_connection((self.address,443),self.timeout)
        try:self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except BaseException:raw.close();raise


def fetch(url,headers=None,payload=None,local=False,max_bytes=1_000_000,rpc_id=None):
    u=endpoint(url,local)
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    h={'User-Agent':'GlobalDigitalHQ/1.5 (owner-operated research)','Accept':'application/json,text/html,text/plain','Accept-Encoding':'identity'}
    h.update(headers or {})
    if data is not None:h['Content-Type']='application/json'
    # Pin exactly the address validated above; TLS still verifies the original host.
    try:
        conn=http.client.HTTPConnection('127.0.0.1',u.port,timeout=30) if local and u.hostname=='127.0.0.1' else PinnedHTTPS(u.hostname,public_addresses(u.hostname)[0],30)
        try:
            conn.request('GET' if data is None else 'POST',u.path+('?' + u.query if u.query else ''),body=data,headers=h)
            response=conn.getresponse();rh={k.lower():v for k,v in response.getheaders()}
            if not 200<=response.status<300:raise ConnectorError('HTTP '+str(response.status)+' ; aucune relance automatique')
            if 'text/event-stream' in rh.get('content-type','') and rpc_id is not None:
                start=time.monotonic();raw=bytearray();event=[];total=0
                while time.monotonic()-start<45:
                    line=response.readline(max_bytes+1);total+=len(line)
                    if total>max_bytes:raise ConnectorError('Flux MCP trop volumineux')
                    if not line:break
                    if line.strip()==b'':
                        if event:
                            try:obj=json.loads(b'\n'.join(event))
                            except ValueError:obj={}
                            if obj.get('id')==rpc_id and ('result' in obj or 'error' in obj):
                                return json.dumps(obj).encode(),rh
                        event=[]
                    elif line.startswith(b'data:'):event.append(line[5:].strip())
                raise ConnectorError('Réponse MCP absente ou flux interrompu')
            raw=response.read(max_bytes+1)
            if len(raw)>max_bytes:raise ConnectorError('Réponse trop volumineuse')
            return raw,rh
        finally:conn.close()
    except ConnectorError:raise
    except Exception as exc:
        # Never include URLs, headers, keys or provider response bodies in error logs.
        raise ConnectorError('Connexion impossible : '+type(exc).__name__) from None
