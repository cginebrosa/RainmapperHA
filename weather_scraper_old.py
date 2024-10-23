# Made with love by Karl
# Contact me on Telegram: @karlpy
from datetime import datetime
import requests
import csv
import lxml.html as lh

import config

from util.UnitConverter import ConvertToSystem
from util.Parser import Parser
from util.Utils import Utils
#inicio modi
from util.parseStationData import parseStationData
import pandas as pd
from const import _PYTHON_REQUIRES, _GMAPS_KEY, _DATA_PATH, _MAPS_PATH

#fin modi

# configuration
stations_file = open('stations.txt', 'r')
URLS = stations_file.readlines()
# Date format: YYYY-MM-DD
START_DATE = config.START_DATE
END_DATE = config.END_DATE
MONTHLY = config.MONTHLY
MERGE_DATA = config.MERGE_DATA

# set to "metric" or "imperial"
UNIT_SYSTEM = config.UNIT_SYSTEM
# find the first data entry automatically
FIND_FIRST_DATE = config.FIND_FIRST_DATE

def scrap_wunderground_station(weather_station_url, launchtime):

    session = requests.Session()
    timeout = 5
    global START_DATE
    global END_DATE
    global UNIT_SYSTEM
    global FIND_FIRST_DATE
    global wunderground_header

    global file_name

    if FIND_FIRST_DATE:
        # find first date
        first_date_with_data = Utils.find_first_data_entry(weather_station_url=weather_station_url, start_date=START_DATE)
        # if first date found
        if(first_date_with_data != -1):
            START_DATE = first_date_with_data
    
    url_gen = Utils.date_url_generator(weather_station_url, START_DATE, END_DATE)
    station_name = weather_station_url.split('/')[-1]
    file_prefix = station_name
    
    if MERGE_DATA:
        file_prefix = 'MERGED'
    
    file_name = f'{file_prefix}_{START_DATE}_to_{END_DATE}_at_{launchtime}.csv'

    with open(file_name, 'a+', newline='') as csvfile:
        if MONTHLY:
            fieldnames = ['StationID','Date','Time','StationName','Comarca','Municipi',
                          'Provincia','Elevation','Latitude','Longitude',
                          'High','Avg','Low','High_1','Avg_1','Low_1','High_2','Avg_2','Low_2','High_3','Avg_3','Low_3',
                          'High_4','Low_4','Sum']
        else:
            fieldnames = ['StationID','Date', 'Time','StationName','Comarca','Municipi',
                          'Provincia','Elevation','Latitude','Longitude',
                          'Temperature','Dew_Point','Humidity',	'Wind','Speed','Gust','Pressure','Precip_Rate',	
                          'Precip_Accum','UV','Solar']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if wunderground_header:
            # Write the correct headers to the CSV file
            if UNIT_SYSTEM == "metric":
                if MONTHLY:
                    writer.writerow({'StationID':'Codi Estació','Date': 'Data', 
                                    'Time': 'Hora','StationName':'Estació','Comarca':'Comarca','Municipi':'Municipi',
                                    'Provincia':'Provincia','Elevation':'Altitud','Latitude':'Latitud','Longitude':'Longitud',
                                    'High': 'TempHigh_C','Avg': 'TempAvg_C','Low': 'TempLow_C',
                                    'High_1': 'DPHigh_C','Avg_1': 'DPAvg_C', 'Low_1': 'DPLow_C','High_2': 'HumHigh_%',
                                    'Avg_2': 'HumAvg_%','Low_2': 'HumLow_%','High_3': 'SpeedHigh_kmh','Avg_3': 'SpeedAv_kmh',
                                    'Low_3': 'SpeedLow_kmh','High_4': 'PressHigh_hPa','Low_4': 'PressLow_hPa','Sum': 'Rain_mm'})
                else:
                    # 12:04 AM	24.4 C	18.3 C	69 %	SW	0.0 km/h	0.0 km/h	1,013.88 hPa	0.00 mm	0.00 mm	0	0 w/m²
                    writer.writerow({'StationID':'Codi Estació','Date': 'Data', 'Time': 'Hora',
                                    'StationName':'Estació','Comarca':'Comarca','Municipi':'Municipi',
                                    'Provincia':'Provincia','Elevation':'Altitud','Latitude':'Latitud','Longitude':'Longitud',
                                    'Temperature': 'Temperature_C','Dew_Point': 'Dew_Point_C',
                                    'Humidity': 'Humidity_%','Wind': 'Wind','Speed': 'Speed_kmh','Gust': 'Gust_kmh',
                                    'Pressure': 'Pressure_hPa','Precip_Rate': 'Precip_Rate_mm','Precip_Accum': 'Precip_Accum_mm',
                                    'UV': 'UV','Solar': 'Solar_w/m2'})
            elif UNIT_SYSTEM == "imperial":
                # 12:04 AM	75.9 F	65.0 F	69 %	SW	0.0 mph	0.0 mph	29.94 in	0.00 in	0.00 in	0	0 w/m²
                writer.writerow({'StationID':'Codi Estació','Date': 'Data', 'Time': 'Hora',
                                'StationName':'Estació','Comarca':'Comarca','Municipi':'Municipi',
                                'Provincia':'Provincia','Elevation':'Altitud_f','Latitude':'Latitud','Longitude':'Longitud',
                                'Temperature': 'Temperature_F','Dew_Point': 'Dew_Point_F',
                                'Humidity': 'Humidity_%','Wind': 'Wind','Speed': 'Speed_mph','Gust': 'Gust_mph',
                                'Pressure': 'Pressure_in','Precip_Rate': 'Precip_Rate_in','Precip_Accum': 'Precip_Accum_in',
                                'UV': 'UV','Solar': 'Solar_w/m2'})
            else:
                raise Exception("please set 'unit_system' to either \"metric\" or \"imperial\"! ")
            wunderground_header = False

        #print(f'url_gen: {list(url_gen)}')
        for date_string, url in url_gen:
            try:
                # Inicio modi
                print('')
                print('==================================================================================================')
                print(f'Retrieving Station Data for {weather_station_url}')                

                scraper = parseStationData(weather_station_url)

                try:
                    scraper.fetch_data()
                    # Obtener y mostrar los datos de la estación
                    #elevation, latitude, longitude, station_name, station_ID, location_name = scraper.get_station_header()
                    station_ID, station_name, location_name, elevation, latitude, longitude = scraper.get_station_header()
                    print(f'Código de la estación: {station_ID}')
                    print(f'Nombre de la estación: {station_name}')
                    print(f'Municipi: {location_name}')
                    print(f"Latitud: {latitude}")
                    print(f"Longitud: {longitude}")
                    print(f"Altitud: {elevation} m")

                    
                except Exception as e:
                    print(e)
