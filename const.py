import os

_script_path = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.path.join(_script_path, 'Data/')
_PLOT_PATH = os.path.join(_script_path, 'Plots/')
_MAPS_PATH = os.path.join(_script_path, 'Tomap/')
_GMAPS_KEY = os.environ.get('GMAP_API_KEY')
#
_PYTHON_REQUIRES='>=3.11'
#
#  VARIABLES FOR PROCESSING
_days_init = -7                         # NUMBER OF DAYS BACKWARD FOR START DATE ((Meteocat))
_days_end = 0                           # NUMBER OF DAYS BACKWARD FOR END DATE ((Meteocat))
_days_bucket = 10                       # NUMBER OF DAYS OF BUCKET SELECTION FROM METEOCAT (DUE TO THROTTLING RESTRICTIONS)
_qcodi_variable = "'35'"                # VARIABLE FOR PRECIPITATION = 35 ((Meteocat))
_qcodi_variable2 = "'35'"               # SECOND VARIABLE RESERVATION (JUST IN CASE) ((Meteocat))
_codi_estacio = 'ALL'                   # ALL STATIONS - PUT HERE 'codi_estacio' if just want one ((Meteocat))
_minima_lectura_meteoclimatic = 0       # RAIN per reading must be >=     For Meteoclimatic stations
_minima_lectura_meteocat = 0            # RAIN per reading must be >=     For Meteocat stations
_minimum_rain_toprint = 1               # MINIMUM RAIN per period to output to print ((Meteocat & Meteoclimatic))
_minimum_rain_tomap = 0                 # MINIMUM RAIN per day to output to map ((Meteocat & Meteoclimatic))
_print_totals = True                    # Print Totals per station (Meteocat & Meteoclimatic if created)
_create_meteocat = True                 # Get data from Meteocat  (Meteocat)
_incremental_meteocat = True            # Saves incremental data from Meteocat locally (Meteocat)
_create_meteocat_conditions = True      # Get temperature data from Meteocat  (Meteocat)
_create_daily_stats = False             # Create daily summary for Meteocat and save to csv (Meteocat)
_create_weekly_stats = False            # Create weekly summary for Meteocat and save to csv (Meteocat)
_create_monthly_stats = False           # Create monthly summary for Meteocat and save to csv (Meteocat)
_create_meteoclimatic = True            # Get data from Meteoclimatic (it has just last reading, no range selection) (Meteoclimatic)
_incremental_meteoclimatic = True       # Saves incremental Meteoclimatic data locally (Meteoclimatic)
_create_wunderground = True             # Get data from Wrunderground (Wunderground)
_incremental_wunderground = True        # Saves incremental Wunderground data locally (Wunderground)
_create_googlemaps_files = True         # Creates csv files to map
_last_number_rains = 20                 # Number of rains to generate for map
_print_dataframes = False
#_codi_provincia = '' ## NOT IMPLEMENTED