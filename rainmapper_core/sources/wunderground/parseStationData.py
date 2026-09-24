import requests
import time
import re
from datetime import date
from urllib.parse import urlparse
from rainmapper_core.sources.wunderground.daily_api import cache_encodings
from bs4 import BeautifulSoup
from rainmapper_core.config.const import _max_attempts, _wunderground_full_log


class WundergroundPageError(ValueError):
    """The response cannot safely provide the requested station data."""


def validate_history_dates(rows, start_date, end_date):
    selected = []
    for row in rows:
        try:
            observed = date.fromisoformat(str(row['Date']))
        except (KeyError, ValueError, TypeError) as exc:
            raise WundergroundPageError('Wunderground: fecha de observación inválida') from exc
        if start_date <= observed <= end_date:
            selected.append(row)
    if not selected:
        raise WundergroundPageError(
            f'Wunderground: la respuesta no contiene observaciones del intervalo '
            f'{start_date}..{end_date}; no se guardan datos fuera del rango solicitado'
        )
    return selected


class parseStationData:
    def __init__(self, url, max_attempts=_max_attempts, full_log=_wunderground_full_log):
        self.url = url
        self.max_attempts = max(1, max_attempts)
        self.full_log = full_log
        self.soup = None
        self.response = None
        self.validated_data = None
        self.headers =  {
            'Referer': ''  # Referer vacío para simular "noreferrer"
                        }

    def fetch_data_original(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            self.soup = BeautifulSoup(response.content, 'html.parser')
        else:
            raise Exception(f'Error al conectar: {response.status_code}')
        return response
    
    def fetch_data(self, *, require_metadata=False, validator=None):
        """Retry incomplete HTTP 200 responses using bounded encoding variants."""
        def validate(response):
            if require_metadata:
                self.get_station_header()
            self.validated_data = validator(response) if validator else None

        if self.response is not None:
            try:
                validate(self.response)
                return self.response
            except WundergroundPageError:
                pass
        encodings = cache_encodings()
        last_error = 'sin respuesta'
        for attempt in range(self.max_attempts):
            self.soup = self.response = self.validated_data = None
            try:
                response = requests.get(
                    self.url,
                    headers={**self.headers, 'Accept-Encoding': encodings[attempt % len(encodings)]},
                    timeout=(5, 10),
                )
                if response.status_code != 200:
                    raise WundergroundPageError(f'HTTP {response.status_code}')
                self.soup = BeautifulSoup(response.content, 'html.parser')
                validate(response)
                self.response = response
                return response
            except (requests.RequestException, WundergroundPageError) as exc:
                last_error = str(exc)
                if self.full_log:
                    print(f'Wunderground: intento {attempt + 1}/{self.max_attempts}: {last_error}')
            if attempt + 1 < self.max_attempts:
                time.sleep(1)
        self.soup = self.response = self.validated_data = None
        raise WundergroundPageError(
            f'Wunderground: no se pudo obtener una respuesta válida tras '
            f'{self.max_attempts} intentos: {last_error}'
        )

    def get_station_header(self):
        if self.soup is None:
            raise WundergroundPageError('Wunderground: página no cargada')
        header = self.soup.select_one('dashboard-header-view, .station-header')
        if header is None:
            raise WundergroundPageError('Wunderground: falta la cabecera de la estación en el HTML recibido')
        coordinates = header.select_one('.elevation-coordinates') or header
        text = coordinates.get_text(' ', strip=True)
        number = r'([+-]?\d+(?:\.\d+)?)'
        altitude = re.search(r'\bElev(?:ation)?\s*:?\s*' + number + r'\s*(ft|m)\b', text, re.I)
        lat = re.search(number + r'\s*°\s*([NS])\b', text, re.I)
        lon = re.search(number + r'\s*°\s*([EWO])\b', text, re.I)
        if not all((altitude, lat, lon)):
            raise WundergroundPageError('Wunderground: coordenadas o altitud con unidades no reconocidas en el HTML recibido')
        elevation = float(altitude[1]) * (0.3048 if altitude[2].lower() == 'ft' else 1)
        latitude = abs(float(lat[1])) * (-1 if lat[2].upper() == 'S' else 1)
        longitude = abs(float(lon[1])) * (-1 if lon[2].upper() in {'W', 'O'} else 1)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise WundergroundPageError('Wunderground: coordenadas fuera de rango')
        try:
            station_name, station_id = header.find('h1').get_text(' ', strip=True).rsplit(' - ', 1)
        except (AttributeError, ValueError) as exc:
            raise WundergroundPageError('Wunderground: identificación de estación no reconocida') from exc
        station_id = station_id.strip().upper()
        expected = re.search(r'/pws/([^/]+)', urlparse(self.url).path, re.I)
        if expected and station_id != expected[1].upper():
            raise WundergroundPageError('Wunderground: la respuesta corresponde a otra estación')
        location = self.soup.select_one('a.location-name, dashboard-header-view .location-info a')
        if location is None:
            raise WundergroundPageError('Wunderground: localidad de estación no reconocida')
        location_name = location.get_text(' ', strip=True).split(',')[0].split('for ')[-1].strip()
        if not station_name.strip() or not station_id or not location_name:
            raise WundergroundPageError('Wunderground: identificación de estación incompleta')
        return station_id, station_name.strip(), location_name, f'{elevation:.0f}', latitude, longitude

    def get_elevation(self):
        if self.soup:
            elevation = self.soup.find('span', text='Elev').find_next('span').text.strip()
            return elevation
        else:
            raise Exception('Datos no cargados. Llama a fetch_data primero.')

    def get_latitude(self):
        if self.soup:
            latitude = self.soup.find('span', text='Latitud').find_next('span').text.strip()
            return latitude
        else:
            raise Exception('Datos no cargados. Llama a fetch_data primero.')

    def get_longitude(self):
        if self.soup:
            longitude = self.soup.find('span', text='Longitud').find_next('span').text.strip()
            return longitude
        else:
            raise Exception('Datos no cargados. Llama a fetch_data primero.')
