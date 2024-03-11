#!/usr/bin/env python

# make sure to install these packages before running:
# pip install pandas
# pip install sodapy
# pip install pymeteoclimatic

import pandas as pd
from sodapy_local import Socrata
from datetime import datetime, date, timedelta, time
import pytz
import os
import math
import re
import googlemaps
from meteoclimatic_local.client import MeteoclimaticClient
from const import _PYTHON_REQUIRES, _GMAPS_KEY, _DATA_PATH, _MAPS_PATH

# Import parameters from const
from const import   _codi_estacio,\
                    _qcodi_variable,\
                    _qcodi_variable2,\
                    _create_meteoclimatic,\
                    _create_meteocat,\
                    _create_meteocat_conditions,\
                    _incremental_meteocat,\
                    _incremental_meteoclimatic,\
                    _minima_lectura_meteoclimatic,\
                    _minima_lectura_meteocat,\
                    _minimum_rain_toprint,\
                    _minimum_rain_tomap,\
                    _create_googlemaps_files,\
                    _days_init,\
                    _days_end,\
                    _days_bucket,\
                    _print_dataframes,\
                    _print_totals,\
                    _last_number_rains,\
                    _create_daily_stats,\
                    _create_monthly_stats,\
                    _create_weekly_stats

# Add argument parser
import argparse
# Configurar el parser de argumentos
parser = argparse.ArgumentParser(description='Descripción de tu script')
parser.add_argument('--create_meteoclimatic', 
                    dest='_create_meteoclimatic', 
                    nargs='?', 
                    const=True, 
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_create_meteoclimatic,
                    help='Recuperar datos de Meteoclimatic (TRUE/FALSE, 1/0, YES/NO) -> Const=True, Default=True')
parser.add_argument('--create_meteocat', 
                    dest='_create_meteocat', 
                    nargs='?', 
                    const=True, 
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_create_meteocat, 
                    help='Recuperar datos de Meteocat (TRUE/FALSE, 1/0, YES/NO) -> Const=True, Default=True')
parser.add_argument('--days_init', 
                    dest='_days_init', 
                    nargs='?', 
                    const=_days_init,
                    type=int,
                    default= _days_init, 
                    help='Dias hacia atras para buscar lluvia acumulada (negativo, 0 o positivo(?)) -> Const=Default=-7')
parser.add_argument('--days_end', 
                    dest='_days_end',
                    nargs='?', 
                    const=_days_end,
                    type=int, 
                    default=_days_end,
                    help='Dias hacia adelante para buscar lluvia acumulada (negativo, 0 o positivo(?)) -> Const=Default=0')
parser.add_argument('--nomaps', 
                    dest='_create_googlemaps_files', 
                    nargs='?', 
                    const=False, 
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_create_googlemaps_files,
                    help='No crear Googlemaps files (TRUE/FALSE, 1/0, YES/NO) -> Const=False, Default=True')
parser.add_argument('--nototals', 
                    dest='_print_totals', 
                    nargs='?', 
                    const=False, 
                    type=lambda x: not((str(x).lower() in ['true','1','yes'])),
                    default=_print_totals,
                    help='No imprimir Totales (TRUE/FALSE, 1/0, YES/NO) -> Const=False, Default=True')
parser.add_argument('--days_bucket', 
                    dest='_days_bucket',
                    nargs='?', 
                    const=_days_bucket,
                    type=int, 
                    default=_days_bucket,
                    help='Dias bucket en lectura de Meteocat (Numerico positivo) -> Const=Default=10')

# Parsear los argumentos de la línea de comandos
args = parser.parse_args()

_create_meteoclimatic = args._create_meteoclimatic
_create_meteocat = args._create_meteocat
_days_init = args._days_init
_days_end = args._days_end
_days_bucket = args._days_bucket
_create_googlemaps_files = args._create_googlemaps_files
_print_totals = args._print_totals

#print(_create_meteocat)
#print(_days_init)
#print(_days_end)

# Configure pandas to show all rows/columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

_script_path = os.path.dirname(os.path.abspath(__file__))
_requirements_file = os.path.join(_script_path, 'requirements.txt')
 
print ('=============')
print ('REQUIREMENTS:')
print ('=============')
print ('Python:'+_PYTHON_REQUIRES)
with open(_requirements_file, 'r') as requirements:
    requirements = requirements.read()
    print()
    print('Install packages:')
    print('-----------------')
    print(requirements)
print()

#In[0] ## GENERIC FUNCTION DEFINITIONS

# Global variable to store start time
start_time = None

def start_count(_legend=''):
    global start_time
    start_time = datetime.now()
    print('')
    print(_legend)

def end_count(_legend=''):
    if start_time is None:
        print("Error: start_count() not initialized.")
        return
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    print(_legend+"--> Time elapsed: {}".format(elapsed_time))

def local_to_utc(_datetime_local):
    # Obtiene la zona horaria local
    local_tz = pytz.timezone('Europe/Madrid')

    # Añade la información del timezone a la hora local
    _datetime_local = local_tz.localize(_datetime_local, is_dst=None)

    # Convierte la hora local a UTC
    _datetime_utc = _datetime_local.astimezone(pytz.utc)

    # Elimina la información de timezone antes de devolver el resultado
    _datetime_utc = _datetime_utc.replace(tzinfo=None)

    # Devuelve la hora en UTC sin información de timezone
    return _datetime_utc

def utc_to_local(_datetime_utc):
    # Obtiene la zona horaria local
    local_tz = pytz.timezone('Europe/Madrid')

    # Añade la información del timezone a la hora UTC
    _datetime_utc = pytz.utc.localize(_datetime_utc)

    # Convierte la hora UTC a la hora local
    _datetime_local = _datetime_utc.astimezone(local_tz)

    # Elimina la información de timezone antes de devolver el resultado
    _datetime_local = _datetime_local.replace(tzinfo=None)

    # Devuelve la hora local sin información de timezone
    return _datetime_local

def get_query_date(base_date,date_timedelta):
    query_date= local_to_utc(base_date + timedelta(days=date_timedelta)).strftime("%Y-%m-%dT%H:%M:00")
    return query_date

