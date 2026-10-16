from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent

def data_dir():
    given = os.environ.get('GDHQ_DATA_DIR', '').strip()
    if given:
        return Path(given).expanduser().resolve()
    return (Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local' / 'share') / 'GlobalDigitalHQ_Next' / 'data').resolve()


def local_endpoint(url):
    from urllib.parse import urlsplit
    split = urlsplit(url)
    if split.scheme != 'http' or split.username or split.password or split.hostname not in ('127.0.0.1','::1') or split.query or split.fragment:
        raise ValueError('Seule une URL HTTP de boucle locale est autorisée pour les modèles IA.')
    if split.port not in (1234, 11434):
        raise ValueError('Port de modèle local non approuvé.')
    return url.rstrip('/')
