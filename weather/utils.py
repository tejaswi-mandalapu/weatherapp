import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_weather_by_coords(lat, lon):
    """
    Get weather data by coordinates using WeatherAPI
    """
    try:
        # Check cache first
        cache_key = f'weather_{lat}_{lon}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        url = f"http://api.weatherapi.com/v1/current.json?key={settings.WEATHER_API_KEY}&q={lat},{lon}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather_data = {
            'temperature': data['current']['temp_c'],
            'description': data['current']['condition']['text'],
            'icon': data['current']['condition']['icon'],
            'humidity': data['current']['humidity'],
            'wind_speed': data['current']['wind_kph'],
            'feels_like': data['current']['feelslike_c'],
            'location': data['location']['name']
        }
        
        # Cache for 30 minutes
        cache.set(cache_key, weather_data, 1800)
        return weather_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather API request failed: {e}")
        return {'error': 'Could not fetch weather data'}
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing weather data: {e}")
        return {'error': 'Invalid weather data received'}