#!/usr/bin/env python3
"""Plan or install public map dependencies offline, separately from private data."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_volume import plan, install, MAX_MANIFEST_BYTES

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('plan','install','publish'))
    p.add_argument('--config',type=Path)
    p.add_argument('--source-root',type=Path)
    p.add_argument('--manifest',type=Path)
    p.add_argument('--publication-root',type=Path)
    p.add_argument('--generation')
    p.add_argument('--restore-timestamps',action='store_true',help='Restore index mtimes from the sealed import manifest')
    p.add_argument('--destination',type=Path)
    p.add_argument('--link',action='store_true',help='Reuse public files on the same disk; mount read-only')
    a=p.parse_args()
    if a.action=='publish':
        if not a.publication_root or not a.generation: p.error('publication-root and generation required')
        from rainmapper_core.mushroom_map_geography_runtime import publish
        print(json.dumps(publish(a.publication_root,a.generation,restore_timestamps=a.restore_timestamps)))
        return
    if not a.source_root or not a.manifest: p.error('source-root and manifest required')
    if a.action=='plan':
        if not a.config or a.manifest.exists(): p.error('config required; manifest must be new')
        data=plan(json.loads(a.config.read_text()),a.source_root)
        a.manifest.parent.mkdir(parents=True,exist_ok=True)
        a.manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:data[k] for k in ('format','file_count','bytes')}))
    else:
        if not a.destination: p.error('destination required')
        if a.manifest.stat().st_size>MAX_MANIFEST_BYTES: p.error('manifest too large')
        print(json.dumps(install(json.loads(a.manifest.read_text()),a.source_root,a.destination,link=a.link)))

if __name__=='__main__': main()