def get_data_inici():
    # GET START DATE in d-m-Y H:M:S format for file naming
    _data_inici = datetime.strptime(_start_date, "%Y-%m-%dT%H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
    return _data_inici

def get_data_fi():
    # GET  DATE in d-m-Y H:M:S format for file naming
    _data_fi = datetime.strptime(_end_date, "%Y-%m-%dT%H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
    return _data_fi

def get_googlemaps(lat,long):
    try:
        lat = float(lat)
        long = float(long)
        if lat < long:                              # Exchange lat/long if they seems  to be flipped
            lat, long = long, lat
    except ValueError:                              #If lat or long are not float(able) return elevation=0 
        print ('Error')
        return (0,'Municipi Not found','Provincia Not Found')

    gmaps = googlemaps.Client(key=_GMAPS_KEY)
    elevation_result= gmaps.elevation((lat,long))
    if len(elevation_result) == 0:                  # If elevation not found set to 0
        elevation_result = [0]

    reverse_geocode_result = gmaps.reverse_geocode((lat,long),language='ES')

    locality = [component['long_name'] for item in reverse_geocode_result \
            for component in item.get('address_components', []) if 'locality' in component.get('types', [])]
    if len(locality) == 0:                          # If not found set to "Check lat/long"
        locality = ["Not found in googlemaps - Check lat/long"]

    administrative_area_level_2 = [component['long_name'] for item in reverse_geocode_result \
            for component in item.get('address_components', []) if 'administrative_area_level_2' in component.get('types', [])]
    if len(administrative_area_level_2) == 0:       # If not found set to "Check lat/long"
        administrative_area_level_2 = ["Not found - Check lat/long"]
    #print(reverse_geocode_result)
    #print(elevation_result)

    return elevation_result[-1]['elevation'],locality[0], administrative_area_level_2[0]

## END GENERIC FUNCTION DEFINITIONS
#In[5] ## DATA RETRIEVAL functions
def read_incremental(_dataframe, _nrows=None):
    if _nrows is None:
        df = pd.read_csv(_DATA_PATH + _dataframe + '.csv', decimal=',')
    else:
        df = pd.read_csv(_DATA_PATH + _dataframe + '.csv', decimal=',', nrows=_nrows)
    #df['Data Lectura'] = pd.to_datetime(df['Ultima Lectura'])       # Construye 'Data Lectura' como datetime64
    df['Data Lectura'] = pd.to_datetime(df['Data Lectura'],format='%Y-%m-%d %H:%M:%S') # 'Data Lectura' como datetime64
    df['Total'] = df['Total'].astype(float)     # Convierte la columna 'Total' a tipo float
    df['Altitud'] = df['Altitud'].astype(str)  # Convierte la columna 'Altitud' a tipo str
    df['Latitud'] = df['Latitud'].astype(str)  # Convierte la columna 'Latitud' a tipo str
    df['Longitud'] = df['Longitud'].astype(str)  # Convierte la columna 'Longitud' a tipo str
    df['Data Local'] = df['Data Local'].astype(str)  # Convierte la columna 'Data Local' a tipo str

    return df

def get_myquery(_codi_estacio,_qcodi_variable, _qcodi_variable2,_start_date, _end_date): # Create _myquery for sum records
    _qcodi_estacio="'"+_codi_estacio+"'"    # BUILD STRING FOR STATION CODE IN CASE SOMEONE IS SELECTED 
    _select_per_codi_variable = ' AND (codi_variable='+_qcodi_variable+' '+'OR codi_variable='+_qcodi_variable2+') ' 

    if _codi_estacio == ''  or _codi_estacio == 'ALL':            
        _select_per_codi_estacio = ''   
    else:                               
        _select_per_codi_estacio = ' AND (codi_estacio='+_qcodi_estacio+' '+'OR codi_estacio='+_qcodi_estacio+') '  

    _myquery = "SELECT codi_estacio, max(data_lectura) as ultima_lectura, codi_variable, sum(valor_lectura) as valor_variable, \
            avg(valor_lectura) as valor_avg, median(valor_lectura) as valor_median \
            WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
            AND valor_lectura > 0 \
            GROUP BY codi_estacio, codi_variable \
            ORDER BY valor_variable DESC, codi_estacio ASC LIMIT 1000"   # Limit to 1,000 stations
    return _myquery

def get_myquery_rain_all(_codi_estacio,_qcodi_variable, _qcodi_variable2,_start_date, _end_date): # Create _myquery for all records
    _qcodi_estacio="'"+_codi_estacio+"'"    # BUILD STRING FOR STATION CODE IN CASE SOMEONE IS SELECTED 
    _select_per_codi_variable = ' AND (codi_variable='+_qcodi_variable+' '+'OR codi_variable='+_qcodi_variable2+') ' 

    if _codi_estacio == ''  or _codi_estacio == 'ALL':            
        _select_per_codi_estacio = ''   
    else:                               
        _select_per_codi_estacio = ' AND (codi_estacio='+_qcodi_estacio+' '+'OR codi_estacio='+_qcodi_estacio+') '  

    #_myquery = "SELECT codi_estacio, data_lectura as ultima_lectura, codi_variable, valor_lectura as valor_variable \
    #        WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
    #        AND valor_lectura > 0 \
    #        GROUP BY codi_estacio, codi_variable, data_lectura,valor_lectura \
    #        ORDER BY ultima_lectura,valor_variable DESC, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records
    
    _myquery = "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, codi_variable, sum(valor_lectura) as valor_variable \
            WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
            AND valor_lectura >= 0 \
            GROUP BY codi_estacio, codi_variable, ultima_lectura \
            ORDER BY ultima_lectura,valor_variable DESC, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records    
    
    #print('myquery_rain_all:',_myquery)
    return _myquery

def get_myquery_conditions_all(_codi_estacio,_start_date, _end_date): # Create _myquery for all records
    _qcodi_estacio="'"+_codi_estacio+"'"    # BUILD STRING FOR STATION CODE IN CASE SOMEONE IS SELECTED 
    _select_per_codi_variable = " AND (codi_variable in ('40','42','3','44')) " # temp_max(40),temp_min(42),hum_max(3),hum_min(44)

    if _codi_estacio == ''  or _codi_estacio == 'ALL':            
        _select_per_codi_estacio = ''   
    else:                               
        _select_per_codi_estacio = ' AND (codi_estacio='+_qcodi_estacio+' '+'OR codi_estacio='+_qcodi_estacio+') '  

    #_myquery = "SELECT codi_estacio, data_lectura as ultima_lectura, codi_variable, valor_lectura as valor_variable \
    #        WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
    #        GROUP BY codi_estacio, codi_variable, data_lectura,valor_lectura \
    #        ORDER BY ultima_lectura,valor_variable DESC, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records
    _myquery = "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, codi_variable, \
                max(valor_lectura) as max_valor_variable, min(valor_lectura) as min_valor_variable \
            WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " \
                    + _select_per_codi_estacio +_select_per_codi_variable+" \
            GROUP BY codi_estacio, codi_variable, ultima_lectura \
            ORDER BY ultima_lectura, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records    

    #print('myquery_conditions_all:',_myquery)
    return _myquery

def get_estacions_xema(): # Get estacions data from Meteocat
    estacions = client.get(socrata_metadades_estacions_xema, \
                       query="SELECT codi_estacio, nom_estacio, nom_comarca, nom_provincia, \
                       nom_municipi, altitud, latitud, longitud ORDER BY codi_estacio", exclude_system_fields='true')
    
    # Drop duplicates from 20240306
    estacions_xema = pd.DataFrame.from_records(estacions).drop_duplicates()

    #save_dataframe(estacions_xema, 'estacions_xema_downloaded', _save_to_csv=True, _save_to_excel=False,_decimal=',')   

    estacions_xema.rename(columns={'codi_estacio':'Codi Estació',
                                   'nom_estacio':'Estació',
                                   'nom_comarca':'Comarca',
                                   'nom_provincia':'Provincia',
                                   'nom_municipi':'Municipi',
                                   'altitud':'Altitud',
                                   'latitud':'Latitud',
                                   'longitud':'Longitud',
                                   },inplace=True)
    #estacions_xema['Latitud'] = estacions_xema['Latitud'].astype(float)
    #estacions_xema['Longitud'] = estacions_xema['Longitud'].astype(float)

    # Retrieve and update local file
    try:
        estacions_old = pd.read_csv(_DATA_PATH+'estacions_xema.csv')
    except FileNotFoundError:
        # If not existing file a new df is created 
        estacions_old = pd.DataFrame(columns=estacions_xema.columns)
    
    estacions_xema.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    estacions_old.set_index(keys=["Codi Estació"],drop=False,inplace=True)

    # Identify existing stations
    existing_stations = estacions_xema[estacions_xema.index.isin(estacions_old.index)].copy()

    # if changes Latitud/Longitud, or Altitud==0 in xema or in local DB
    for index, station in existing_stations.iterrows():
        if  station['Latitud'] != estacions_xema.loc[index,'Latitud'] or \
            station['Longitud'] != estacions_xema.loc[index,'Longitud'] or \
            estacions_old.loc[index,'Altitud'] == 0 or \
            station['Altitud'] == 0:
            _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])

            existing_stations.loc[index,'Altitud'] = int(_altitud)
        else:
            existing_stations.loc[index,'Altitud'] = estacions_old.loc[index,'Altitud']

    estacions_old.update(existing_stations)
    
    # Identify new stations
    new_stations = estacions_xema[~estacions_xema.index.isin(estacions_old.index)]

    for index, station in new_stations.iterrows():
        if index == 0:
            print('Checking Googlemaps data...')

        _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
        new_stations.loc[index,'Altitud'] = int(_altitud)

    estacions_old.reset_index(drop=True,inplace=True)
    new_stations.reset_index(drop=True,inplace=True)
    estacions_incremental = pd.merge(new_stations, estacions_old.drop_duplicates(), on=estacions_old.columns.to_list(),
                how='outer', indicator=False)
    estacions_incremental.sort_values(by=['Codi Estació'], ascending=[True],inplace=True)

    estacions_incremental.to_csv(_DATA_PATH+'estacions_xema.csv',index=False)
    return estacions_incremental

def get_variables_xema(): # Get variables data from Meteocat
    variables = client.get(socrata_metadades_variables_xema, exclude_system_fields = 'true')
    variables_xema = pd.DataFrame.from_records(variables)
    variables_xema.rename(columns={'codi_variable':'Codi Variable',
                                   'nom_variable':'Variable',
                                   'unitat':'Unitat',
                                   'acronim':'Acronim',
                                   'codi_tipus_var':'Codi Tipus Variable',
                                   'decimals':'Decimals',
                                   },inplace=True)
    ###
    variables_xema.to_csv(_DATA_PATH+'variables_xema.csv',decimal=',',index=False)

    return variables_xema

def get_lectures_rain_xema(_myquery):  # Get lectures data from Meteocat
    lectures = client.get(socrata_lectures_xema, query=_myquery, exclude_system_fields='true')
    lectures_xema = pd.DataFrame.from_records(lectures)

    # If no records returned, return an empty dataframe
    if len(lectures_xema) == 0:
        return lectures_xema
        print(' ')
        print('NO RECORDS RETURNED FOR SELECTION -- Exiting program')
        print(' ')
        exit()

    if 'data_lectura' not in lectures_xema.columns:
        lectures_xema['data_lectura'] = lectures_xema['ultima_lectura']
    
    lectures_xema.rename(columns={'codi_estacio':'Codi Estació',
                                'ultima_lectura':'Ultima Lectura',
                                'codi_variable':'Codi Variable',
                                'valor_variable':'Total',
                                'data_lectura':'Data Lectura',
                                },inplace=True)
    return lectures_xema

