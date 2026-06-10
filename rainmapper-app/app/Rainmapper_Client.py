import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, timezone
from pytz import timezone
from bokeh.io import output_notebook, output_file, show
from bokeh.plotting import gmap
from bokeh.models import ColumnDataSource, HoverTool, ColorBar, GMapOptions
from bokeh.transform import linear_cmap
from bokeh.palettes import YlOrRd9 as palette
#from bokeh.models import ColorBar
from const import _MAPS_PATH, _PLOT_PATH, _GMAPS_KEY

def plot_map(_title, lat, lng, map_type='roadmap', _zoom_level=8,_alpha=0.8):
    global df
    # List with all rain date columns
    rain_columns = [col for col in df.columns if col.startswith('Pluja_Diaria_')]
    max_temperature_columns = [col for col in df.columns if col.startswith('Temp_Max_')] 
    min_temperature_columns = [col for col in df.columns if col.startswith('Temp_Min_')]

    # Find max rain day over daily rain columns and add day number in a new  column
    df['max_rain_column'] = df[rain_columns].apply(lambda row: row.idxmax() if not all(pd.isna(row)) else np.nan, axis=1)
    df['max_temperature_column'] = df[max_temperature_columns].apply(lambda row: row.idxmax() if not all(pd.isna(row)) else np.nan, axis=1)
    df['min_temperature_column'] = df[min_temperature_columns].apply(lambda row: row.idxmin() if not all(pd.isna(row)) else np.nan, axis=1)
    # Old pandas < 3.0 style, now avoided because it triggers chained-assignment FutureWarning:
    # df['max_rain_column'].fillna('Pluja_Diaria_01', inplace=True)
    # df['max_temperature_column'].fillna('Temp_Max_01', inplace=True)
    # df['min_temperature_column'].fillna('Temp_Min_01', inplace=True)
    df['max_rain_column'] = df['max_rain_column'].fillna('Pluja_Diaria_01')  # pandas 3.0-compatible: assign the filled Series back to the original column.
    df['max_temperature_column'] = df['max_temperature_column'].fillna('Temp_Max_01')  # pandas 3.0-compatible: assign the filled Series back to the original column.
    df['min_temperature_column'] = df['min_temperature_column'].fillna('Temp_Min_01')  # pandas 3.0-compatible: assign the filled Series back to the original column.

    #print(df.info())
    #print(df)
    for index,rains  in df.iterrows():
        df.loc[index,'max_rain_column'] = df.loc[index,'max_rain_column'].split('_')[-1]
        #print(df.loc[index,'max_temperature_column'])
        df.loc[index,'max_temperature_column'] = df.loc[index,'max_temperature_column'].split('_')[-1]
        df.loc[index,'min_temperature_column'] = df.loc[index,'min_temperature_column'].split('_')[-1]
    #df['max_rain_column'] = df['max_rain_column'].astype(str)
    #df['max_temperature_column'] = df['max_temperature_column'].astype(str)
    #df['min_temperature_column'] = df['min_temperature_column'].astype(str)    
    df.to_csv(_MAPS_PATH+_file+'_with_maxs.csv')

    # the tools are defined below:s
    # Iterate over columns and add tooltips dinamically 
    tooltips = [('Estació:', '@Codi_Estacio - @Estacio'),
                ('Municipi:', '@Municipi - @Altitud metros'),
                ('Pluja acumulada:', '@Total{1.1} mm')]

    for index, column in enumerate(rain_columns):
        day_number = column.split('_')[-1]  # Obtiene el número del día desde el nombre de la columna        
        tooltip_text = f"@Data_Pluja_{day_number} (fa @Dias_{day_number} díes)=@Pluja_Diaria_{day_number}{{1.1}} mm"

        tooltip_conditions = ''
        tooltip_conditions = f"@Temp_Max_{day_number}{{1.1}} / @Temp_Min_{day_number}{{1.1}} °C"

#       Text for first rain
        if index == 0:                              
            tooltips.append(('Ultimes Plujes:', tooltip_text+' --> '+tooltip_conditions))
