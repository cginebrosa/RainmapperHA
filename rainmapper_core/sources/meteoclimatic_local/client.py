from urllib.request import Request, urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup

from rainmapper_core.sources.meteoclimatic_local.exceptions import MeteoclimaticError, StationNotFound
from rainmapper_core.sources.meteoclimatic_local.observation import Observation
from rainmapper_core.sources.meteoclimatic_local import __version__


import pandas as pd

class MeteoclimaticClient(object): 
    """
    Entry point class providing clients for the Meteoclimatic service.
    """

    _base_url = "https://www.meteoclimatic.net/feed/rss/{station_code}"

    def weather_at_station(self, station_code):
        url = self._base_url.format(station_code=station_code)

        req = Request(url, headers={"User-Agent": f"pymeteoclimatic/{__version__}"})

        try:
            parse_xml_url = urlopen(req)
        except HTTPError as exc:
            raise MeteoclimaticError(
                "Error fetching station data [status_code=%d]" % (exc.getcode(),)
                ) from exc

        xml_page = parse_xml_url.read()
        parse_xml_url.close()

        soup_page = BeautifulSoup(xml_page, "xml")
        items = soup_page.findAll("item")

        if len(items) == 0:
            raise StationNotFound(station_code)
        
        observation = Observation.from_feed_item(items[0])
                
        return observation

    def weather_sel_stations(self, station_code):               ## Added to select stations according to Meteoclimatic specifications
        url = self._base_url.format(station_code=station_code)

        req = Request(url, headers={"User-Agent": f"pymeteoclimatic/{__version__}"})

        try:
            parse_xml_url = urlopen(req)
        except HTTPError as exc:
            raise MeteoclimaticError(
                "Error fetching station data [status_code=%d]" % (exc.getcode(),)
                ) from exc

        xml_page = parse_xml_url.read()
        parse_xml_url.close()

        soup_page = BeautifulSoup(xml_page, "xml")
        items = soup_page.findAll("item")

        if len(items) == 0:
            raise StationNotFound(station_code)
        
        data_list = []
        for i in range(len(items)):
            observation = Observation.from_feed_item(items[i])
            new_row = {
                        'Codi Estació': observation.station.code,
                        'Data Lectura': observation.weather.reference_time,
                        'Estació': observation.station.name,
                        'Comarca': 'Not set yet',
                        'Municipi': 'To be set later',
                        'Provincia': 'To be set later',
                        'Altitud': 'To be set later',
                        'Latitud': observation.station.geolat,    
                        'Longitud': observation.station.geolon,
                        'Ultima Lectura': observation.weather.reference_time,
                        'Variable': 'Precipitació',
                        'Total': observation.weather.rain,
                        'Unitat': 'mm',
                        'max_temp_celsius': observation.weather.temp_max,
                        'min_temp_celsius': observation.weather.temp_min,
                        'max_humidity_percent': observation.weather.humidity_max,
                        'min_humidity_percent': observation.weather.humidity_min,
                        'wind_avg_kmh': observation.weather.wind_current,
                        'wind_min_kmh': pd.NA,
                        'wind_max_kmh': observation.weather.wind_max,
                        'wind_gust_kmh': observation.weather.wind_max,
                        'wind_direction_deg': observation.weather.wind_bearing,
                        'wind_gust_direction_deg': pd.NA,
                        'wind_observation_count': 1,
                        'wind_source_height_m': pd.NA,
                        'Data Local': 'To be set later',
                        'Hora Local': 'To be set later'
                        }
            data_list.append(new_row)
        stations_df = pd.DataFrame(data_list).query('Total.notna()').sort_values(by=['Total'], ascending=False).reset_index(drop=True)
        return stations_df
