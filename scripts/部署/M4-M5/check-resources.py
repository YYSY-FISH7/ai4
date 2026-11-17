"""Verify supplied M4 assets without installing/importing any third-party code."""
import argparse,hashlib,json,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--model',type=Path)
 p.add_argument('--wheelhouse',type=Path)
 a=p.parse_args()
 if not a.model and not a.wheelhouse:p.error('Specify --model and/or --wheelhouse')
 manifest=json.loads((Path(__file__).resolve().parent/'resources/RESOURCE_MANIFEST.json').read_text(encoding='utf-8'))
 checked=[]
 for row in manifest['files']:
  rel=Path(row['path'])
  if rel.suffix=='.onnx':f=a.model
  elif rel.suffix=='.whl':f=a.wheelhouse/rel.name if a.wheelhouse else None
  else:raise ValueError('Unexpected manifest entry')
  if f is None:continue
  if not f.is_file():raise ValueError('Missing asset: '+str(f))
  if f.stat().st_size!=row['bytes']:raise ValueError('Size mismatch: '+str(f))
  h=hashlib.sha256()
  with f.open('rb') as stream:
   for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
  if h.hexdigest()!=row['sha256']:raise ValueError('SHA-256 mismatch: '+str(f))
  checked.append({'name':rel.name,'bytes':row['bytes'],'sha256':row['sha256']})
 print(json.dumps({'verified':checked,'third_party_code_executed':False},ensure_ascii=False,indent=2))

if __name__=='__main__':
 try:main()
 except (OSError,ValueError) as e:
  print('Resource check failed: '+str(e),file=sys.stderr)
  sys.exit(2)