#       Text for all other rains
        else:
            tooltips.append(('', tooltip_text+' --> '+tooltip_conditions))

#       Append indicator for max rain over all rain columns
        #print('Column:',column,'max_rain_column',df['max_rain_column'].iloc[index])
        #if column == df['max_rain_column'].iloc[index]:
        #    tooltip_text += " (MAX RAIN)"


    TOOLTIPS1 = """
    <div style="min-width: 200px; display: flex; flex-direction: column;">        
        <div>
            <img
                src="@imgs" height="{ancho_max}" alt="@imgs" width="{ancho_max}"
                style="float: left; margin: 0px 15px 15px 0px;"
                border="2"
            ></img>
        </div>
        <div>
            <span style="font-size: 17px; font-weight: bold; order: 2;">@desc</span>"""
    TOOLTIPS2 = """
            <span style="font-size: 15px; color: #966;">[$index]</span>
        </div>
        <div>
            <span>@fonts{safe}</span>
        </div>
        <div style="display: flex; flex-direction: row;">
            <span style="font-size: 15px; display:inline;order:2;">Location</span>
            <span style="font-size: 15px; color: #696; display:inline; order: 1;">($x, $y)</span><br>
            <span style="font-size: 15px; display:block;order:3;">Ubicacion</span>
            <span style="font-size: 15px; color: #696; display:inline; order: 4;">($x, $y)</span>
        </div>
    </div>
    """
    TOOLTIPS = TOOLTIPS1 + TOOLTIPS2


    hover = HoverTool(tooltips=tooltips)
    gmap_options = GMapOptions(lat=lat, lng=lng, 
                               map_type=map_type, zoom=_zoom_level)

    p = gmap(_GMAPS_KEY, gmap_options, title=_title, 
             width=bokeh_width, height=bokeh_height, match_aspect=True,
             tools=[hover, 'reset','wheel_zoom', 'pan'],toolbar_location="above")

    #p.add_tools(HoverTool(tooltips=tooltips, mode='vline'))

    # definition of the column data source: 
    source = ColumnDataSource(df)
    # defining a color mapper, that will map values of rain
    # between min and max on the color palette
    mapper = linear_cmap('Total', palette, _min_rain, _max_rain)    
    # we use the mapper for the color of the circles
    # see how we specify the x and y columns as strings,
    # define the radius of the circles to be consistent at different zoom levels 
    # and how to declare as a source the ColumnDataSource:
    p.circle('Longitud', 'Latitud', radius='radius', alpha=_alpha, 
                      color=mapper, source=source)
    # and we add a color scale to see which values the colors 
    # correspond to 
    color_bar = ColorBar(color_mapper=mapper['transform'], 
                         location=(0,0))
    p.add_layout(color_bar, 'right')
    show(p)
    #from bokeh.models import Button, CustomJS
    #from bokeh.layouts import column
#
    #button = Button(label="Mi Boton", button_type="success")
    #button.js_on_click(CustomJS(code="console.log('button: click!', this.toString())"))
    #layout = column(button,p)
    #show(layout)
    return p

