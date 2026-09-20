#!/usr/bin/env python3
"""Loopback-only station research; never writes operational Rainmapper catalogs."""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
STATES = ('pending', 'doubtful', 'accepted', 'rejected')
ASSETS = Path(__file__).with_name('web')
VENDOR = Path(__file__).with_name('vendor')
DATA = Path(__file__).resolve().parents[1] / 'data'


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def summarize(rows, start, end):
    days = {}
    last = None
    altitude = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        stamp = str(row.get('obsTimeLocal') or '')
        try:
            day = date.fromisoformat(stamp[:10])
        except ValueError:
            continue
        if not start <= day <= end:
            continue
        if last is None or stamp > last:
            last = stamp
        metric = row.get('metric') or {}
        elev = metric.get('elev')
        if valid_number(elev):
            altitude = elev
        rain = metric.get('precipTotal')
        if valid_number(rain) and rain >= 0:
            days[day.isoformat()] = rain
    return dict(days=len(days), window=30, start=str(start), end=str(end),
                last_reading=last, altitude_m=altitude, rainfall_mm=days,
                fetched_at=datetime.now(timezone.utc).isoformat())


class Research:
    def __init__(self, root, fetch=None, place_fetch=None):
        self.root = Path(root)
        self.lock = threading.RLock()
        self.network_lock = threading.Lock()
        self.history_lock = threading.Lock()
        self.last_request = 0
        self.fetch = fetch or self.request
        self.place_fetch = place_fetch or self.request_places
        self.place_lock = threading.Lock()
        self.last_place_request = 0
        self.db = sqlite3.connect(self.root / 'research.sqlite3', check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT, review TEXT, data TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, data TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS audit (at TEXT, id TEXT, action TEXT, value TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS queries (key TEXT PRIMARY KEY, lat REAL, lon REAL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
        if not self.db.execute("SELECT value FROM metadata WHERE key='searches_seeded'").fetchone():
            for i, point in enumerate(self.load('search-points.json')):
                self.db.execute('INSERT OR IGNORE INTO queries VALUES (?,?,?)', (f'baseline:{i}', point['lat'], point['lon']))
            self.db.execute("INSERT INTO metadata VALUES ('searches_seeded','true')")
        for row in self.load('candidates.json'):
            self.db.execute('INSERT OR IGNORE INTO records VALUES (?,?,?,?)',
                            (row['stationId'], 'candidate', 'pending', json.dumps(row)))
        self.db.commit()
        self.stations = self.load('stations.json')
        self.baseline = self.load('baseline-summary.json')
        self.known = set(self.baseline.get('known_wu', []))
        self.excluded = set(self.baseline.get('excluded_codes', [])) | set(self.baseline.get('disabled_wu', []))
        self.current = (self.known - self.excluded) | {
            s['id'] for s in self.stations if s['source'] == 'Wunderground'
        }
        self.station_days = self.local_availability()

    def load(self, name):
        return json.loads((self.root / name).read_text())

    def local_availability(self):
        target = self.root / 'existing-availability-30.json'
        if target.exists():
            return json.loads(target.read_text())
        result = {}
        for spec in self.baseline.get('inputs', []):
            path = ROOT / spec['path']
            if not path.exists():
                continue
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != spec['sha256']:
                continue  # Never silently substitute a newer operational snapshot.
            data = json.loads(raw)
            end = datetime.fromisoformat(data['metadata']['generated_at']).date() - timedelta(days=1)
            start = end - timedelta(days=29)
            for feature in data['features']:
                props = feature['properties']
                rows = []
                for i in range(1, 91):
                    try:
                        day = datetime.strptime(props.get(f'Data_Pluja_{i:02}') or '', '%d/%m/%Y').date()
                    except ValueError:
                        continue
                    rows.append({'obsTimeLocal': str(day), 'metric': {'precipTotal': props.get(f'Pluja_Diaria_{i:02}')}})
                key = props['Source'] + ':' + str(props['Codi Estació']).upper()
                result[key] = summarize(rows, start, end)
                result[key]['origin'] = 'Base local del 17/09/2026; no es una consulta en vivo'
        target.write_text(json.dumps(result, ensure_ascii=False))
        return result

    def cache_get(self, key):
        with self.lock:
            row = self.db.execute('SELECT data FROM cache WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key, data):
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO cache VALUES (?,?)', (key, json.dumps(data)))

    def request(self, endpoint, params):
        import requests
        from rainmapper_core.sources.wunderground.daily_api import daily_api_key
        with self.network_lock:
            time.sleep(max(0, 0.4 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                response = requests.get('https://api.weather.com/' + endpoint,
                    params={**params, 'apiKey': daily_api_key(), 'format': 'json'},
                    headers={'Accept-Encoding': 'gzip'}, timeout=(5, 20))
                if response.status_code == 204:
                    return {}
                if response.status_code != 200:
                    raise ValueError(f'Wunderground devuelve HTTP {response.status_code}; no se puede evaluar disponibilidad.')
                return response.json()
            except (requests.RequestException, requests.exceptions.JSONDecodeError):
                raise ValueError('No se pudo consultar Wunderground (red, tiempo de espera o respuesta inválida). Reintenta.') from None

    def request_places(self, params):
        import requests
        try:
            response = requests.get('https://photon.komoot.io/api/', params=params,
                headers={'User-Agent': 'RainmapperStationResearch/1.0', 'Accept': 'application/json'},
                timeout=(5, 15))
            if response.status_code != 200:
                raise ValueError(f'El buscador de lugares devuelve HTTP {response.status_code}. Reintenta más tarde.')
            return response.json()
        except requests.RequestException:
            raise ValueError('No se pudo consultar el buscador de lugares. Comprueba la conexión y reintenta.') from None

    def search_places(self, query, lat=None, lon=None):
        if not isinstance(query, str):
            raise ValueError('Escribe un municipio o topónimo.')
        query = ' '.join(query.split())
        if not 2 <= len(query) <= 160:
            raise ValueError('Escribe entre 2 y 160 caracteres para buscar un lugar.')
        params = {'q': query, 'limit': 8}
        if lat is not None or lon is not None:
            if not (valid_number(lat) and valid_number(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError('Centro del mapa inválido.')
            # Bias toward the viewport, without restricting searches to that region.
            params.update(lat=round(lat, 1), lon=round(lon, 1))
        key = 'places:photon:v1:' + json.dumps({**params, 'q': query.casefold()}, sort_keys=True)
        with self.place_lock:
            cached = self.cache_get(key)
            if cached is not None:
                return cached
            time.sleep(max(0, 1 - (time.monotonic() - self.last_place_request)))
            self.last_place_request = time.monotonic()
            payload = self.place_fetch(params)
            if not isinstance(payload, dict) or not isinstance(payload.get('features'), list):
                raise ValueError('Respuesta inválida del buscador de lugares. Reintenta.')
            results = []
            for feature in payload['features'][:8]:
                if not isinstance(feature, dict):
                    continue
                geometry, props = feature.get('geometry'), feature.get('properties')
                if not isinstance(geometry, dict) or not isinstance(props, dict):
                    continue
                coords = geometry.get('coordinates')
                if geometry.get('type') != 'Point' or not isinstance(coords, list) or len(coords) != 2:
                    continue
                x, y = coords
                if not (valid_number(x) and valid_number(y) and -180 <= x <= 180 and -90 <= y <= 90):
                    continue
                parts = list(dict.fromkeys(v for field in ('name', 'city', 'county', 'state', 'country')
                    if isinstance(v := props.get(field), str) and v.strip()))
                if not parts:
                    continue
                results.append({'name': parts[0], 'label': ' · '.join(parts), 'lon': x, 'lat': y,
                    'zoom': {'country': 5, 'state': 8, 'county': 10, 'city': 12}.get(props.get('type'), 14)})
            if payload['features'] and not results:
                raise ValueError('El buscador no devolvió coordenadas utilizables. Reintenta.')
            result = {'results': results}
            self.cache_put(key, result)
            return result

    def records(self, include_current=False):
        with self.lock:
            return [dict(json.loads(data), kind=kind, review_status=review)
                    for station, kind, review, data in self.db.execute('SELECT * FROM records')
                    if include_current or station not in self.current]

    def get(self, station):
        if not isinstance(station, str) or not re.fullmatch(r'[A-Z0-9_-]{1,50}', station):
            raise ValueError('Identificador de estación inválido.')
        with self.lock:
            row = self.db.execute('SELECT kind,review,data FROM records WHERE id=?', (station,)).fetchone()
        if not row:
            raise ValueError('Estación no recuperada por esta investigación.')
        return dict(json.loads(row[2]), kind=row[0], review_status=row[1])

    def review(self, station, state):
        record = self.get(station)
        if station in self.current or record['kind'] != 'candidate' or state not in STATES:
            raise ValueError('Estado o candidata inválidos.')
        with self.lock, self.db:
            self.db.execute('UPDATE records SET review=? WHERE id=?', (state, station))
            self.db.execute('INSERT INTO audit VALUES (?,?,?,?)', (datetime.now(timezone.utc).isoformat(), station, 'review', state))
        return self.get(station)

    def promote(self, station):
        record = self.get(station)
        if station in self.current or station in self.excluded:
            raise ValueError('Estación ya registrada o excluida en la base local; no se cambia su situación operativa.')
        with self.lock, self.db:
            self.db.execute("UPDATE records SET kind='candidate' WHERE id=?", (station,))
            self.db.execute('INSERT INTO audit VALUES (?,?,?,?)', (datetime.now(timezone.utc).isoformat(), station, 'promote', 'candidate'))
        return self.get(station)

    def clear_preliminary(self):
        with self.lock, self.db:
            count = self.db.execute("DELETE FROM records WHERE kind='preliminary'").rowcount
            self.db.execute('INSERT INTO audit VALUES (?,?,?,?)',
                (datetime.now(timezone.utc).isoformat(), '', 'clear_preliminary', str(count)))
        return {'removed': count}

    def clear_queries(self):
        with self.lock, self.db:
            count = self.db.execute('DELETE FROM queries').rowcount
            self.db.execute('INSERT INTO audit VALUES (?,?,?,?)',
                (datetime.now(timezone.utc).isoformat(), '', 'clear_queries', str(count)))
        return {'removed': count}

    def near(self, lat, lon):
        if not valid_number(lat) or not valid_number(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Coordenadas inválidas.')
        key = f'near:{lat:.4f}:{lon:.4f}:{datetime.now(timezone.utc).date()}'
        data = self.cache_get(key)
        if data is None:
            data = self.fetch('v3/location/near', {'geocode': f'{lat:.5f},{lon:.5f}', 'product': 'pws'})
            if data and not isinstance(data.get('location'), dict):
                raise ValueError('Respuesta de localizaciones no reconocida.')
            self.cache_put(key, data)
        location = data.get('location', {})
        ids = []
        ignored_current = set()
        for i, station in enumerate(location.get('stationId', [])[:10]):
            if not isinstance(station, str) or not re.fullmatch(r'[A-Z0-9_-]{1,50}', station):
                continue
            if station in self.current:
                ignored_current.add(station)
                continue
            row = {k: v[i] for k, v in location.items() if isinstance(v, list) and i < len(v)}
            if not valid_number(row.get('latitude')) or not valid_number(row.get('longitude')):
                continue
            row.update(status='excluida' if station in self.excluded else 'conocida' if station in self.known else 'nueva',
                       retrieved_utc=datetime.now(timezone.utc).isoformat(), rank=None)
            if self.stations:
                def distance(s):
                    a, b = math.radians(row['latitude']), math.radians(s['lat'])
                    h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(s['lon']-row['longitude'])/2)**2
                    return 12742 * math.asin(math.sqrt(min(1, h)))
                nearest = min(self.stations, key=distance)
                row.update(nearest_existing_km=round(distance(nearest), 3), nearest_existing_name=nearest['name'],
                           nearest_existing_source=nearest['source'], nearest_existing_id=nearest['id'])
            with self.lock, self.db:
                self.db.execute('INSERT OR IGNORE INTO records VALUES (?,?,?,?)', (station, 'preliminary', 'pending', json.dumps(row)))
            if station not in ids:
                ids.append(station)
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO queries VALUES (?,?,?)', (key, lat, lon))
        return {'records': [self.get(s) for s in ids], 'query': {'lat': lat, 'lon': lon},
                'limit': 10, 'ignored_current': len(ignored_current)}

    def availability(self, station):
        with self.history_lock:
            return self._availability(station)

    def _availability(self, station):
        self.get(station)
        end = datetime.now(ZoneInfo('Europe/Madrid')).date() - timedelta(days=1)
        start = end - timedelta(days=29)
        key = f'history:{station}:{end}'
        result = self.cache_get(key)
        if result is None:
            payload = self.fetch('v2/pws/history/daily', {'stationId': station, 'units': 'm',
                'startDate': start.strftime('%Y%m%d'), 'endDate': end.strftime('%Y%m%d'), 'numericPrecision': 'decimal'})
            if payload and not isinstance(payload.get('observations'), list):
                raise ValueError('Respuesta histórica no reconocida; no equivale a cero días.')
            result = summarize(payload.get('observations', []), start, end)
            self.cache_put('raw:' + key, payload)
            self.cache_put(key, result)
        current_key = f'current:{station}:{datetime.now(timezone.utc):%Y-%m-%dT%H}'
        current = self.cache_get(current_key)
        try:
            if current is None:
                current = self.fetch('v2/pws/observations/current', {'stationId': station, 'units': 'm', 'numericPrecision': 'decimal'})
                if current and not isinstance(current.get('observations'), list):
                    raise ValueError('Respuesta actual no reconocida.')
                self.cache_put(current_key, current)
            observations = current.get('observations', [])
            if observations:
                latest = max(observations, key=lambda r: str(r.get('obsTimeLocal') or ''))
                result['current_reading'] = latest.get('obsTimeLocal')
                elev = (latest.get('metric') or {}).get('elev')
                if valid_number(elev):
                    result['altitude_m'] = elev
        except ValueError as exc:
            result['current_error'] = str(exc)  # Historical availability remains independently valid.
        return result

    def state(self):
        return {'stations': [dict(s, availability=self.station_days.get(s['source'] + ':' + s['id'])) for s in self.stations],
                'records': self.records(), 'gaps': [g for g in self.load('grid.json') if g['nearest_km'] > 8],
                'searches': self.query_points()}

    def query_points(self):
        with self.lock:
            return [{'lat': lat, 'lon': lon} for lat, lon in self.db.execute('SELECT lat,lon FROM queries')]


def handler(research):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Requests never log upstream URLs or API credentials.

        def send_json(self, data, status=200):
            raw = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def trusted(self):
            host = self.headers.get('Host', '')
            expected = f'127.0.0.1:{self.server.server_port}'
            return host == expected and self.headers.get('Origin', 'http://' + expected) == 'http://' + expected

        def do_GET(self):
            if not self.trusted():
                return self.send_json({'error': 'Origen no permitido'}, 403)
            path = urlsplit(self.path).path
            if path in ('/api/state', '/api/export'):
                return self.send_json(research.state() if path.endswith('state') else {'records': research.records(include_current=True)})
            fixed = {'/': ASSETS / 'index.html', '/app.js': ASSETS / 'app.js', '/style.css': ASSETS / 'style.css',
                     '/base-styles.js': research.root / 'viewer/base-styles.js',
                     '/maplibre-gl.js': VENDOR / 'maplibre-gl.js',
                     '/maplibre-gl.css': VENDOR / 'maplibre-gl.css'}
            file = fixed.get(path)
            if file is None:
                return self.send_json({'error': 'No encontrado'}, 404)
            raw = file.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html'}[file.suffix] + '; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if not self.trusted() or self.headers.get('Content-Type') != 'application/json':
                return self.send_json({'error': 'Origen o formato no permitido'}, 403)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096:
                    raise ValueError('Petición demasiado grande o vacía.')
                data = json.loads(self.rfile.read(size))
                path = urlsplit(self.path).path
                if path == '/api/near':
                    result = research.near(data.get('lat'), data.get('lon'))
                elif path == '/api/places':
                    result = research.search_places(data.get('query'), data.get('lat'), data.get('lon'))
                elif path == '/api/availability':
                    result = research.availability(data.get('id'))
                elif path == '/api/review':
                    result = research.review(data.get('id'), data.get('state'))
                elif path == '/api/promote':
                    result = research.promote(data.get('id'))
                elif path == '/api/clear-preliminary':
                    result = research.clear_preliminary()
                elif path == '/api/clear-queries':
                    result = research.clear_queries()
                else:
                    return self.send_json({'error': 'No encontrado'}, 404)
                self.send_json(result)
            except (ValueError, TypeError, AttributeError) as exc:
                self.send_json({'error': str(exc)}, 400)
            except Exception:
                self.send_json({'error': 'Error local al procesar o guardar. No se ha confirmado la operación.'}, 500)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--port', type=int, default=8123)
    args = parser.parse_args()
    source = (ROOT / 'rainmapper_core/viewers/maplibre-viewer/app.js').read_text()
    styles = source.split('const baseStyles = ', 1)[1].split('\nlet currentStyle', 1)[0].strip()
    terrain = source.split('const TERRAIN_TILES = ', 1)[1].split(';', 1)[0]
    (args.data / 'viewer/base-styles.js').write_text('const COVERAGE_BASE_STYLES = ' + styles +
        '\nconst COVERAGE_TERRAIN_TILES = ' + terrain + ';\n')
    research = Research(args.data)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(research))
    print(f'Investigación de estaciones: http://127.0.0.1:{args.port}/', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