def get_lectures_conditions_xema(_myquery):  # Get lectures data from Meteocat
    lectures = client.get(socrata_lectures_xema, query=_myquery, exclude_system_fields='true')
    lectures_xema = pd.DataFrame.from_records(lectures)

    # If no records returned, return an empty dataframe
    if len(lectures_xema) == 0:
        return lectures_xema
        print(' ')
        print('NO RECORDS RETURNED FOR SELECTION -- Exiting program')
        print(' ')
        exit()

    if 'data_lectura' not in lectures_xema.columns:
        lectures_xema['data_lectura'] = lectures_xema['ultima_lectura']
    
    lectures_xema.rename(columns={'codi_estacio':'Codi Estació',
                                'ultima_lectura':'Ultima Lectura',
                                'codi_variable':'Codi Variable',
                                'data_lectura':'Data Lectura',
                                },inplace=True)
    #print(lectures_xema.info())

    return lectures_xema

def get_results_rain_xema(results_xema:pd.DataFrame, estacions_df, variables_df):    # Create results_df from query to Meteocat data 
    _myquery0 = get_myquery(_codi_estacio,_qcodi_variable, _qcodi_variable2,_start_date, _end_date) # Get summarized data (1 record per station)
    _myquery = get_myquery_rain_all(_codi_estacio, _qcodi_variable, _qcodi_variable2,_start_date, _end_date) # Get detailed data (all rain records)
    #print(_myquery)

    # Get lectures_df from Meteocat according to _myquery
    lectures_xema = get_lectures_rain_xema(_myquery)
    '''print('')
    print('RAIN XEMA:')
    print(lectures_xema)'''
    # If not records returned, return empty dataframe
    if lectures_xema.empty:
        return lectures_xema
    
    # Merge estacions_df data and reject non existing codi_estacio
    results_xema = (pd.merge(lectures_xema, estacions_df, on = 'Codi Estació', how = 'inner'))

    # Merge variables_df data and reject non existing codi_variable 
    results_xema = (pd.merge(results_xema, variables_df, on = 'Codi Variable', how = 'inner'))
    results_xema = results_xema[['Codi Estació','Data Lectura','Estació','Comarca','Municipi','Provincia','Altitud',
                             'Latitud','Longitud','Ultima Lectura','Codi Variable',
                             'Variable','Total','Unitat','Decimals'
                            ]]
    results_xema['Total'] = results_xema['Total'].astype(float)
    results_xema['Altitud'] = results_xema['Altitud'].astype(str)
    results_xema['Latitud'] = results_xema['Latitud'].astype(str)
    results_xema['Longitud'] = results_xema['Longitud'].astype(str)

    pd.set_option('mode.chained_assignment', None)            # Reset warning on copy Dataframe
    results_xema.drop('Codi Variable', axis=1, inplace=True)  # Not needed by now
    results_xema.drop('Decimals', axis=1, inplace=True)       # Not needed by now
    '''results_df.rename(columns={'valor_variable':'Total',
                        'data_lectura':'Data Lectura',
                        'ultima_lectura':'Ultima Lectura',
                        'codi_estacio':'Codi Estació',
                        'nom_estacio':'Estació',
                        'nom_comarca':'Comarca',
                        'nom_provincia':'Provincia',
                        'nom_municipi':'Municipi',
                        'altitud':'Altitud',
                        'latitud':'Latitud',
                        'longitud':'Longitud',
                        'nom_variable':'Variable',
                        'unitat':'Unitat'    
                        },inplace=True)'''

    # Create New Columns from only Date and only Time from 'ultima_lectura'
    results_xema['Data Local'] = results_xema['Ultima Lectura'].astype(str)
    results_xema['Hora Local'] = results_xema['Ultima Lectura'].astype(str)

    # Convert 'Ultima Lectura' to local time and format 'Data Local' & 'Hora Local'
    for i in range(len(results_xema)):
        results_xema.loc[i, 'Ultima Lectura'] = (datetime.strptime(results_xema.loc[i,'Ultima Lectura'],'%Y-%m-%dT%H:%M:%S.%f')
                                                  + timedelta(hours=2,seconds=1)).strftime("%Y/%m/%d %H:%M:%S")

        results_xema.loc[i,'Data Local'] = datetime.strptime(results_xema.loc[i,'Ultima Lectura']
                                                             ,'%Y/%m/%d %H:%M:%S').strftime("%Y%m%d")   # Set Date as only date from 'Ultima Lectura'
        results_xema.loc[i,'Hora Local'] = datetime.strptime(results_xema.loc[i,'Ultima Lectura']
                                                             ,'%Y/%m/%d %H:%M:%S').strftime("%H:%M:%S")  # Set Time as only time from 'Ultima Lectura'
        
    ## Convert 'Ultima Lectura' to 'Data Lectura' in datetime for index
    results_xema['Data Lectura'] = pd.to_datetime(results_xema['Ultima Lectura'],format='%Y/%m/%d %H:%M:%S')
    results_xema.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)
    return results_xema

def get_results_conditions_xema(results_xema:pd.DataFrame, estacions_df, variables_df):    # Create results_df from query to Meteocat data 
    _myquery = get_myquery_conditions_all(_codi_estacio, _start_date, _end_date)    # Get daily data (temp/humidity)
    #print(_myquery)
    # Get lectures_df from Meteocat according to _myquery
    lectures_xema = get_lectures_conditions_xema(_myquery)
    '''print('')
    print('CONDITIONS XEMA:')
    print(lectures_xema)'''
    # If not records returned, return empty dataframe
    if lectures_xema.empty:
        return lectures_xema
    
    # Merge estacions_df data and reject non existing codi_estacio
    results_xema = (pd.merge(lectures_xema, estacions_df, on = 'Codi Estació', how = 'inner'))

    # Merge variables_df data and reject non existing codi_variable 
    results_xema = (pd.merge(results_xema, variables_df, on = 'Codi Variable', how = 'inner'))
    results_xema = results_xema[['Codi Estació','Data Lectura','Estació','Comarca','Municipi','Provincia','Altitud',
                             'Latitud','Longitud','Ultima Lectura','Codi Variable',
                             'Variable','max_valor_variable','min_valor_variable','Unitat','Decimals'
                            ]]
    results_xema['max_valor_variable'] = results_xema['max_valor_variable'].astype(float)
    results_xema['min_valor_variable'] = results_xema['min_valor_variable'].astype(float)

    pd.set_option('mode.chained_assignment', None)            # Reset warning on copy Dataframe
    results_xema.drop('Decimals', axis=1, inplace=True)       # Not needed by now

    for i in range(len(results_xema)):
        results_xema.loc[i, 'Ultima Lectura'] = (datetime.strptime(results_xema.loc[i,'Ultima Lectura'],'%Y-%m-%dT%H:%M:%S.%f')
                                                  + timedelta(hours=2,seconds=1)).strftime("%Y/%m/%d %H:%M:%S")
            
    ## Convert 'Ultima Lectura' to 'Data Lectura' in datettime for index
    results_xema['Data Lectura'] = pd.to_datetime(results_xema['Ultima Lectura'],format='%Y/%m/%d %H:%M:%S')

# Pivotar el DataFrame para obtener max y min valores para 'Codi Variable' 40 y 42
    pivot_df = results_xema.pivot_table(index=['Codi Estació', 'Data Lectura', 
                                               'Estació', 'Comarca','Municipi', 'Provincia', 
#                                               'Ultima Lectura', 'Variable', 
                                               ],
                            columns='Codi Variable',
                            values=['max_valor_variable', 'min_valor_variable'],
                            aggfunc='first').reset_index()

    pivot_df.columns = [f'{col[0]}_{col[1]}' if col[1] else col[0] for col in pivot_df.columns]

    # Agrupar por 'Codi Estació' y 'Data Lectura' y obtener los valores correspondientes a 'Codi Variable' 40 y 42
    pivot_df = pivot_df.groupby(['Codi Estació', 'Data Lectura']).agg({
        'Estació': 'first',
        'Comarca': 'first',
        'Municipi': 'first',
        'Provincia': 'first',
#        'Ultima Lectura': 'first',
        'max_valor_variable_40': 'first',
        'max_valor_variable_42': 'first',
        'min_valor_variable_40': 'first',
        'min_valor_variable_42': 'first',
        'max_valor_variable_44': 'first',
        'max_valor_variable_3': 'first',
        'min_valor_variable_44': 'first',
        'min_valor_variable_3': 'first'       
    }).reset_index()

    # Crear un nuevo DataFrame con las columnas requeridas
    new_columns = ['Codi Estació', 'Data Lectura', 
                   'Estació', 'Comarca', 'Municipi', 'Provincia', 
#                   'Ultima Lectura', 
                   'max_temp_celsius', 
#                   'min_temp_max_celsius', 
#                   'max_temp_min_celsius', 
                   'min_temp_celsius',
                   'max_humidity_percent',
#                   'min_humidity_max_percent',
#                   'max_humidity_min_percent',
                   'min_humidity_percent'
                   ]
    conditions_xema = pd.DataFrame(columns=new_columns)

    # Llenar el nuevo DataFrame con los valores pivotados
    conditions_xema['Codi Estació'] = pivot_df['Codi Estació']
    conditions_xema['Data Lectura'] = pivot_df['Data Lectura']
    conditions_xema['Estació'] = pivot_df['Estació']
    conditions_xema['Comarca'] = pivot_df['Comarca']
    conditions_xema['Municipi'] = pivot_df['Municipi']
    conditions_xema['Provincia'] = pivot_df['Provincia']
