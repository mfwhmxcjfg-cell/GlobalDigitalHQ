from pathlib import Path
import hashlib,sys
root=Path(__file__).resolve().parent.parent
manifest=root/'MANIFEST.sha256'
missing=[];bad=[];checked=0
for line in manifest.read_text(encoding='utf-8').splitlines():
    if '  ' not in line: continue
    expected,name=line.split('  ',1)
    file=root/name
    if not file.is_file(): missing.append(name); continue
    checked+=1
    if hashlib.sha256(file.read_bytes()).hexdigest()!=expected: bad.append(name)
print(f'Empreintes : {checked} fichiers valides; absents={len(missing)}; modifies={len(bad)}')
if missing or bad:
    print('Fichiers invalides :',', '.join((missing+bad)[:15]))
    sys.exit(1)
