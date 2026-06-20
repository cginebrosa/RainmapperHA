import unicodedata
from datetime import datetime
from rainmapper_core.config import config

MONTHLY = config.MONTHLY

class Parser:
    @staticmethod
    def format_key(key: str) -> str:
        # Replace white space and delete dots
        return key.replace(' ', '_').replace('.', '')

    @staticmethod
    def parse_html_table(date_string: str, 
                         history_table: list, 
                         station_ID: str, 
                         station_name: str,
                         location_name: str,
                         elevation: float,
                         latitude: float,
                         longitude: float) -> dict:
        #Añadido
        #data_dict = {}
        #index = 0 
        #Fin Añadido

        if MONTHLY:
            table_rows = [tr for tr in history_table[0].xpath('//tr') if len(tr) == 16]
        else:
            table_rows = [tr for tr in history_table[0].xpath('//tr') if len(tr) == 12]

        headers_list = []
        data_rows = []
        #print(f'table_rows: {table_rows}')

        # set Table Headers
        for header in table_rows[0]:
            #print(header.text)
            headers_list.append(header.text)

        for tr in table_rows[1:]:
            row_dict = {}
            for i, td in enumerate(tr.getchildren()):
                td_content = unicodedata.normalize("NFKD", td.text_content())
                #print(f"Contenido de la celda {i}: {td_content}")                
                # set date and time in the first 2 columns
                if i == 0:
                    row_dict['StationID'] = station_ID
                    row_dict['StationName'] = station_name
                    row_dict['Municipi'] = location_name
                    row_dict['Comarca'] = 'Not set yet'
                    row_dict['Provincia'] = 'Not set yet'
                    row_dict['Elevation'] = elevation
                    row_dict['Latitude'] = latitude
                    row_dict['Longitude'] = longitude
                    if MONTHLY:
                        date = datetime.strptime(td_content, "%m/%d/%Y")
                        row_dict['Date'] = date.strftime('%Y-%m-%d')
                        #time = datetime.strptime(td_content, "%I:%M %p")
                        row_dict['Time'] = '02:00:01'

                    else:
                        date = datetime.strptime(date_string, "%Y-%m-%d")
                        row_dict['Date'] = date.strftime('%Y-%m-%d')
                        time = datetime.strptime(td_content, "%I:%M %p")
                        row_dict['Time'] = time.strftime('%I:%M %p')
                else:
                    #print(headers_list[i])
                    #Eliminada row_dict[Parser.format_key(headers_list[i])] = td_content
                    #AÑADIDO
                    key = Parser.format_key(headers_list[i])
                    original_key = key
                    suffix = 1
                    while key in row_dict:
                        key = f"{original_key}_{suffix}"
                        suffix += 1
                    row_dict[key] = td_content                    
                    
                    #FIN AÑADIDO
                    #print(row_dict)

            data_rows.append(row_dict)
            #print(row_dict)
        
        return data_rows
