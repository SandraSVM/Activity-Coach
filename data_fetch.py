from datetime import datetime, timedelta
import requests
from random import randint

class Data_fetch:
    def __init__(self):
        pass

    def fetch_user_data(self):
        'Get current data from the user: # steps, calories burned, mins MPA'
        pass

    def fetch_example_user(self, user_profile):
        steps = 0
        kcal = 0
        mpa = 0

        if user_profile == "VA":
           
            mpa = randint(0,10)
        else:
            mpa = randint(0,20)
        
            
        return {'steps':steps, 'kcal': kcal, 'mpa': mpa}

    def location_finder(self, zipcode:str="7511"):
        country = "NL"

        url = (
                    "https://geocoding-api.open-meteo.com/v1/search"
                    f"?name={zipcode}"
                    f"&countryCode={country}"
                    "&count=1"
                )

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            raise ValueError(f"Postal code '{zipcode}' not found")

        result = data["results"][0]

        return result["latitude"], result["longitude"]
 

    def fetch_weather_data(self, latitude, longitude):
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current=temperature_2m"
            "&hourly=precipitation"
            "&forecast_days=1"
            "&models=knmi_seamless"
        )

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        #Temperature
        current_temp = data["current"]["temperature_2m"]


        # Next 6 hours precipitation
        current_time = str(datetime.now())
        current_time = datetime.fromisoformat(current_time)
        rounded = current_time.replace(minute=0,second=0,microsecond=0)

        if current_time.minute != 0:
            rounded += timedelta(hours=1)

        current_time = rounded.isoformat(timespec="minutes")
     


        times = data["hourly"]["time"]
        precip = data["hourly"]["precipitation"]
      
                
        start_index = times.index(current_time)
        precip_next_6h = precip[start_index:start_index + 6]
        times_next_6h = times[start_index:start_index + 6]

        first_rain = None
        rain_threshold = 0.1
        

        for time, amount in zip(times_next_6h, precip_next_6h):
            if amount > rain_threshold:
                first_rain = time
                break

        if first_rain:
            first_rain = datetime.fromisoformat(first_rain)
            first_rain = first_rain.strftime("%H:%M")
            precip_forecast = f"Precipitation expected around {first_rain}."
            precipitation = "True"

        else:
            precip_forecast = "No precipitation expected in the next 6 hours."
            precipitation = "False"

        return current_temp, precipitation, precip_forecast

    
    def fetch_weather_by_zipcode(self, zipcode:str):
        latitude, longitude = self.location_finder(zipcode)
        weather = self.fetch_weather_data(latitude, longitude)
        return weather

    def get_workout_location(self, current_temp):
        
        restricted_workout_location = 0

        if current_temp >= 32:
            #disable retrieving a workout recommendation -> skip directly to the LLM part, with an input about not recommending exercise due to hot temperatures
            restricted_workout_location = -1

        elif current_temp >= 28:
            #filter out for indoor workouts only
            restricted_workout_location = 1
        
        return restricted_workout_location
    

#Common weather fields:
#'''temperature_2m
#apparent_temperature
#relative_humidity_2m
#precipitation
#rain
#snowfall
#cloud_cover
#wind_speed_10m
#wind_direction_10m
#surface_pressure'''