def process_map(_file):
    global df
    df = pd.read_csv(_MAPS_PATH+_file+'.csv')
    # adjust names for Bokeh
    df.rename(columns={ 'Codi Estació':'Codi_Estacio',
                        'Estació': 'Estacio',
                        'Ultima Lectura':'Ultima_Lectura',
                        'Data Local':'Data_Local'
                        }
                        , inplace=True)
    #df['Totalfloat'] = df['Total'].str.replace(',', '.').astype(float)

    global _max_rain, _min_rain
    _max_rain = df['Total'].max()
    _min_rain = df['Total'].min()
    #print(df.info())
    #exit()
    df['Ultima_Lectura'] = pd.to_datetime(df['Ultima_Lectura']).dt.strftime('%d/%m/%Y %H:%M:%S')
    df['Data_Local'] = pd.to_datetime(df['Data_Local']).dt.strftime('%d/%m/%Y')
    # Create new columns with number of days from last rain --> As many columns as 'Data_Pluja_' pattern
    rain_date_columns = [col for col in df.columns if col.startswith('Data_Pluja_')]
    for date_column in rain_date_columns:
        df[f'Dias_{date_column[-2:]}'] =abs((pd.to_datetime(df[date_column],format="%d/%m/%Y").dt.tz_localize('CET')
                    - datetime.now(timezone('CET'))).dt.days + 1)
    #print(df.info())
    #exit()
    min_radius = 5
    df['radius'] = np.maximum(np.sqrt(df['Total'])*2, min_radius)

    # Calcular el rango de valores para el radio (0 a 7000)
    max_radius = 7000

    # Calcular la diferencia entre el máximo y el mínimo
    rain_range = _max_rain - _min_rain

    # Calcular el radio para cada valor en 'Totalfloat'
    #df['radius'] = np.sqrt((df['Totalfloat'] - _min_rain) / rain_range) * max_radius * 1.2

    min_radius = 500

    # Realizar el cálculo para 'radius' y asegurar que el valor mínimo sea 1000
    df['radius'] = np.maximum(np.sqrt((df['Total'] - _min_rain) / rain_range) * max_radius * 0.5, min_radius)    
    #df['radius'] = min_radius  

## MAIN ###
bokeh_width, bokeh_height = 1450,900
_zoom_level = 8
_alpha = 0.7
_map_type = 'hybrid'   # hybrid - roadmap - satellite - terrain
_output_file = True

global df           # Global df to be used in process_map & plot_map
df=pd.DataFrame()
#output_notebook(hide_banner=True)

#Center of the map
lat, lon = 41.7963, 1.9514  # Original
lat, lon = 41.8329, 1.7524  # Suria

_sufix = datetime.now(timezone('CET')).strftime("%d/%m/%Y %H:%M:%S (%Z = UTC%z)")

_file='07_Tomap_Last_three_months'
_title='Pluja últims 3 mesos - a '+_sufix
process_map(_file)
output_file(filename=_PLOT_PATH+_file+'.html',title=_title)

plot_map(_title, lat, lon, map_type=_map_type,_zoom_level=_zoom_level,_alpha=_alpha)

_file='06_Tomap_Last_two_months'
_title='Pluja últims 2 mesos - a '+_sufix
process_map(_file)
output_file(filename=_PLOT_PATH+_file+'.html',title=_title)
plot_map(_title, lat, lon, map_type=_map_type,_zoom_level=_zoom_level,_alpha=_alpha)

_file='05_Tomap_Last_month'
_title='Pluja últim mes - a '+_sufix
process_map(_file)
output_file(filename=_PLOT_PATH+_file+'.html',title=_title)
plot_map(_title, lat, lon, map_type=_map_type,_zoom_level=_zoom_level,_alpha=_alpha)

_file='04_Tomap_Last_three_weeks'
_title='Pluja últimes 3 setmanes - a '+_sufix
process_map(_file)
output_file(filename=_PLOT_PATH+_file+'.html',title=_title)
plot_map(_title, lat, lon, map_type=_map_type,_zoom_level=_zoom_level,_alpha=_alpha)

_file='03_Tomap_Last_two_weeks'
_title='Pluja últimes 2 setmanes - a '+_sufix
process_map(_file)
output_file(filename=_PLOT_PATH+_file+'.html',title=_title)
plot_map(_title, lat, lon, map_type=_map_type,_zoom_level=_zoom_level,_alpha=_alpha)

_file='02_Tomap_Last_week'
_title='Pluja última setmana - a '+_sufix
process_map(_file)
output_file(filename=_PLOT_PATH+_file+'.html',title=_title)
plot_map(_title, lat, lon, map_type=_map_type,_zoom_level=_zoom_level,_alpha=_alpha)

_file='01_Tomap_Last_day'
_title='Pluja últim dia - a '+_sufix
process_map(_file)
output_file(filename=_PLOT_PATH+_file+'.html',title=_title)
plot_map(_title, lat, lon, map_type=_map_type,_zoom_level=_zoom_level,_alpha=_alpha)
