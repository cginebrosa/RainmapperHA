"""Synchronize active immutable weather files into a specified local data root."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import os

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--reuse',type=Path,action='append',default=[])
    parser.add_argument('--report',type=Path,default=Path('docker-data/diagnostics/rainfall-qc/snapshot-copy.json'))
    args=parser.parse_args()
    if args.target.resolve()==args.source.resolve():
        raise SystemExit('Source and destination must be different')
    current_bytes=(args.source/'CURRENT.json').read_bytes()
    current=json.loads(current_bytes)
    manifest_bytes=(args.source/current['manifest_path']).read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest()==current['manifest_sha256']
    manifest=json.loads(manifest_bytes)
    reused={}
    roots=([args.target] if (args.target/'CURRENT.json').is_file() else [])+args.reuse
    for root in roots:
        c=json.loads((root/'CURRENT.json').read_text())
        m=json.loads((root/c['manifest_path']).read_text())
        for entry in [m['catalog'],*m['partitions']]:
            reused.setdefault(entry['sha256'],root/entry['path'])
    journal=[]
    for entry in [manifest['catalog'],*manifest['partitions']]:
        rel=Path(entry['path'])
        assert not rel.is_absolute() and '..' not in rel.parts
        cached=reused.get(entry['sha256'])
        if cached is not None and cached.is_file() and sha(cached)==entry['sha256']:
            source=cached;mode='local_reuse'
        else:
            source=args.source/rel;mode='download'
        dest=args.target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if source.resolve()!=dest.resolve():
            temporary=dest.with_suffix(dest.suffix+'.qc-sync')
            shutil.copyfile(source,temporary)
            assert sha(temporary)==entry['sha256']
            os.replace(temporary,dest)
        assert sha(dest)==entry['sha256']
        journal.append({'path':str(rel),'bytes':dest.stat().st_size,'mode':mode,'sha256':entry['sha256']})
    dest=args.target/current['manifest_path'];dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(manifest_bytes)
    temporary=args.target/'CURRENT.json.qc-sync';temporary.write_bytes(current_bytes)
    os.replace(temporary,args.target/'CURRENT.json')
    report={'generation_id':current['generation_id'],'source':str(args.source),'files':journal,'source_current_unchanged':(args.source/'CURRENT.json').read_bytes()==current_bytes,'downloaded_bytes':sum(x['bytes'] for x in journal if x['mode']=='download'),'reused_bytes':sum(x['bytes'] for x in journal if x['mode']=='local_reuse')}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))

if __name__=='__main__':main()