#    conditions_xema['Ultima Lectura'] = pivot_df['Ultima Lectura']
    conditions_xema['max_temp_celsius'] = pivot_df[('max_valor_variable_40')].astype(str)
    conditions_xema['min_temp_celsius'] = pivot_df[('min_valor_variable_42')].astype(str)
    conditions_xema['max_humidity_percent'] = pivot_df[('max_valor_variable_3')].astype(str)
    conditions_xema['min_humidity_percent'] = pivot_df[('min_valor_variable_44')].astype(str)

    conditions_xema.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)

    return conditions_xema

## END DATA RETRIEVAL FUNCTION DEFINITIONS
#In[8]  ##  Dataframes creation functions

def filter_results(df: pd.DataFrame, _minima_pluja):             # Filter data according to parameters
    df=df.copy()
    df = df.query('Total >= @_minima_pluja')
    return df

def save_dataframe(df:pd.DataFrame, _file_name, _save_to_csv=True, _save_to_excel=False, _decimal=','):
    #
    if _save_to_csv:                                                     # Save df to csv
        df.to_csv(_DATA_PATH+_file_name+'.csv', decimal=_decimal, index=False)
    #
    if _save_to_excel:                                                   # Save df to or excel
        df.to_excel(_DATA_PATH+_file_name+'.xlsx', decimal=_decimal, index=False)
    #

def save_dataframe_tomap(df, _file_name, _save_to_csv=True, _save_to_excel=False,_decimal='.'):
    #
    if _save_to_csv:                                                     # Save df to csv
        df.to_csv(_MAPS_PATH+_file_name+'.csv', decimal=_decimal, index=False)
    #
    if _save_to_excel:                                                   # Save df to or excel
        df.to_excel(_MAPS_PATH+_file_name+'.xlsx', decimal=_decimal, index=False)
    #

def save_incremental_meteocat(csv_param:pd.DataFrame, _save_to_excel):                          # Save incremental Dataframe                    
    csv=csv_param.copy()
    #
    try:
        # Intentar cargar el archivo CSV
        csv_old = read_incremental('Meteocat_incremental')
        #print('Meteocat incremental leido:',csv_old.info())
    except FileNotFoundError:
        # Si el archivo no se encuentra, crear un DataFrame vacío con las mismas columnas que csv
        csv_old = pd.DataFrame(columns=csv.columns)
    #
	# Update existing data in csv_old with values in csv just in case readings have changed (it happens!)
    csv_old.set_index(keys=["Codi Estació","Data Local"],drop=False,inplace=True)
	#
    csv.set_index(keys=["Codi Estació","Data Local"],drop=False,inplace=True)
    csv_old.update(csv)
	#
	# Merge new records from csv & csv_old into csv_incremental
    csv_old.reset_index(drop=True,inplace=True)
    csv.reset_index(drop=True,inplace=True)
    csv_incremental = pd.merge(csv, csv_old.drop_duplicates(), on=csv_old.columns.to_list(),
					how='outer', indicator=False)
    csv_incremental.sort_values(by=['Codi Estació','Data Local'], ascending=[True,False],inplace=True)
    csv_incremental.reset_index(drop=True, inplace=True)
	#
    # Filter rain > 0
    #csv_incremental = filter_results(csv_incremental,_minima_lectura_meteocat)
    #
	# Save incremental Dataframe to csv
    csv_incremental.to_csv(_DATA_PATH+'Meteocat_incremental.csv', decimal=',', index=False) #  Save to csv All incremental rain readings
    #print('Meteocat incremental salvado:',csv_incremental.info())
    #
	# Save csv_incremental Dataframe to Excel

    if _save_to_excel:
        csv_incremental['Altitud'] = csv_incremental['Altitud'].astype(float)
        csv_incremental['Latitud'] = csv_incremental['Latitud'].astype(float)
        csv_incremental['Longitud'] = csv_incremental['Longitud'].astype(float)
        csv_incremental.to_excel(_DATA_PATH+'Meteocat_incremental.xlsx', index=False) # Save to excel All incremental rain readings
    
    return csv_incremental

def save_incremental_meteoclimatic(csv_param:pd.DataFrame, _save_to_excel):                     # Save incremental Dataframe                    
    csv=csv_param.copy()
    #
    try:
        # Intentar cargar el archivo CSV
        #csv_old = pd.read_csv(_DATA_PATH+'Meteoclimatic_incremental.csv',decimal=',')
        csv_old = read_incremental('Meteoclimatic_incremental')

    except FileNotFoundError:
        # Si el archivo no se encuentra, crear un DataFrame vacío con las mismas columnas que csv
        csv_old = pd.DataFrame(columns=csv.columns)

	# Update existing data in csv_old with values in csv just in case readings have changed (it happens!)
    csv_old.set_index(keys=["Codi Estació","Data Local"],drop=False,inplace=True)
	#
    csv.set_index(keys=["Codi Estació","Data Local"],drop=False,inplace=True)
    csv_old.update(csv)
	#
	# Merge new records from csv & csv_old into csv_incremental
    csv_old.reset_index(drop=True,inplace=True)
    csv.reset_index(drop=True,inplace=True)
    csv_incremental = pd.merge(csv, csv_old.drop_duplicates(), on=csv_old.columns.to_list(),
					how='outer', indicator=False)

    csv_incremental.sort_values(by=['Codi Estació','Data Local'], ascending=[True,False],inplace=True)
    csv_incremental.reset_index(drop=True, inplace=True)
    #print(' ')
	#
    # Refresh Station data on incremental local DB from local DB of Stations
    estacions_meteoclimatic_df = pd.read_csv(_DATA_PATH+'estacions_meteoclimatic.csv',decimal=',')

    estacions_meteoclimatic_df.set_index(keys='Codi Estació',drop=False,inplace=True)
    csv_incremental.set_index(keys='Codi Estació',drop=False,inplace=True)
    csv_incremental.update(estacions_meteoclimatic_df)
    
    # Filter rain > _minima_lectura_meteoclimatic (Daily rain in Meteoclimatic - Discard minimum readings as are errors) 
    #csv_incremental = filter_results(csv_incremental,_minima_lectura_meteoclimatic)
    
    csv_incremental.reset_index(drop=True, inplace=True)

	# Save incremental Dataframe to csv
    csv_incremental.to_csv(_DATA_PATH+'Meteoclimatic_incremental.csv', decimal=',', index=False) #  Save to csv All incremental rain readings
	#
	# Save csv_incremental Dataframe to Excel

    if _save_to_excel:
        csv_incremental['Altitud'] = csv_incremental['Altitud'].astype(float)
        csv_incremental['Latitud'] = csv_incremental['Latitud'].astype(float)
        csv_incremental['Longitud'] = csv_incremental['Longitud'].astype(float)
        csv_incremental.to_excel(_DATA_PATH+'Meteoclimatic_incremental.xlsx', index=False) # Save to excel All incremental rain readings
    
    return csv_incremental

