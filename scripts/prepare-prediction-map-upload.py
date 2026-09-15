#!/usr/bin/env python3
"""Prepare a portable geography archive on the workstation, never on a map click."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_geography_runtime import checked_manifest, read_json, encode, fingerprint
from rainmapper_core.mushroom_map_volume import MAX_MANIFEST_BYTES, local


class HashWriter:
    def __init__(self, stream):
        self.stream, self.check, self.size = stream, hashlib.sha256(), 0
    def write(self, raw):
        self.check.update(raw); self.size += len(raw)
        return self.stream.write(raw)
    def flush(self): self.stream.flush()


def prepare(publication_root, generation, destination):
    source = local(Path(publication_root).resolve(), 'generations/'+generation)
    manifest = checked_manifest(read_json(source/'manifest.json', MAX_MANIFEST_BYTES))
    destination = Path(destination)
    if destination.exists():
        raise ValueError('upload_archive_already_exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name+'.preparing')
    prefix = 'generations/'+generation+'/'
    with temporary.open('xb') as out:
        writer = HashWriter(out)
        with gzip.GzipFile(filename='', mode='wb', fileobj=writer, compresslevel=1, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                for row in manifest['files']:
                    path = local(source, row['path']); stat = path.stat()
                    if (stat.st_size, stat.st_mtime_ns) != (row['bytes'], row['mtime_ns']):
                        raise ValueError('upload_source_changed:'+row['path'])
                    info = tarfile.TarInfo(prefix+row['path']); info.size = row['bytes']; info.mode = 0o644
                    ns = row['mtime_ns']; info.pax_headers = {'mtime': f'{ns//10**9}.{ns%10**9:09d}'}
                    with path.open('rb') as stream: archive.addfile(info, stream)
                    if (path.stat().st_size, path.stat().st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
                        raise ValueError('upload_source_changed:'+row['path'])
                extras = {
                    prefix+'manifest.json': encode(manifest),
                    'SHA256SUMS': ''.join(r['sha256']+'  '+prefix+r['path']+'\n' for r in manifest['files']).encode(),
                    # Deliberately not CURRENT.json: activation happens after full extraction.
                    'publication.json': encode({'format':'map_geography_publication_v1','generation':generation,'fingerprint':fingerprint(manifest)}),
                }
                for path, raw in extras.items():
                    info = tarfile.TarInfo(path); info.size = len(raw); info.mode = 0o644
                    archive.addfile(info, io.BytesIO(raw))
        writer.flush(); os.fsync(out.fileno())
    os.replace(temporary, destination)
    receipt = {'archive':destination.name, 'sha256':writer.check.hexdigest(), 'archive_bytes':writer.size,
               'files':manifest['file_count'], 'uncompressed_asset_bytes':manifest['bytes'],
               'fingerprint':fingerprint(manifest), 'asset_hashes_reused':True}
    destination.with_suffix(destination.suffix+'.json').write_text(json.dumps(receipt,indent=2)+'\n')
    destination.with_suffix(destination.suffix+'.sha256').write_text(receipt['sha256']+'  '+destination.name+'\n')
    return receipt


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--publication-root', type=Path, required=True)
    p.add_argument('--generation', required=True)
    p.add_argument('--destination', type=Path, required=True)
    args=p.parse_args()
    print(json.dumps(prepare(args.publication_root, args.generation, args.destination)), flush=True)
