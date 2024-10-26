import requests
import time
import re
from bs4 import BeautifulSoup

class parseStationData:
    def __init__(self, url):
        self.url = url
        self.soup = None
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
    
    def fetch_data(self):
        max_retries = 10
        for attempt in range(max_retries):
            try:
                #response = requests.get(self.url, headers=self.headers)
                response = requests.get(self.url, headers=self.headers)

                if response.status_code == 200:
                    self.soup = BeautifulSoup(response.content, 'html.parser')
                    return response
                else:
                    print(f'Error al conectar: {response.status_code}. Intento {attempt + 1} de {max_retries}')
            except requests.RequestException as e:
                print(f'Excepción al intentar conectar: {e}. Intento {attempt + 1} de {max_retries}')
            # Esperar un poco antes de intentar de nuevo (opcional)
            time.sleep(1)
        
        raise Exception(f'Error al conectar después de {max_retries} intentos. Status code={response.status_code}')
    
            
    def get_station_header(self):
            # Extraer la elevation, latitude y longitude
        try:
            station_header = self.soup.find('div', class_='columns small-12 station-header')
            #print(datos)
            span = station_header.find('span')

            # Extraer el texto del <span>
            span_text = span.get_text()

            # Usar expresiones regulares para extraer los valores
            # Buscar todos los números en el texto
            numbers = re.findall(r'\d+\.\d+|\d+', span_text)

            # Buscar los signos de latitud y longitud
            latitude_sign = re.search(r'°(N|S)', span_text)
            longitude_sign = re.search(r'°(E|W|O)', span_text)

            # Extraer la elevación
            elevation_ft = numbers[0]
            elevation = (float(elevation_ft) * 0.3048)                        # Pasar pies a metros
            elevation = f"{elevation:.0f}"

            # Extraer la latitud
            latitude = float(numbers[1])
            if latitude_sign and latitude_sign.group(1) == 'S':
                latitude = -latitude

            # Extraer la longitud
            longitude = float(numbers[2])
            if longitude_sign and (longitude_sign.group(1) in ['W','O']):
                longitude = -longitude

        except (AttributeError, IndexError):
            raise Exception("No se pudieron encontrar Elevacion,Latitud,Longitud en la página")
        
        # Extraer la poblacion, el codigo de estacion y el nombre de la estacion

        try:
            h1_tag = self.soup.find('h1')

            # Extraer el nombre de la estación y el código de la estación del <h1>
            station_text = h1_tag.get_text(strip=True)
            # Usar rsplit para dividir desde la derecha
            station_name, station_ID = station_text.rsplit(' - ', 1)

            # Encontrar el <a> que contiene la información de la población
            a_tag = self.soup.find('a', class_='location-name')

            # Extraer la población del atributo href del <a>
            location_text = a_tag.get_text(strip=True)
            # Dividir el texto por las comas
            parts = location_text.split(',')
            # Obtener la parte que contiene "Forecast for"
            forecast_part = parts[0]
            # Dividir esta parte por el espacio y obtener el último elemento
            location_name = forecast_part.split('for ')[-1]
            
        except (AttributeError, IndexError):
            raise Exception("No se pudieron encontrar Datos Identificativos Estación en la página")

        return station_ID, station_name, location_name, elevation, latitude, longitude

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