def create_total_dataframe(csv_param:pd.DataFrame, _save_to_excel, _save_to_csv):               # Create Total Dataframe 
    csv=csv_param.copy()
    #csv['Data Lectura'] = pd.to_datetime(csv['Ultima Lectura'])
    csv.set_index(keys=['Data Lectura'],drop=False,inplace=True)

    csv_total = csv.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud', 
                            'Variable',
                            'Unitat'],dropna=False). \
                    agg({'Codi Estació':'last',
                        'Estació':'last',
                        'Comarca':'last',
                        'Municipi':'last',
                        'Provincia':'last',
                        'Altitud':'last',
                        'Latitud':'last',
                        'Longitud':'last',
                        'Data Lectura':'max',
                        'Variable':'last',
                        'Total':'sum',
                        'Unitat':'last'                                       
                        }). \
                    round(1). \
                    rename(columns={'Data Lectura':'Ultima Lectura'}).\
                    sort_values(by=['Total'], ascending=[False],inplace=False)
    #
    csv_total.reset_index(drop=True,inplace=True)
    #
    # Sort in descending order by Accumulated precipitation
    #
    csv_total.sort_values(by=['Total'], ascending=False,inplace=True)
    csv_total.reset_index(drop=True,inplace=True)

    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    if _save_to_csv:
        csv_total.to_csv(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Total rain
    if _save_to_excel:
        csv_total['Altitud'] = csv_total['Altitud'].astype(float)
        csv_total['Latitud'] = csv_total['Latitud'].astype(float)
        csv_total['Longitud'] = csv_total['Longitud'].astype(float)
        csv_total.to_excel(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' al '+_data_fi+'.xlsx', index=False) # Save to excel Total rain
    #
    return csv_total

def create_total_meteoclimatic(csv_param:pd.DataFrame, _save_to_excel, _save_to_csv):               # Create Total Dataframe 
    csv=csv_param.copy()
    #csv['Data Lectura'] = pd.to_datetime(csv['Ultima Lectura'])
    csv.set_index(keys=['Data Lectura'],drop=False,inplace=True)

    csv_total = csv.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud', 
                            'Variable',
                            'Unitat'],dropna=False). \
                    agg({'Codi Estació':'last',
                        'Estació':'last',
                        'Comarca':'last',
                        'Municipi':'last',
                        'Provincia':'last',
                        'Altitud':'last',
                        'Latitud':'last',
                        'Longitud':'last',
                        'Data Lectura':'max',
                        'Variable':'last',
                        'Total':'sum',
                        'Unitat':'last',
                        'max_temp_celsius':'last',
                        'min_temp_celsius':'last',
                        'max_humidity_percent':'last',
                        'min_humidity_percent':'last'                                         
                        }). \
                    round(1). \
                    rename(columns={'Data Lectura':'Ultima Lectura'}).\
                    sort_values(by=['Total'], ascending=[False],inplace=False)
    #
    csv_total.reset_index(drop=True,inplace=True)
    csv_total['max_temp_celsius'] = csv_total['max_temp_celsius'].astype(str)
    csv_total['min_temp_celsius'] = csv_total['min_temp_celsius'].astype(str)
    csv_total['max_humidity_percent'] = csv_total['max_humidity_percent'].astype(str)
    csv_total['min_humidity_percent'] = csv_total['min_humidity_percent'].astype(str)
    #
    # Sort in descending order by Accumulated precipitation
    #
    #csv_total.sort_values(by=['Total'], ascending=False,inplace=True)
    #csv_total.reset_index(drop=True,inplace=True)

    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    if _save_to_csv:
        csv_total.to_csv(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Total rain
    if _save_to_excel:
        csv_total['Altitud'] = csv_total['Altitud'].astype(float)
        csv_total['Latitud'] = csv_total['Latitud'].astype(float)
        csv_total['Longitud'] = csv_total['Longitud'].astype(float)
        csv_total.to_excel(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' al '+_data_fi+'.xlsx', index=False) # Save to excel Total rain
    #
    return csv_total


def create_daily_dataframe(csv_param:pd.DataFrame, _save_to_excel):               # Create daily Dataframe
    csv_daily = csv_param.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Altitud', 
                            'Latitud',
                            'Longitud',
                            'Variable',
                            'Unitat',
                            pd.Grouper(key='Data Lectura',freq='D')])['Total']. \
                            sum().\
                            reset_index().\
                            rename(columns={'Data Lectura':'Data Pluja'}).\
                            round(1)

    csv_daily = csv_daily[['Codi Estació',
                            'Estació', 
                            'Comarca', 
                            'Municipi', 
                            'Provincia', 
                            'Altitud', 
                            'Latitud', 
                            'Longitud', 
                            'Variable', 
                            'Total', 
                            'Unitat',
                            'Data Pluja' 
                            ]]

    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    csv_daily.to_csv(_DATA_PATH+'Plujes_Diaries_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Daily rain
    if  _save_to_excel:
        csv_daily.to_excel(_DATA_PATH+'Plujes_Diaries_'+_data_inici+' a '+_data_fi+'.xlsx', index=False)      # Save to excel Daily rain
    return

def create_weekly_dataframe(csv_param:pd.DataFrame, _save_to_excel):                        # Create weekly Dataframe 
    csv_weekly = csv_param.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud', 
                            'Variable',
                            'Unitat',
                            pd.Grouper(key='Data Lectura',freq='W')])['Total'].sum().reset_index().round(1)
    #
    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    csv_weekly.to_csv(_DATA_PATH+'Plujes_Setmanals_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Weekly rain
    if  _save_to_excel:
        csv_weekly.to_excel(_DATA_PATH+'Plujes_Setmanals_'+_data_inici+' a '+_data_fi+'.xlsx', index=False) # Save to excel Weekly rain
    return

def create_monthly_dataframe(csv_param:pd.DataFrame,_save_to_excel):                       # Create monthly Dataframe
    csv_monthly = csv_param.groupby(['Codi Estació',  
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud', 
                            'Variable',
                            'Unitat',
                            pd.Grouper(key='Data Lectura',freq='M')])['Total'].sum().reset_index().round(1)
    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    csv_monthly.to_csv(_DATA_PATH+'Plujes_Mensuals_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Monthly rain
    if _save_to_excel:
        csv_monthly.to_excel(_DATA_PATH+'Plujes_Mensuals_'+_data_inici+' a '+_data_fi+'.xlsx', index=False) # Save to excel Monthly rain

def print_dataframes(df:pd.DataFrame, columns_to_print=None):  # Define a function to print some columns from a Dataframe
    if columns_to_print is None:        # If no columns list supplied, use default
        default_columns = ['Codi Estació', 
                           'Data Lectura',
                           'Estació',
                           'Municipi',
                           'Provincia',
                           'Altitud',
                           'Variable',
                           'Total',
                           'Unitat']
        columns_to_print = default_columns
    
    # Select columns to print
    print(df[columns_to_print].to_string(index=True))

def print_totals_per_station(csv_total:pd.DataFrame): # Print totals per station (csv_total) for selection in Terminal sorted by accumulated precipitation DESC 
    #
    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    print(" ")
    print("Dades XEMA & Meteoclimatic de Pluja acumulada:",len(csv_total), "Estacions reportan pluja")
    print("Minima pluja acumulada:",_minimum_rain_toprint, "mm")
    print("Data Inici:", utc_to_local(datetime.strptime(_data_inici,"%d-%m-%Y %H:%M:%S")).strftime("%d-%m-%Y %H:%M:%S"))
    print("Data Fi:", utc_to_local(datetime.strptime(_data_fi,"%d-%m-%Y %H:%M:%S")).strftime("%d-%m-%Y %H:%M:%S"))
    if len(csv_total) != 0:
        print("Codi Estació:"+_codi_estacio+" ("+(csv_total.iloc[-1]["Estació"])+")" 
            if _codi_estacio!='' and _codi_estacio!='ALL' 
            else "Totes les estacions")               
        print(" ")
    #
    for i in range(len(csv_total)):
        _this_codi_estacio = csv_total.iloc[i]['Codi Estació']
        _this_nom_estacio = csv_total.iloc[i]['Estació']
        #_this_nom_estacio = re.sub(r'\s*\[.*?\]\s*', '', _this_nom_estacio)
        #_this_nom_estacio = re.sub(r'^\[|\]$', '', _this_nom_estacio)
        _this_nom_municipi = csv_total.iloc[i]['Municipi']        
        _this_valor_variable = csv_total.iloc[i]['Total']
        _this_unitat = csv_total.iloc[i]['Unitat']
        _this_ultima_lectura =csv_total.iloc[i]['Ultima Lectura'].strftime("%d/%m/%Y %H:%M:%S CET")
    # 
    #   Print records from csv Dataframe in Console 
    #
        if False:
            print("REGISTRE:" + \
                    str(i), \
                    "Estació: "+ \
                    _this_codi_estacio+" - " + \
                    _this_nom_estacio+" [" + _this_nom_municipi+ \
                    "] - Pluja acumulada:", \
                    _this_valor_variable,\
                    _this_unitat, \
                    "- Ultima lectura: " + \
                    _this_ultima_lectura)
        elif True:
            print(f"REC: {i:<3} Estació: {_this_codi_estacio:<19} - {_this_nom_estacio:<40} [{_this_nom_municipi:<30}] - Pluja acumulada: {_this_valor_variable:<5} {_this_unitat:3} - Ultima pluja: {_this_ultima_lectura:<20}")
 
        else:
            print("REGISTRE:"+str(i),"Estació: "+ _codi_estacio+" (UNDEFINED) - Pluja acumulada:"\
                    ,_valor_variable,_unitat,"- Ultima lectura: "+\
                    _ultima_lectura)
    print("")

def refresh_estacions_meteoclimatic(meteoclimatic_df:pd.DataFrame):
    csv = meteoclimatic_df[['Codi Estació', 
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Altitud',
                            'Latitud',
                            'Longitud']].copy()

    try:
        # Try to read local DB of stations
        csv_old = pd.read_csv(_DATA_PATH+'estacions_meteoclimatic.csv',decimal=',')
    except FileNotFoundError:
        # If not existing file a new df is created 
        csv_old = pd.DataFrame(columns=csv.columns)

    #print(csv_old.info())
    csv_old.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    #
    csv.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    
    # Utilizamos una expresión regular para encontrar el último par de paréntesis en Estació y lo eliminamos
    # Utilizamos apply y una función lambda para aplicar la operación a cada elemento de la columna
    csv['Estació'] = csv['Estació'].apply(lambda x: re.sub(r'\([^)]*\)(?=[^()]*$)', '', x))

    # Get elevation for existing stations in 'estacions_meteoclimatic.csv' if not set or changed lat or long
    existing_stations = csv[csv.index.isin(csv_old.index )]

    for index, station in existing_stations.iterrows():
        try:
            _check_altitud = float(csv_old['Altitud'][index])
            if math.isnan(_check_altitud) or \
                csv_old.loc[index,'Municipi'] == 'To be set later' or \
                csv_old.loc[index,'Provincia'] == 'To be set later':
                _isvalid = False
            else:
                existing_stations.loc[index,'Altitud'] = csv_old.loc[index,'Altitud']
                existing_stations.loc[index,'Municipi'] = csv_old.loc[index,'Municipi']
                existing_stations.loc[index,'Provincia'] = csv_old.loc[index,'Provincia']
                _isvalid = True
        except ValueError:
            _isvalid = False

        if  station['Latitud'] != csv_old.loc[index,'Latitud'] or \
            station['Longitud'] != csv_old.loc[index,'Longitud'] or \
            not _isvalid: 
            #print('Estacion a actualizar', existing_stations['Codi Estació'][index])
            _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
            #print(_altitud,_municipi,_provincia)
            #existing_stations['Altitud'][index] = int(get_googlemaps(station['Latitud'], station['Longitud'],'elevation'))
            existing_stations.loc[index,'Altitud'] = int(_altitud)
            existing_stations.loc[index,'Municipi'] = _municipi
            existing_stations.loc[index,'Provincia'] = _provincia

    # Get elevation, municipi & provincia for new stations added to 'estacions_meteoclimatic.csv'
    new_stations = csv[ ~csv.index.isin(csv_old.index) ]
    for index, station in new_stations.iterrows():
        _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
        #new_stations['Altitud'][index] = int(get_googlemaps(station['Latitud'], station['Longitud'],'elevation'))
        new_stations.loc[index,'Altitud'] = int(_altitud)
        new_stations.loc[index,'Municipi'] = _municipi
        new_stations.loc[index,'Provincia'] = _provincia

    csv_old.update(existing_stations)
    csv.update(existing_stations)
    csv.update(new_stations)
    #
    # Merge new records from csv & csv_old into csv_incremental
    csv_old.reset_index(drop=True,inplace=True)
    new_stations.reset_index(drop=True,inplace=True)
    csv_incremental = pd.merge(new_stations, csv_old.drop_duplicates(), on=csv_old.columns.to_list(),
                how='outer', indicator=False)
    csv_incremental.sort_values(by=['Codi Estació'], ascending=[True],inplace=True)

    csv_incremental.reset_index(drop=True, inplace=True)

    # Save local DB of Stations for Meteoclimatic - Each new station read is added to local DB
    csv_incremental.to_csv(_DATA_PATH+'estacions_meteoclimatic.csv',decimal=',',index=False)
    return csv

def create_meteoclimatic(_save_to_csv):

    client = MeteoclimaticClient()
    meteoclimatic_df = client.weather_sel_stations("ESCAT")
    meteoclimatic_df = create_total_meteoclimatic(meteoclimatic_df, _save_to_excel = False, _save_to_csv=False)

    meteoclimatic_df['Data Local'] = meteoclimatic_df['Ultima Lectura']
    meteoclimatic_df['Hora Local'] = meteoclimatic_df['Ultima Lectura']

    meteoclimatic_df['Data Lectura'] = meteoclimatic_df['Ultima Lectura'].dt.tz_localize(tz=None)
    for i in range(len(meteoclimatic_df)):
        meteoclimatic_df.loc[i,'Data Lectura'] = utc_to_local(meteoclimatic_df.loc[i,'Data Lectura'])

    meteoclimatic_df['Ultima Lectura']= meteoclimatic_df['Data Lectura'].dt.strftime("%Y/%m/%d %H:%M:%S")
    meteoclimatic_df['Data Local'] = meteoclimatic_df['Data Lectura'].dt.strftime("%Y%m%d") # Set Date as only date from 'Ultima Lectura'
    meteoclimatic_df['Hora Local'] = meteoclimatic_df['Data Lectura'].dt.strftime("%H:%M:%S")  # Set Time as only time from 'Ultima Lectura'

    # Set order of columns to match Meteocat's columns order
    cols = meteoclimatic_df.columns.tolist()
    cols = cols[:1]+cols[-1:]+ cols[1:-1]
    meteoclimatic_df = meteoclimatic_df[cols].reset_index(drop=True)
    
    # Extract Provincia & Municipi from Station name on meteoclimatic data
    meteoclimatic_df['Provincia'] = meteoclimatic_df['Estació'].str.extract(r'\((.*?)\)')
    meteoclimatic_df['Municipi_temp'] = meteoclimatic_df['Estació'].str.extract(r'^(.*?) -')
    meteoclimatic_df['Municipi_temp'].fillna(meteoclimatic_df['Estació'].str.extract(r'^(.*?) \(')[0], inplace=True)
    meteoclimatic_df['Municipi'] = meteoclimatic_df['Municipi_temp']
    meteoclimatic_df.drop(columns=['Municipi_temp'], inplace=True)
    
    # Refresh local DB of stations (to not search for elevation in googlemaps all the time)
    refreshed_stations_df = refresh_estacions_meteoclimatic(meteoclimatic_df)
    
    # Update Altitud on meteoclimatic_df from local DB stations
    refreshed_stations_df.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    meteoclimatic_df.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    meteoclimatic_df.update(refreshed_stations_df)

    meteoclimatic_df.reset_index(drop=True,inplace=True)
    meteoclimatic_df.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)

    return meteoclimatic_df                             # Same format than Meteocat and with elevation set

def merge_dataframes(source01_df_param:pd.DataFrame, source02_df_param:pd.DataFrame, printit=False):
    ### Merge data from source01 & source02
    source01_df=source01_df_param.copy()
    if source01_df.empty:
        source01_df = read_incremental('Meteocat_incremental',_nrows=0)
    source02_df=source02_df_param.copy()
    if source02_df.empty:
        source02_df = read_incremental('Meteocat_incremental',_nrows=0)
    source01_df.reset_index(drop=True,inplace=True)
    source02_df.reset_index(drop=True,inplace=True)

    csv_completo = pd.merge(source01_df, source02_df.drop_duplicates(), on=source01_df.columns.to_list(),
					how='outer', indicator=False)

    csv_completo.sort_values(by=['Total','Codi Estació'], ascending=[False,True],inplace=True)
    csv_completo.reset_index(drop=True, inplace=True)
    if printit:
        if len(source02_df) != 0: 
            print('------------------------------------------')
            print('Data merged from source01 & source02:')
            print('------------------------------------------')

        else:
            print('-------------------------------------------------')
            print('Data merged from source01 & source02(EMPTY):')
            print('-------------------------------------------------')

        print_dataframes(csv_completo)
    return csv_completo

def create_filtered(df_to_filter_param:pd.DataFrame, _base_date, _days_backward, _days_forward):
    # Define una función para parsear las fechas y aplicar el filtro por rango de fechas
    df_to_filter=df_to_filter_param.copy()
    def custom_date_parser(date, start_date, end_date):
        parsed_date = pd.to_datetime(date, format='%Y%m%d', errors='coerce')
        if start_date <= parsed_date <= end_date:
            return parsed_date
        else:
            return None
    # Calcula start_date y end_date en función de la fecha base y los días hacia atrás y hacia adelante
    start_date = _base_date - timedelta(days=_days_backward)
    end_date = _base_date + timedelta(days=_days_forward)

    df_to_filter['Data Local'] = df_to_filter['Data Local'].apply(lambda x: custom_date_parser(x, start_date, end_date))
        
    #print(df_to_group.info())
    df_to_filter = df_to_filter.dropna(subset=['Data Local'])  # Elimina filas con fechas fuera del rango
    #print(df_to_group.info())
    return df_to_filter

def create_grouped(df_to_group_param:pd.DataFrame):
    df_to_group=df_to_group_param.copy()
    # Establece 'Ultima Lectura' como índice
    df_to_group.set_index(['Ultima Lectura'], drop=False, inplace=True)

    # Agrupa por 'Codi Estació', selecciona 'Ultima Lectura' como el último valor y suma la columna 'Total'
    datos_finales = df_to_group.groupby('Codi Estació').agg({
        'Codi Estació': 'last',
        'Estació': 'last',
        'Comarca': 'last',
        'Municipi': 'last',
        'Provincia': 'last',
        'Altitud': 'last',
        'Latitud': 'last',
        'Longitud': 'last',
        'Ultima Lectura': 'max',
        'Variable': 'last',
        'Total': lambda x: round(x.sum(), 1),
        'Unitat': 'last',
        'Data Local': 'max'
    }).sort_values(by=['Total'], ascending=[False]).reset_index(drop=True)  # Establece drop=True para eliminar el índice

    # Resultado final: datos_finales contiene las filas dentro del rango de fechas especificado,
    # donde 'Ultima Lectura' es el último valor dentro de cada grupo de 'Codi Estació',
    # y la columna 'Total' se suma para cada grupo de 'Codi Estació'
    # Se filtra que la lluvia total sea > que la _minimum_rain_toprint
    #print(datos_finales)
    #print(datos_finales.info())
    return filter_results(datos_finales,_minimum_rain_tomap)

def create_last_rains(df:pd.DataFrame, _nrecords):
    # Tu DataFrame original
    # df = ...

    # Operación 1
    result_step1 = df.groupby(['Codi Estació', 'Data Local'], as_index=False).agg({
        'Data Lectura': 'first',
        'Estació': 'first',
        'Comarca': 'first',
        'Municipi': 'first',
        'Provincia': 'first',
        'Altitud': 'first',
        'Latitud': 'first',
        'Longitud': 'first',
        'Ultima Lectura': 'first',
        'Variable': 'first',
        'Total': 'sum',
        'Unitat': 'first',
        'max_temp_celsius':'first',
        'min_temp_celsius':'first',
        'max_humidity_percent':'first',
        'min_humidity_percent':'first',
        'Hora Local': 'first'
    })
    
    result_step1 = filter_results(result_step1,_minimum_rain_tomap)
    # Operación 2
    result_step2 = result_step1.groupby('Codi Estació').apply(lambda x: x.nlargest(_nrecords, 'Data Local')).reset_index(drop=True)
    
    # Convertir 'Data Local' al formato YYYY/MM/DD
    result_step2['Data Local'] = pd.to_datetime(result_step2['Data Local']).dt.strftime('%Y/%m/%d')
    #print (result_step2)
    # Operación 3
    result_step3 = result_step2.pivot_table(index='Codi Estació', 
                                            columns=result_step2.groupby('Codi Estació').cumcount().add(1), 
                                            values=['Data Local', 'Total',
                                                    'max_temp_celsius','min_temp_celsius',
                                                    'max_humidity_percent','min_humidity_percent',
                                                    ], aggfunc='first')

    #print(result_step3)
    #print(result_step3.info())
    #print(_nrecords)

    # Renombrar las columnas 'Data Local' a 'Data_Pluja{i:02}' y convertirlas al formato DD/MM/YYYY
    for i in range(1, _nrecords+1):
        column_name = f'Data_Pluja{i:02}'
        result_step3[('Data Local', i)] = pd.to_datetime(result_step3[('Data Local', i)]).dt.strftime('%d/%m/%Y')
    
    #print(result_step3.info())
    #print(result_step3)
    #exit()
    # Renombrar las columnas
    result_step3.columns =  [f'Data_Pluja_{i:02}' for i in range(1, _nrecords+1)] + \
                            [f'Pluja_Diaria_{i:02}' for i in range(1, _nrecords+1)] + \
                            [f'Hum_Max_{i:02}' for i in range(1, _nrecords+1)] + \
                            [f'Temp_Max_{i:02}' for i in range(1, _nrecords+1)] + \
                            [f'Hum_Min_{i:02}' for i in range(1, _nrecords+1)] + \
                            [f'Temp_Min_{i:02}' for i in range(1, _nrecords+1)] 

                            
    result_step3.reset_index(drop=False,inplace=True)
    #
    for i in range(1, _nrecords+1):
        column_name = f'Data_Pluja_{i:02}'
        result_step3[column_name] = result_step3[column_name].astype(str).str.split('.').str[0]

    # Redondear las columnas 'Pluja_Diaria{i:02}' a un decimal
    for i in range(1, _nrecords+1):
        column_name = f'Pluja_Diaria_{i:02}'
        result_step3[column_name] = result_step3[column_name].round(decimals=1)

    result_final = result_step3

    #result_final.to_csv(_MAPS_PATH+'Last'+str(_nrecords)+'_rains.csv',decimal=',')
    result_final.to_csv(_MAPS_PATH+'Last'+str(_nrecords)+'_rains.csv')
    save_dataframe_tomap(result_final,_file_name='Last'+str(_nrecords)+'_rains',_save_to_csv=True,_decimal='.')
    return result_final


#In[10] ##  MAIN LOOP ## 
# 
# DEFINE BASE DATES FROM 00:00:00 TO 23:59:59 IN TODAY'S DATE
_data_inici_base = datetime.combine(date.today(), time())                               # Today at 00:00:00
_data_fi_base = datetime.combine(date.today(), time()) - timedelta(days=-1,seconds=1)   # Today at 23:59:59
#
_current_path = os.getcwd()
print('Current path',_current_path)
#
# GET START AND END DATES FOR QUERY
_start_date = get_query_date(_data_inici_base, _days_init)       # Start date for data selection
_end_date = get_query_date(_data_fi_base, _days_end)             # End date for data selection

## PRINT SET PARAMETERS TO TERMINAL
print('')
print("Set parameters")
print("--------------")
print('Start date:', utc_to_local(datetime.strptime(_start_date,'%Y-%m-%dT%H:%M:%S')).strftime('%d/%m/%Y %H:%M:%S'),' in local time')
print('End   date:',  utc_to_local(datetime.strptime(_end_date,'%Y-%m-%dT%H:%M:%S')).strftime('%d/%m/%Y %H:%M:%S'),' in local time')
print('')
print("Print totals:",_print_totals)
print("Print DataFrames:",_print_dataframes)
print("Create daily stats:",_create_daily_stats)
print("Create weekly stats:",_create_weekly_stats)
print("Create monthly stats:",_create_monthly_stats)
print('')
print("Create Meteocat:",_create_meteocat)
print("Save incremental Meteocat:",_incremental_meteocat)
print('')
print("Create Meteoclimatic:",_create_meteoclimatic)
print("Save incremental Meteoclimatic:",_incremental_meteoclimatic)
print('')

#################################
## Process Meteocalimatic data ##
#################################
if _create_meteoclimatic:
    start_count(_legend='Start processing Meteoclimatic...')
    meteoclimatic_df = create_meteoclimatic(_save_to_csv=True)
    
    if _incremental_meteoclimatic:                                                   
        meteoclimatic_incremental = save_incremental_meteoclimatic(meteoclimatic_df, _save_to_excel=False) 	# Saves incremental data to csv. Also to excel depending on param
    else:
        meteoclimatic_incremental = read_incremental('Meteoclimatic_incremental')
    
    # Filter results according to settings in parameters
    #meteoclimatic_df = filter_results(meteoclimatic_df,_minima_lectura_meteoclimatic)
    save_dataframe(meteoclimatic_df, 'Meteoclimatic', _save_to_csv=True, _save_to_excel=False,_decimal=',')   
    if _print_dataframes:
        print('------------------------')
        print('Data from Meteoclimatic:')
        print('------------------------')
        print_dataframes(meteoclimatic_df)

    end_count(_legend='Finished processing Meteoclimatic')
else:
    meteoclimatic_incremental = read_incremental('Meteoclimatic_incremental')
    meteoclimatic_df = read_incremental('Meteoclimatic_incremental',_nrows=0)
    
    #meteoclimatic_df = pd.read_csv(_DATA_PATH +'Meteoclimatic_incremental.csv',decimal=',',nrows=0)
    #meteoclimatic_df['Data Lectura'] = pd.to_datetime(meteoclimatic_df['Ultima Lectura'])

###########################
## Process Meteocat data ##
###########################
if _create_meteocat:
    start_count(_legend='Start processing Meteocat...')
    # DEFINE base data for Meteocat connection##
    # 
    # Unauthenticated client only works with public data sets. Note 'None'
    # in place of application token, and no username or password:
    socrata_domain = "analisi.transparenciacatalunya.cat"
    socrata_lectures_xema = "nzvn-apee"
    socrata_metadades_lectures_xema =  "4fb2-n3yi"
    socrata_metadades_estacions_xema = "yqwd-vj5e"
    socrata_metadades_variables_xema = "4fb2-n3yi"
    # If you choose to use a token, run the following command on the terminal (or add it to your .bashrc)
    # $ export SODAPY_APPTOKEN=<token>
    #socrata_token = os.environ.get("SODAPY_APPTOKEN")
    socrata_token = None

    client = Socrata(socrata_domain, socrata_token)

    # Example authenticated client (needed for non-public datasets):
    # client = Socrata(analisi.transparenciacatalunya.cat,
    #                  MyAppToken,
    #                  username="user@example.com",
    #                  password="AFakePassword")

    # Get Metadata for Stations and Variables - Only 1 reading per launch
    estacions_xema = get_estacions_xema()   # Get info data from estacions at Meteocat
    variables_xema = get_variables_xema()   # Get info data from variables at Meteocat 
    end_count(_legend='Processed Meteocat estacions&variables reading from Socrata')

    if _create_meteocat_conditions:
        meteocat_conditions_xema=get_results_conditions_xema(pd.DataFrame, estacions_xema, variables_xema)
        # Save current readings from meteocat_conditions_xema to csv
        #save_dataframe(meteocat_conditions_xema, 'Meteocat_conditions_xema.csv',_save_to_csv=True, _save_to_excel=False, _decimal='.')
        if meteocat_conditions_xema.empty:
            meteocat_conditions_xema = read_incremental('Meteocat_incremental',_nrows=0)
        end_count(_legend='Processed Meteocat reading conditions temperature.max/min -  humidity.max&min from Socrata')

    meteocat_rain_xema = get_results_rain_xema(pd.DataFrame, estacions_xema, variables_xema)
    if meteocat_rain_xema.empty:
            meteocat_rain_xema = read_incremental('Meteocat_incremental',_nrows=0)
    meteocat_df = pd.merge(meteocat_rain_xema, meteocat_conditions_xema.drop_duplicates(), 
                              on=('Codi Estació','Estació','Data Lectura','Comarca','Municipi','Provincia'),
					how='left', indicator=False)
    #save_dataframe(meteocat_merge, 'Meteocat_merged_xema.csv',_save_to_csv=True, _save_to_excel=False, _decimal='.')
    #meteocat_df = meteocat_merge
    end_count(_legend='Processed Meteocat reading precipitation from Socrata')
    # If no records returned, initialize empty meteocat's dataframes with columns from incremental
    if meteocat_df.empty:
        meteocat_incremental = read_incremental('Meteocat_incremental')
        meteocat_df = read_incremental('Meteocat_incremental',_nrows=0)       

    if _incremental_meteocat:
        #print('Meteocat creado:',meteocat_df.info())                                           
        meteocat_incremental = save_incremental_meteocat(meteocat_df, _save_to_excel=False) 			 # Saves incremental data to csv. Also to excel depending on param
        #print('Meteocat incremental:',meteocat_incremental.info())
    else:
        meteocat_incremental = read_incremental('Meteocat_incremental')
    # Filter results according to settings in parameters
    #meteocat_df = filter_results(meteocat_df, _minima_lectura_meteocat)
    # Save current readings from meteocat to csv
    save_dataframe(meteocat_df, 'Meteocat', _save_to_csv=True, _save_to_excel=False,_decimal=',')

    if _print_dataframes:
        print('-------------------')
        print('Data from Meteocat:')
        print('-------------------')
        print_dataframes(meteocat_df)
        
    end_count(_legend='Finished processing Meteocat')
else:
    meteocat_incremental = read_incremental('Meteocat_incremental')
    meteocat_df = read_incremental('Meteocat_incremental',_nrows=0)

if _print_totals:                                              # Create totals per station sorted by precipitacion DESC
    # Defines base date
    start_count(_legend='Start printing routine')
    _base_date = _data_inici_base
    _days_backward = _days_init * -1
    _days_forward = _days_end
    meteoclimatic_df= create_filtered(meteoclimatic_incremental,_base_date, _days_backward, _days_forward)
    meteoclimatic_df=filter_results(meteoclimatic_df,_minima_pluja=0.4)
    meteocat_df = create_filtered(meteocat_incremental,_base_date, _days_backward, _days_forward)
    meteocat_df=filter_results(meteocat_df,_minima_pluja=0.4)
    df_toprint = merge_dataframes(meteocat_df, meteoclimatic_df, _print_dataframes)
    csv_total= create_total_dataframe(df_toprint, _save_to_csv=False, _save_to_excel=False)
    #else:
    #    df_toprint = merge_dataframes(meteocat_df, meteocat_df.iloc[:0,:].copy(),_print_dataframes)
    #    csv_total= create_total_dataframe(df_toprint, _save_to_csv=True, _save_to_excel=False)

    csv_total = filter_results(csv_total,_minima_pluja=_minimum_rain_toprint)
    print_totals_per_station(csv_total)
    end_count(_legend='End printing routine')


## Recuperar de Meteocat_incremental.csv los ultimos 3 meses
## Recuperar de Meteoclimatic_incremental.csv los ultimos 3 meses
## Hacer Merge de los 2 dataframes
## Llamar funcion que cree el fichero diario
## LLamar funcion que cree el fichero semanal
## etc...

if _create_daily_stats:                                                  # Create daily summary and save to csv
    create_daily_dataframe(meteocat_df, _save_to_excel=False)

if _create_weekly_stats:                                                 # Create weekly summary and save to csv
    create_weekly_dataframe(meteocat_df, _save_to_excel=False)

if _create_monthly_stats:                                                # Create monthly summary and save to csv
    create_monthly_dataframe(meteocat_df, _save_to_excel=False)
#

############ REVISAR ESTO DE AQUI ABAJO
if not _create_googlemaps_files:
    exit()

##################################################################################
### GRABAR csvs PARA PUBLICAR EN GOOGLEMAPS - 90-60-30-21-15-7-1 DAYS desde hoy ##
##################################################################################
if len(meteoclimatic_incremental) == 0 and len(meteocat_incremental) == 0:
    print(' ')
    print('NO RECORDS RETURNED FOR SELECTION -- Exiting program')
    print(' ')
    exit()

# Defines base date
_base_date = _data_inici_base

#  RAIN LAST 90 DAYS
start_count('Start processing 90 days backward map...')
# Defines days backward & forward from _base_date
_days_backward = 90  
_days_forward = 1     # Including Today

meteoclimatic_df = create_filtered(meteoclimatic_incremental,_base_date, _days_backward, _days_forward)
meteocat_df = create_filtered(meteocat_incremental,_base_date, _days_backward, _days_forward)

df_total = merge_dataframes(meteocat_df, meteoclimatic_df)
end_count('Finished creating 90 days filtered Dataframe...')

# AQUI crear el DataFrame con las lluvias diarias acumuladas de df_total: --> Solo será de los ultimos 90 dias, pero bueno
# - Acumuladas por 'Codi Estació' y 'Data Local', sumando 'Total'
# - Filtrando solo aparezcan 10 resultados por cada 'Codi Estació', los 10 primeros ordenando por 'Data Local' descending
# - Sacar solo 1 regitro por 'Codi Estació' y con 10 columnas de 'Data_plujaXX' y 10 columnas de 'Pluja_dia_XX' --> Revisar si poner algo mas
# - Llamarlo df_last_rains y salvarlo como 'Last_rains.csv'
#print('df_total.info():')
#print(df_total.info())
#exit()
df_last_rains= create_last_rains(df_total, _nrecords=_last_number_rains)
end_count('Finished creating last '+str(_last_number_rains)+' rains...')

df_toprint = create_grouped(df_total)

df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
save_dataframe_tomap(df_tomap, '07_Tomap_Last_three_months', _save_to_csv=True, _save_to_excel=False)
end_count('Finished processing 90 days backward map')

# RAIN LAST 60 DAYS
start_count('Start processing 60 days backward map...')
# Defines days backward & forward from _base_date
_days_backward = 60  
#_days_forward = 0     # Including Today

df_toprint = create_filtered(df_total,_base_date, _days_backward, _days_forward)
df_toprint = create_grouped(df_toprint)

df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
save_dataframe_tomap(df_tomap, '06_Tomap_Last_two_months', _save_to_csv=True, _save_to_excel=False)
end_count('Finished processing 60 days backward map')

#  RAIN LAST 30 DAYS
start_count('Start Processing 30 days backward map...')
# Defines days backward & forward from _base_date
_days_backward = 30  
#_days_forward =0     # Including Today

df_toprint = create_filtered(df_total,_base_date, _days_backward, _days_forward)
df_toprint = create_grouped(df_toprint)

df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
save_dataframe_tomap(df_tomap, '05_Tomap_Last_month', _save_to_csv=True, _save_to_excel=False)
end_count('Finished processing 30 days backward map')

#  RAIN LAST 21 DAYS
start_count('Start processing 21 days backward map...')
# Defines days backward & forward from _base_date
_days_backward = 21  
#_days_forward = 0     # Including Today

df_toprint = create_filtered(df_total,_base_date, _days_backward, _days_forward)
df_toprint = create_grouped(df_toprint)

df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
save_dataframe_tomap(df_tomap, '04_Tomap_Last_three_weeks', _save_to_csv=True, _save_to_excel=False)
end_count('Finished processing 21 days backward map')

#  RAIN LAST 15 DAYS
start_count('Start processing 15 days backward map...')
# Defines days backward & forward from _base_date
_days_backward = 15       
#_days_forward = 0     # Including Today

df_toprint = create_filtered(df_total,_base_date, _days_backward, _days_forward)
df_toprint = create_grouped(df_toprint)

df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
save_dataframe_tomap(df_tomap, '03_Tomap_Last_two_weeks', _save_to_csv=True, _save_to_excel=False)
end_count('Finished processing 15 days backward map')

# RAIN LAST 7 DAYS
start_count('Start processing 7 days backward map...')
# Defines days backward & forward from _base_date
_days_backward = 7        
#_days_forward =0     # Including Today

df_toprint = create_filtered(df_total,_base_date, _days_backward, _days_forward)
df_toprint = create_grouped(df_toprint)

df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
save_dataframe_tomap(df_tomap, '02_Tomap_Last_week', _save_to_csv=True, _save_to_excel=False)
end_count('Finished processing 7 days backward map')

# RAIN LAST 1 DAYS
start_count('Start processing 1 days backward map...')
# Defines days backward & forward from _base_date
_days_backward = 0        
#_days_forward = 0     # Including Today

df_toprint = create_filtered(df_total,_base_date, _days_backward, _days_forward)
df_toprint = create_grouped(df_toprint)

df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
save_dataframe_tomap(df_tomap, '01_Tomap_Last_day', _save_to_csv=True, _save_to_excel=False)
end_count('Finished processing 1 days backward map')

print('')
