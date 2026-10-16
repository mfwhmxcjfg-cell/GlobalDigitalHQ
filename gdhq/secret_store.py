"""Windows DPAPI user-bound key storage. Never expose plaintext in API responses."""
import ctypes,json,os,re,threading
from pathlib import Path
from ctypes import wintypes
LOCK=threading.RLock()

def crypt(data,encrypt):
    if os.name!='nt':raise ValueError('Coffre intégré disponible sous Windows ; ailleurs utiliser les variables d’environnement')
    class Blob(ctypes.Structure):_fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    buf=ctypes.create_string_buffer(data);source=Blob(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte)));out=Blob()
    dll=ctypes.windll.crypt32;fn=dll.CryptProtectData if encrypt else dll.CryptUnprotectData
    # CRYPTPROTECT_UI_FORBIDDEN; no machine-wide flag: bound to this Windows account.
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out)):raise ValueError('Coffre Windows indisponible pour ce compte')
    try:return ctypes.string_at(out.pbData,out.cbData)
    finally:ctypes.windll.kernel32.LocalFree(out.pbData)

def load(home):
    path=Path(home)/'credentials.dpapi'
    if not path.exists():return {}
    return json.loads(crypt(path.read_bytes(),False))

def save(home,name,value):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{1,69}_(KEY|TOKEN|SECRET)',name):raise ValueError('Nom de clé invalide')
    if not isinstance(value,str) or not 1<=len(value)<=5000 or '\n' in value or '\r' in value:raise ValueError('Clé invalide')
    with LOCK:
        data=load(home);data[name]=value
        encrypted=crypt(json.dumps(data).encode(),True)
        path=Path(home)/'credentials.dpapi';temp=path.with_suffix('.tmp');temp.write_bytes(encrypted);temp.replace(path)
        os.environ[name]=value
    return {'saved':True,'name':name,'storage':'WINDOWS_DPAPI_CURRENT_USER'}
