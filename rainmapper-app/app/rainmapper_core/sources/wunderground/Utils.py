import config
from datetime import timedelta, date
import lxml.html as lh
import requests

MONTHLY = config.MONTHLY

class Utils:
    session = requests.Session()
    weather_station_url = None

    def __init__(self, session, weather_station_url):
        self.session = session
        self.weather_station_url = weather_station_url
        
    @classmethod
    def date_range_generator(cls, start, end = date.today()):
        if MONTHLY:
             # Inicializar la fecha actual al inicio del mes de la fecha de inicio
            current = start.replace(day=1)
            
            while current <= end:
                # Encontrar el último día del mes actual
                next_month = current.replace(day=28) + timedelta(days=4)  # Esto asegura que estamos en el próximo mes
                last_day_of_month = next_month - timedelta(days=next_month.day)
                
                if last_day_of_month < start:
                    current = next_month.replace(day=1)
                    continue

                #print(last_day_of_month)
                yield last_day_of_month

                # Avanzar al primer día del próximo mes
                current = next_month.replace(day=1)

            # Asegurar que el último día del mes de end sea incluido si end no es el último día del mes
            if end.month != last_day_of_month.month or end.year != last_day_of_month.year:
                last_day_of_end_month = (end.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                yield last_day_of_end_month
        else:
            for i in range(int ((end - start).days) + 1):
                yield start + timedelta(i)

    @classmethod
    def date_url_generator(cls, weather_station_url, start_date, end_date = date.today()):
        date_range = Utils.date_range_generator(start_date, end_date)
        #print(date_range)
        for date in date_range:
            #print(date)
            date_string = date.strftime("%Y-%m-%d")
            if MONTHLY:
                url = f'{weather_station_url}/table/{date_string}/{date_string}/monthly'
            else:
                url = f'{weather_station_url}/table/{date_string}/{date_string}/daily'

            yield date_string, url
    
    @classmethod
    def date_url_array(cls, date_url_gen):
        date_url_arr = []
        for url in date_url_gen:
            date_url_arr.append(url)
        return date_url_arr

    @classmethod
    def fetch_data_table(cls, url):
        """
            Fetches a weather data url and checks if there are data entries for that date
        """
        html_string = cls.session.get(url)
        doc = lh.fromstring(html_string.content)
        if MONTHLY:
            print(doc)
        else:
            data_table = doc.xpath('//*[@id="main-page-content"]/div/div/div/lib-history/div[2]/lib-history-table/div/div/div/table/tbody/tr')
        if data_table != []:
            return True
        else:
            return False

    @classmethod
    def first_data_url(cls, date_arr, low, high):

        if(high >= low):
            mid = low + (high - low) // 2
            print(f"low is {low} - {date_arr[low]}")
            print(f"high is {high} - {date_arr[high]}")
            print(f"mid is {mid} - {date_arr[mid]}")
            print(f"----//----")

            date_string_1 = date_arr[mid].strftime("%Y-%m-%d")
            date_string_2 = date_arr[mid - 1].strftime("%Y-%m-%d")
            if MONTHLY:
                url_1 = f'{Utils.weather_station_url}/table/{date_string_1}/{date_string_1}/monthly'
                url_2 = f'{Utils.weather_station_url}/table/{date_string_2}/{date_string_2}/monthly'
            else:
                url_1 = f'{Utils.weather_station_url}/table/{date_string_1}/{date_string_1}/daily'
                url_2 = f'{Utils.weather_station_url}/table/{date_string_2}/{date_string_2}/daily'
            data_1 = Utils.fetch_data_table(url_1)
            data_2 = Utils.fetch_data_table(url_2)

            if((data_1 and not data_2)):
                # result found, return result
                print(f'First date found! {date_arr[mid]}')
                print(url_1)
                return date_arr[mid]
            elif(data_1 == True):
                return Utils.first_data_url(date_arr, low, (mid - 1))
            elif(data_1 == False):
                return Utils.first_data_url(date_arr, (mid + 1), high)
        
        print(f'\nFirst date not found!')
        return -1


    @classmethod
    def find_first_data_entry(cls, weather_station_url, start_date):
        """
            Given a station URL, finds the first date_url where data exists.
        """
        Utils.weather_station_url = weather_station_url
        date_gen = Utils.date_range_generator(start_date)
        date_arr = Utils.date_url_array(date_gen)

        n = len(date_arr)

        print("\n** Initializing binary search to find the first date with data **")
        first_date_with_data = Utils.first_data_url(date_arr, 0, n - 1)
        return first_date_with_data