# Fin modi
                print(f'Scraping data from {url}')
                history_table = False
                while not history_table:
                    html_string = session.get(url, timeout=timeout)
                    doc = lh.fromstring(html_string.content)
                    history_table = doc.xpath('//*[@id="main-page-content"]/div/div/div/lib-history/div[2]/lib-history-table/div/div/div/table/tbody')
                    if not history_table:
                        print("refreshing session")
                        session = requests.Session()

                # parse html table rows
                #print(f'Parsing html table rows from {url}')

                data_rows = Parser.parse_html_table(date_string, 
                                                    history_table, 
                                                    station_ID, 
                                                    station_name,
                                                    location_name,
                                                    elevation,
                                                    latitude, 
                                                    longitude)

                # convert to metric system
                converter = ConvertToSystem(UNIT_SYSTEM)
                data_to_write = converter.clean_and_convert(data_rows)
                    
                print(f'Saving {len(data_to_write)} rows')
                writer.writerows(data_to_write)
            except Exception as e:
                print(e)

def create_wunderground():
    launchtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    for url in URLS:
        url = url.strip()
        #print(url)
        scrap_wunderground_station(url, launchtime)

    # Convert to Rainmapper format

    # Newly created csv file = file_name
    scraper_df = pd.read_csv(file_name , decimal=',')
    #print(scraper_df)
    # Crear dataframe con las columnas del formato Rainmapper
    new_columns = [
        'Codi Estació',
        'Data Lectura',
        'Estació',
        'Comarca',
        'Municipi',
        'Provincia',
        'Altitud',
        'Latitud',    
        'Longitud',
        'Ultima Lectura',
        'Variable',
        'Total',
        'Unitat',
        'max_temp_celsius',
        'min_temp_celsius',
        'max_humidity_percent',
        'min_humidity_percent',
        'Data Local',
        'Hora Local'
                    ]
    wunderground_df = pd.DataFrame(columns=new_columns)
    # Llenar nuevo dataframe con valores de scrapped
    wunderground_df['Codi Estació'] = scraper_df['Codi Estació']
    wunderground_df['Data Lectura'] = scraper_df['Data'] + ' '+ scraper_df['Hora']
    wunderground_df['Estació'] = scraper_df['Estació']
    wunderground_df['Comarca'] = scraper_df['Comarca']
    wunderground_df['Municipi'] = scraper_df['Municipi']
    wunderground_df['Codi Estació'] = scraper_df['Codi Estació']
    wunderground_df['Altitud'] = scraper_df['Altitud']
    wunderground_df['Latitud'] = scraper_df['Latitud']
    wunderground_df['Longitud'] = scraper_df['Longitud']
    wunderground_df['Ultima Lectura'] = scraper_df['Data']
    wunderground_df['Variable'] = 'Precipitació'
    wunderground_df['Total'] = scraper_df['Rain_mm']
    wunderground_df['Unitat'] = 'mm'
    wunderground_df['max_temp_celsius'] = scraper_df['TempHigh_C']
    wunderground_df['min_temp_celsius'] = scraper_df['TempLow_C']
    wunderground_df['max_humidity_percent'] = scraper_df['HumHigh_%']
    wunderground_df['min_humidity_percent'] = scraper_df['HumLow_%']
    wunderground_df['Data Local'] = scraper_df['Data']
    wunderground_df['Hora Local'] = scraper_df['Hora']


    #print(wunderground_df)

    # Save wunderground_df to csv
    wunderground_df.to_csv(_DATA_PATH+'Wunderground'+'.csv', decimal='.', index=False)
    return wunderground_df
    '''         new_row = {
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
                            'Data Local': 'To be set later',
                            'Hora Local': 'To be set later'
                            }
    '''

global wunderground_header
wunderground_header = True
wunderground_df = create_wunderground()
print(wunderground_df)