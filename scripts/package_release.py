"""Build a reproducible source package without private runtime state."""
from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parent.parent

def build(output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    files=[]
    for area in ('gdhq','seed','web','scripts','tests','docs','third_party','.github'):
        files.extend(p for p in (ROOT/area).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    files.extend(p for p in ROOT.iterdir() if p.is_file() and (p.suffix in ('.md','.cmd') or p.name in ('MANIFEST.sha256','requirements-sdk.txt')))
    for f in files:
        if f.is_symlink():raise ValueError('Symlink excluded')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for f in sorted(files):archive.write(f,'GlobalDigitalHQ/'+f.relative_to(ROOT).as_posix())
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n')
    return {'package':output.name,'files':len(files),'sha256':digest}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='dist/GlobalDigitalHQ_1_5_0.zip');a=ap.parse_args()
    print(json.dumps(build(a.output)))
