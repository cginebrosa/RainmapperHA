"""Copy publicly linked GBIF photos to a resumable local research archive."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    root = args.snapshot
    media_dir = root / 'media'
    media_dir.mkdir(exist_ok=True)
    records = json.loads((root / 'occurrences.json').read_text())
    photos, references = {}, []
    for row in records:
        for index, media in enumerate(row.get('media', [])):
            if media.get('type') != 'StillImage':
                continue
            url = media.get('identifier', '')
            reference = {'gbifID': row['key'], 'media_index': index, 'url': url,
                         'metadata': media, 'photo_id': sha(url.encode())}
            references.append(reference)
            photos.setdefault(url, {'url': url, 'photo_id': reference['photo_id']})
    dump(media_dir / 'references.json', references)
    previous = {}
    if (media_dir / 'index.json').exists():
        previous = {p['url']: p for p in json.loads((media_dir / 'index.json').read_text())}
    lock = threading.Lock()
    next_request = [0.0]
    total_bytes = [0]
    max_total = 15 * 1024**3
    max_file = 100 * 1024**2
    # URLs come directly from the occurrence media fields, never guessed variants.
    hosts = {urllib.parse.urlparse(url).hostname for url in photos}
    print(f'{len(records)} records; {len(photos)} unique photo URLs; hosts {sorted(hosts)}', flush=True)

    def download(photo):
        url = photo['url']
        old = previous.get(url)
        if old and old.get('status') == 'downloaded':
            path = root / old['path']
            if path.is_file() and sha(path.read_bytes()) == old['sha256']:
                with lock:
                    total_bytes[0] += old['bytes']
                return old
        result = {**photo, 'attempted_at': utc()}
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return {**result, 'status': 'error', 'error': 'Unsupported public photo URL'}
        for attempt in range(3):
            with lock:
                wait = max(0, next_request[0] - time.monotonic())
                next_request[0] = time.monotonic() + wait + .15
            if wait:
                time.sleep(wait)
            try:
                request = urllib.request.Request(url, headers={
                    'User-Agent': 'Rainmapper-GBIF-local-research/1.0', 'Accept': 'image/*'})
                with urllib.request.urlopen(request, timeout=40) as response:
                    body = response.read(max_file + 1)
                    content_type = response.headers.get_content_type()
                    final_url = response.url
                if len(body) > max_file:
                    raise ValueError('Photo exceeds 100 MiB bound')
                if body.startswith(b'\xff\xd8\xff'):
                    extension = '.jpg'
                elif body.startswith(b'\x89PNG\r\n\x1a\n'):
                    extension = '.png'
                elif body.startswith((b'GIF87a', b'GIF89a')):
                    extension = '.gif'
                elif body[:4] == b'RIFF' and body[8:12] == b'WEBP':
                    extension = '.webp'
                else:
                    raise ValueError(f'Unrecognized image bytes ({content_type})')
                with lock:
                    if total_bytes[0] + len(body) > max_total:
                        raise ValueError('Photo collection exceeds 15 GiB bound')
                    total_bytes[0] += len(body)
                path = media_dir / (photo['photo_id'] + extension)
                path.write_bytes(body)
                return {**result, 'status': 'downloaded', 'path': str(path.relative_to(root)),
                        'bytes': len(body), 'sha256': sha(body), 'content_type': content_type,
                        'final_url': final_url, 'completed_at': utc()}
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
                retryable = not isinstance(error, (urllib.error.HTTPError, ValueError)) or (
                    isinstance(error, urllib.error.HTTPError) and error.code in (429, 500, 502, 503, 504))
                if retryable and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                return {**result, 'status': 'error', 'error': str(error), 'attempts': attempt + 1}

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(download, p) for p in photos.values()]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            if len(results) % 25 == 0 or len(results) == len(photos):
                dump(media_dir / 'index.json', sorted(results, key=lambda p: p['url']))
                counts = Counter(r['status'] for r in results)
                print(f'Photos {len(results)}/{len(photos)}: {dict(counts)}; '
                      f'{total_bytes[0] / 1024**2:.1f} MiB', flush=True)
    dump(media_dir / 'summary.json', {'completed_at': utc(), 'unique_urls': len(photos),
         'references': len(references), 'statuses': dict(Counter(r['status'] for r in results)),
         'bytes': total_bytes[0], 'hosts': sorted(hosts),
         'note': 'Photo licenses and attribution remain in references.json; occurrence licenses may differ.'})

    # No external libraries, scripts, fonts, tiles or image requests: file:// works offline.
    by_url = {p['url']: p for p in results}
    rows = {str(r['key']): r for r in records}
    e = lambda value: html.escape(str(value if value is not None else 'desconocida'), quote=True)
    sections = ['<!doctype html><html lang="es"><meta charset="utf-8"><title>GBIF · fotos locales</title>',
                '<style>body{font:16px system-ui;max-width:1200px;margin:2em auto;padding:1em}'
                'article{border-bottom:1px solid #aaa;padding:1em 0}img{max-width:240px;max-height:200px}'
                'figure{display:inline-block;vertical-align:top;width:260px;margin:8px}'
                'figcaption{font-size:12px;overflow-wrap:anywhere}input{padding:10px;width:90%}</style>',
                '<h1>GBIF · investigación local</h1><p>Catalunya · 19/06/2012–16/09/2026. '
                'Fotografías originales accesibles, con autoría y licencia. Incertidumbre desconocida ≠ 0 m.</p>',
                '<p><a href="review.csv">Tabla CSV</a> · <a href="occurrences.json">Registros completos</a> · '
                '<a href="metadata/taxonomy-map.json">Correspondencias taxonómicas</a></p>',
                '<input id="filter" placeholder="Filtrar por especie, fecha o GBIF ID" aria-label="Filtrar">']
    grouped = {}
    for ref in references:
        grouped.setdefault(str(ref['gbifID']), []).append(ref)
    for key, row in sorted(rows.items(), key=lambda kv: (kv[1].get('species', ''), kv[1].get('eventDate', ''))):
        name = row.get('species', row.get('scientificName', ''))
        sections.append(f'<article><h2>{e(name)} · {e(row.get("eventDate"))} · {e(key)}</h2>'
                        f'<p>Incertidumbre (m): {e(row.get("coordinateUncertaintyInMeters"))} · '
                        f'Coordenadas: {e(row.get("decimalLatitude"))}, {e(row.get("decimalLongitude"))}</p>'
                        f'<a href="raw/verbatim/{e(key)}.json">Registro original</a>')
        if not grouped.get(key):
            sections.append('<p>Sin fotografía enlazada en GBIF.</p>')
        for ref in grouped.get(key, []):
            result = by_url[ref['url']]
            meta = ref['metadata']
            sections.append('<figure>')
            if result['status'] == 'downloaded':
                sections.append(f'<a href="{e(result["path"])}"><img loading="lazy" src="{e(result["path"])}" '
                                f'alt="{e(name)}"></a>')
            else:
                sections.append(f'<p>Foto no descargada: {e(result.get("error"))}</p>')
            sections.append(f'<figcaption>{e(meta.get("creator", meta.get("rightsHolder")))}<br>'
                            f'{e(meta.get("license"))}</figcaption></figure>')
        sections.append('</article>')
    sections.append('<script>document.getElementById("filter").addEventListener("input",function(){'
                    'const q=this.value.toLowerCase();document.querySelectorAll("article").forEach('
                    'a=>a.hidden=!a.textContent.toLowerCase().includes(q))});</script></html>')
    (root / 'index.html').write_text('\n'.join(sections))


if __name__ == '__main__':
    main()
